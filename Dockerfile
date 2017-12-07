FROM amazonlinux AS base

RUN yum install -y python36-pip shadow-utils && \
    ln -fs /usr/bin/python3.6 /usr/bin/python && \
    ln -fs /usr/bin/pip-3.6 /usr/bin/pip

RUN pip install --no-cache-dir pygithub sh

COPY sync_github_users.py /usr/bin/

FROM base

RUN yum install -y gcc python36-devel && \
    ln -fs /usr/bin/python3.6 /usr/bin/python && \
    ln -fs /usr/bin/pip-3.6 /usr/bin/pip && \
    pip install --no-cache-dir pytest mypy

COPY test_sync_github_users.py /usr/bin/

RUN mypy --ignore-missing-imports /usr/bin/sync_github_users.py
RUN pytest /usr/bin/test_sync_github_users.py

FROM base

CMD ["python", "/usr/bin/sync_github_users.py"]
