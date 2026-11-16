#! /usr/bin/bash

npm ci
npm run build_development
uv run manage.py collectstatic --noinput
touch fpan/wsgi.py
