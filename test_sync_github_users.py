import os
import stat

from unittest.mock import patch, MagicMock, Mock

from pytest import raises

from sh import id as id_, getent, useradd, ErrorReturnCode

import sync_github_users


def filemode(filepath):
    return stat.filemode(os.stat(filepath).st_mode)


def setup_mock_teams():
    mock_key_1 = Mock()
    mock_key_1.key = 'ssh-rsa foo'
    mock_key_2 = Mock()
    mock_key_2.key = 'ssh-rsa bar'
    mock_key_3 = Mock()
    mock_key_3.key = 'ssh-rsa baz'
    mock_key_4 = Mock()
    mock_key_4.key = 'ssh-rsa bat'

    mock_member_1 = Mock()
    mock_member_1.login = 'aad'
    mock_member_1.get_keys.return_value = [mock_key_1]

    mock_member_2 = Mock()
    mock_member_2.login = 'bbe'
    mock_member_2.get_keys.return_value = [mock_key_2, mock_key_3]

    mock_member_3 = Mock()
    mock_member_3.login = 'ccf'
    mock_member_3.get_keys.return_value = [mock_key_4]

    mock_members_1 = MagicMock()
    mock_members_1.__iter__.return_value = [mock_member_1, mock_member_2]

    mock_members_2 = MagicMock()
    mock_members_2.__iter__.return_value = [mock_member_3]

    mock_team_1 = Mock()
    mock_team_1.name = 'foo'
    mock_team_1.get_members.return_value = mock_members_1

    mock_team_2 = Mock()
    mock_team_2.name = 'bar'
    mock_team_2.get_members.return_value = mock_members_2

    mock_team_3 = Mock()
    mock_team_3.name = 'baz'

    mock_teams = MagicMock()
    mock_teams.__iter__.return_value = [mock_team_1, mock_team_2, mock_team_3]

    return mock_teams


@patch.object(sync_github_users.Github, 'get_organization', autospec=True)
def test_adds_users(get_organization):
    # Given
    get_organization.return_value.get_teams.return_value = setup_mock_teams()

    os.environ['GITHUB_SSH_TEAMS'] = 'foo,Bar'
    os.environ['GITHUB_TOKEN'] = 'token'
    os.environ['GITHUB_ORG'] = 'org'

    # When
    sync_github_users.main()

    # Then
    assert 'groups' in id_('aad')
    assert 'groups' in id_('bbe')
    assert 'groups' in id_('ccf')

    assert 'aad' in getent('group', 'users')
    assert 'bbe' in getent('group', 'users')
    assert 'ccf' in getent('group', 'users')

    assert 'aad' in getent('group', 'wheel')
    assert 'bbe' in getent('group', 'wheel')
    assert 'ccf' in getent('group', 'wheel')


@patch.object(sync_github_users.Github, 'get_organization', autospec=True)
def test_adds_ssh_keys(get_organization):
    # Given
    get_organization.return_value.get_teams.return_value = setup_mock_teams()

    os.environ['GITHUB_SSH_TEAMS'] = 'foo,Bar'
    os.environ['GITHUB_TOKEN'] = 'token'
    os.environ['GITHUB_ORG'] = 'org'

    # When
    sync_github_users.main()

    # Then
    assert filemode('/home/aad/.ssh/authorized_keys') == '-rw-------'
    assert filemode('/home/bbe/.ssh/authorized_keys') == '-rw-------'
    assert filemode('/home/ccf/.ssh/authorized_keys') == '-rw-------'

    with open('/home/aad/.ssh/authorized_keys') as f:
        content = f.read()
        assert 'ssh-rsa foo' in content

    with open('/home/bbe/.ssh/authorized_keys') as f:
        content = f.read()
        assert 'ssh-rsa bar' in content
        assert 'ssh-rsa baz' in content

    with open('/home/ccf/.ssh/authorized_keys') as f:
        content = f.read()
        assert 'ssh-rsa bat' in content


@patch.object(sync_github_users.Github, 'get_organization', autospec=True)
def test_removes_users(get_organization):
    # Given
    get_organization.return_value.get_teams.return_value = setup_mock_teams()

    sync_github_users.add_user('foo')

    os.environ['GITHUB_SSH_TEAMS'] = 'foo,Bar'
    os.environ['GITHUB_TOKEN'] = 'token'
    os.environ['GITHUB_ORG'] = 'org'

    # When
    sync_github_users.main()

    # Then
    with raises(ErrorReturnCode):
        id_('foo')

    assert 'foo' not in getent('group', 'users')

    assert 'foo' not in getent('group', 'wheel')

    assert not os.path.isdir('/home/foo')
