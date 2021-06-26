# syntax=docker/dockerfile:1
FROM python:3.9-alpine
WORKDIR /app
ENV FLASK_RUN_HOST=0.0.0.0
# Alpine image includes dev headers, but pyncal can't find them on its own.
ENV CPATH=/usr/local/include/python3.9
EXPOSE 5000
# Build-time only dependencies.
RUN apk add --no-cache --virtual .deps build-base\
    musl-dev \
    linux-headers \
    libffi-dev
COPY . .
RUN python setup.py develop
# Purge build time dependencies.
RUN apk del .deps
