FROM python:3.6-alpine

ARG PIP_REGISTRY

# Install dependencies
COPY requirements.txt /tmp/

RUN addgroup jenkins && adduser -s /bin/bash -D -G jenkins jenkins && \
	apk --update add gcc musl-dev libffi-dev libxml2-dev libxslt-dev openssl-dev bash git openssh-client gettext && \
	cd /tmp/ && pip install --extra-index-url http://$PIP_REGISTRY --trusted-host $(echo $PIP_REGISTRY | cut -d':' -f1) -r requirements.txt && \
	apk del gcc musl-dev libffi-dev openssl-dev && rm -rf /var/cache/apk/* /tmp /root/.cache
