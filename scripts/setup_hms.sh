#! /usr/bin/bash

CY=$'\e[96m'
NC=$'\e[0m'

echo -e "${CY}-- Initialize DATABASE --${NC}"

uv run manage.py setup_db

echo -e "${CY}-- Initialize ELASTICSEARCH --${NC}"

uv run manage.py es delete_indexes
uv run manage.py es setup_indexes

echo -e "${CY}-- Initialize CACHE TABLE --${NC}"

uv run manage.py createcachetable

echo -e "${CY}-- Run MIGRATIONS --${NC}"

uv run manage.py migrate

echo -e "${CY}-- Import SYSTEM SETTINGS --${NC}"

uv run manage.py packages -o import_business_data -s fpan/system_settings/System_Settings.json -ow overwrite

echo -e "${CY}-- Load PACKAGE --${NC}"

uv run manage.py packages -o load_package -s fpan/pkg --yes

echo -e "${CY}-- Update default MAP LAYERS --${NC}"

uv run manage.py update_map_layers

echo -e "${CY}-- Load extra MAP LAYERS --${NC}"

uv run manage.py loaddata 1919-coastal-map
uv run manage.py loaddata slr1-layer
uv run manage.py loaddata slr2-layer
uv run manage.py loaddata slr3-layer
uv run manage.py loaddata slr6-layer
uv run manage.py loaddata slr10-layer

echo -e "${CY}-- Register CUSTOM SEARCH FILTERS --${NC}"

uv run manage.py extension register search-filter --source fpan/search/components/rule_filter.py
uv run manage.py extension register search-filter --source fpan/search/components/scout_report_filter.py

echo -e "${CY}-- Unregister PROVISIONAL SEARCH FILTERS --${NC}"

uv run manage.py extension unregister search-filter --name "Provisional Filter"

echo -e "${CY}-- Enable ETL MANAGER --${NC}"

uv run manage.py enable_etl_manager

echo -e "${CY}-- Load MANAGEMENT AGENCIES --${NC}"

uv run manage.py loaddata management-agencies

uv run manage.py save_management_agencies

echo -e "${CY}-- Load FPAN REGIONS --${NC}"

uv run manage.py loaddata fpan-regions

echo -e "${CY}-- Load MANAGEMENT AREA CATEGORIES --${NC}"

uv run manage.py loaddata management-area-categories

echo -e "${CY}-- Load MANAGEMENT AREAS --${NC}"

uv run manage.py loaddata management-areas-state-park
uv run manage.py loaddata management-areas-state-forest
uv run manage.py loaddata management-areas-fwcc
uv run manage.py loaddata management-areas-conservation-area
uv run manage.py loaddata management-areas-aquatic-preserve
uv run manage.py loaddata management-areas-hillsborough-co-elapp
uv run manage.py loaddata management-areas-hillsborough-co-parks

uv run manage.py save_management_areas

echo -e "${CY}-- Load MANAGEMENT AREA GROUPS --${NC}"

uv run manage.py loaddata management-area-groups

echo -e "${CY}-- Deactivate default ETL MODULES --${NC}"

uv run manage.py extension deactivate etl-module --name "Import Single CSV"
uv run manage.py extension deactivate etl-module --name "Import Branch Excel"

echo -e "${CY}-- Load SITE THEME --${NC}"

uv run manage.py loaddata site_theme

echo -e "${CY}-- Create test MATERIALS --${NC}"

uv run manage.py create_test_materials

## for some reason, running a version of this spatial join within the
## python management command didn't work for the County/FPAN Region fields.
## no time to debug that properly now, so it makes sense to put the call
## within this shell script.
uv run manage.py spatial_join --all
