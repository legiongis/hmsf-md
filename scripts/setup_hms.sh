#! /usr/bin/bash

uv run manage.py setup_db

uv run manage.py setup_hms --test-accounts --test-resources

## for some reason, running a version of this spatial join within the
## python management command didn't work for the County/FPAN Region fields.
## no time to debug that properly now, so it makes sense to put the call
## within this shell script.
uv run manage.py spatial_join --all
