import json
import os
import stat

import unittest

from moto import mock_s3
from pytest import raises

import boto3
from sh import id as id_, getent, useradd, ErrorReturnCode

import sync_ssh_users


def filemode(filepath):
    return stat.filemode(os.stat(filepath).st_mode)


class TestSync(unittest.TestCase):

    S3_BUCKET = 'bucket'

    def setUp(self):
        self._m = mock_s3()
        self._m.start()

        s3_bucket = boto3.resource('s3').create_bucket(Bucket=self.S3_BUCKET)

        foo_data = {
            'members': [
                {'login': 'aad', 'ssh_keys': ['ssh-rsa foo']},
                {'login': 'bbe', 'ssh_keys': ['ssh-rsa bar', 'ssh-rsa baz']},
            ]
        }

        bar_data = {
            'members': [
                {'login': 'ccf', 'ssh_keys': ['ssh-rsa bat']},
                {'login': 'ddg', 'ssh_keys': []},
            ]
        }

        baz_data = {'members': []}

        s3_bucket.Object('teams/foo.json').put(Body=json.dumps(foo_data))
        s3_bucket.Object('teams/bar.json').put(Body=json.dumps(bar_data))
        s3_bucket.Object('teams/baz.json').put(Body=json.dumps(baz_data))

        os.environ['SSH_TEAMS'] = 'foo,Bar'
        os.environ['S3_BUCKET'] = self.S3_BUCKET

    def tearDown(self):
        self._m.stop()

    def test_adds_users(self):
        # When
        sync_ssh_users.main()

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


    def test_adds_ssh_keys(self):
        # When
        sync_ssh_users.main()

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


    def test_removes_users(self):
        # Given
        sync_ssh_users.add_user('foo')

        # When
        sync_ssh_users.main()

        # Then
        with raises(ErrorReturnCode):
            id_('foo')

        assert 'foo' not in getent('group', 'users')

        assert 'foo' not in getent('group', 'wheel')

        assert not os.path.isdir('/home/foo')


    def test_handles_users_with_no_keys(self):
        # When
        sync_ssh_users.main()

        # Then
        with open('/home/ddg/.ssh/authorized_keys') as f:
            assert len(f.read()) == 0
