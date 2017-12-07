# Sync Github Users
Runs on Amazon Linux to sync users and SSH keys from Github.

## Build

```shell
docker build -t sync-github-users.local .
```

## Run

```shell
docker run --rm -e GITHUB_TOKEN -e GITHUB_SSH_TEAMS -e GITHUB_ORG -v /home/:/home/ -v /etc/:/etc/ sync-github-users.local
```
