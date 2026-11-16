#! /usr/bin/bash

rm node_modules -r
npm install
npm run build_development
uv run manage.py collectstatic --noinput
touch fpan/wsgi.py
