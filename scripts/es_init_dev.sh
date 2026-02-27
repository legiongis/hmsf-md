#! /usr/bin/bash

docker run --name es-7.4 \
  --net elastic \
  -e "discovery.type=single-node" \
  -p 9200:9200 \
  -m 1GB \
  docker.elastic.co/elasticsearch/elasticsearch:7.4.2