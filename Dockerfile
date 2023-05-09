FROM python:3.7-alpine3.17

ARG PIP_REGISTRY
ARG PIP_CERTIFICATE

# Install dependencies
COPY make_pip_args.py requirements.txt [p]ypi.crt /tmp/ 

RUN addgroup jenkins && adduser -s /bin/bash -D -G jenkins jenkins && \
	apk --update add gcc libgcc musl-dev libffi-dev libxml2-dev libxslt-dev libressl-dev bash git openssh-client gettext cargo make cmake && \
	cd /tmp/ && pip install certifi && pip install $(python make_pip_args.py $PIP_REGISTRY $PIP_CERTIFICATE) -r requirements.txt && \
	apk del gcc musl-dev libffi-dev libressl-dev cargo make cmake && rm -rf /var/cache/apk/* /tmp /root/.cache /root/.cargo
