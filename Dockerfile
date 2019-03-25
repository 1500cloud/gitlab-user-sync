FROM alpine:latest

RUN apk --no-cache add python3 py3-setuptools
RUN mkdir -p /build
COPY . /build

WORKDIR /build
RUN python3 setup.py install

CMD ["/usr/bin/sync-gitlab-users"]
