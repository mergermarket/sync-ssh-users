import os
from typing import Sequence

from github import Github
from sh import id as id_, useradd


def get_users_to_add(
    github_client, github_org: str, ssh_teams: Sequence[str]
) -> Sequence[object]:
    normalised_ssh_teams = [t.lower() for t in ssh_teams]

    org = github_client.get_organization(github_org)

    teams = [
        t for t in org.get_teams()
        if t.name.lower() in normalised_ssh_teams
    ]

    users = set()
    for team in teams:
        for member in team.get_members():
            users.add(member)

    return list(users)


def add_user(github_user):
    username = github_user.login
    if not _user_exists(username):
        useradd('--create-home', '-g', 'users', '-G', 'wheel',  username)


def _user_exists(username: str) -> bool:
    return id_(username, _ok_code=[0, 1]).startswith('uid')


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


if __name__ == '__main__':
    main()
