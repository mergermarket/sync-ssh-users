# Sync SSH Users
Runs on Amazon Linux to sync users and SSH keys from S3.

## Build

```shell
docker build -t sync-ssh-users.local .
```

## Run

```shell
docker run --rm -e S3_BUCKET -e SSH_TEAMS -v /home/:/home/ -v /etc/:/etc/ sync-ssh-users.local
```
