from collections import namedtuple
from hashlib import md5
import json
import logging
import os
import shutil
from stat import S_IREAD, S_IWRITE
import sys
from typing import Sequence

import boto3
from botocore.exceptions import ClientError
from sh import getent, id as id_, useradd, userdel, ErrorReturnCode


USERS_GROUP = 'users'
SUDO_GROUP = 'wheel'


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


logger = logging.getLogger('__name__')
logger.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.addFilter(InfoFilter())

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)

logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)


User = namedtuple('User', ['login', 'ssh_keys'])


def get_users_to_add(
    s3_bucket, ssh_teams: Sequence[str]
) -> Sequence[object]:
    normalised_ssh_teams = [t.lower() for t in ssh_teams]

    responses = []
    for team in normalised_ssh_teams:
        try:
            response = s3_bucket.Object(f'teams/{team}.json').get()['Body']\
                .read()
            responses.append(response)
        except ClientError as e:
            logger.error(e)

    teams = [
        json.loads(response)
        for response in responses
    ]

    return [
        User(member['login'], member['ssh_keys'])
        for team in teams
        for member in team['members']
    ]


def add_user(username: str):
    if not _user_exists(username):
        logger.info('Adding user: %s', username)
        try:
            useradd(
                '--create-home',
                '-g', USERS_GROUP,
                '-G', ','.join((USERS_GROUP, SUDO_GROUP)),
                username
            )
        except ErrorReturnCode as e:
            logger.error(e)


def _user_exists(username: str) -> bool:
    return id_(username, _ok_code=[0, 1]).startswith('uid')


def add_ssh_keys(user):
    username = user.login
    logger.info('Adding SSH keys for user: %s', username)
    ssh_directory = f'/home/{username}/.ssh/'

    key_file_content = '\n'.join(user.ssh_keys)

    key_file = os.path.join(ssh_directory, 'authorized_keys')

    if _file_has_changed(key_file, key_file_content):
        _ensure_directory(ssh_directory)
        _write_ssh_file(key_file, key_file_content, username)


def _file_has_changed(file, file_content):
    if not os.path.exists(file):
        return True
    data = file_content.encode('utf-8')
    with open(file, 'rb') as f:
        existing_data = f.read()
    if existing_data != data:
        return True
    return md5(data).hexdigest() != md5(existing_data).hexdigest()


def _write_ssh_file(path: str, content: str, username: str):
    temp_file = f'{path}.tmp'
    logger.info('Writing keys to temp path: %s', temp_file)
    with open(temp_file, 'w+') as f:
        f.write(content)
    logger.info('Moving temp path to: %s', path)
    shutil.chown(temp_file, username, USERS_GROUP)
    os.chmod(temp_file, S_IREAD | S_IWRITE)
    os.rename(temp_file, path)


def _ensure_directory(path: str):
    if not os.path.isdir(path):
        logger.info('Creating path: %s', path)
        os.mkdir(path)


def find_users_to_remove(valid_users: Sequence[str]) -> Sequence[str]:
    existing_users = getent('group', USERS_GROUP).split(':')[3].strip()
    users_to_remove = set(existing_users.split(',')) - set(valid_users)
    return list(users_to_remove)


def remove_user(username: str):
    try:
        userdel('--remove', '--force', username)
    except ErrorReturnCode as e:
        logger.error(e)


def main():
    ssh_teams = os.environ['SSH_TEAMS'].split(',')
    s3_bucket_name = os.environ['S3_BUCKET']

    s3_bucket = boto3.resource('s3').Bucket(s3_bucket_name)

    users_to_add = get_users_to_add(s3_bucket, ssh_teams)

    for user in users_to_add:
        logger.info('Attempting to add user: %s', user.login)
        add_user(user.login)
        add_ssh_keys(user)

    users_to_remove = find_users_to_remove((u.login for u in users_to_add))

    for username in users_to_remove:
        logger.info('Removing user: %s', username)
        remove_user(username)


if __name__ == '__main__':
    main()
