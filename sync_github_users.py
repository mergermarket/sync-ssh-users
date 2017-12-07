import os
import shutil
from stat import S_IREAD, S_IWRITE
from typing import Sequence

from github import Github
from sh import id as id_, useradd


USERS_GROUP = 'users'
SUDO_GROUP = 'wheel'


def get_users_to_add(
    github_client, github_org: str, ssh_teams: Sequence[str]
) -> Sequence[object]:
    normalised_ssh_teams = [t.lower() for t in ssh_teams]

    org = github_client.get_organization(github_org)

    teams = [
        t for t in org.get_teams()
        if t.name.lower() in normalised_ssh_teams
    ]

    return list({
        member
        for team in teams
        for member in team.get_members()
    })


def add_user(github_user):
    username = github_user.login
    if not _user_exists(username):
        useradd(
            '--create-home',
            '-g', USERS_GROUP,
            '-G', ','.join((USERS_GROUP, SUDO_GROUP)),
            username
        )


def _user_exists(username: str) -> bool:
    return id_(username, _ok_code=[0, 1]).startswith('uid')


def add_ssh_keys(github_user):
    username = github_user.login
    ssh_directory = f'/home/{username}/.ssh/'

    keys = github_user.get_keys()
    key_file_content = '\n'.join((k.key for k in keys))

    key_file = os.path.join(ssh_directory, 'authorized_keys')

    _ensure_directory(ssh_directory)
    _write_ssh_file(key_file, key_file_content, username)


def _write_ssh_file(path, content, username):
    temp_file = f'{path}.tmp'
    with open(temp_file, 'w+') as f:
        f.write(content)
    os.rename(temp_file, path)
    shutil.chown(path, username, USERS_GROUP)
    os.chmod(path, S_IREAD | S_IWRITE)


def _ensure_directory(path):
    if not os.path.isdir(path):
        os.mkdir(path)


# def find_users_to_remove() -> Sequence[str]:
#     pass


# def remove_user(username: str):
#     pass


def main():
    github_token = os.environ['GITHUB_TOKEN']
    github_org = os.environ['GITHUB_ORG']
    ssh_teams = os.environ['GITHUB_SSH_TEAMS'].split(',')

    github_client = Github(github_token)

    users_to_add = get_users_to_add(github_client, github_org, ssh_teams)

    for github_user in users_to_add:
        add_user(github_user)
        add_ssh_keys(github_user)


if __name__ == '__main__':
    main()
