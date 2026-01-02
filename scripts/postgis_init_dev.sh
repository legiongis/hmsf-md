#! /usr/bin/bash

docker run --name postgis13 \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  postgis/postgis:13-3.5-alpine
