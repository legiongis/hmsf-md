#! /usr/bin/bash

# -- downloads sql file from provide s3 url and loads into
# into local database of the same name

S3URL=$1
SQLFILE="${S3URL##*/}"
DBNAME="${SQLFILE%.*}"

echo "Downloading: $S3URL and loading into database: $DBNAME"

read -p "Database $DBNAME will be overwritten. Continue? Y/n > " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Nn]$ ]]
then
    if [ ! -f ./$SQLFILE ]; then
        aws s3 cp $S3URL .
    fi
    if [ -f $SQLFILE ]; then
        psql -U postgres -h localhost -c "DROP DATABASE IF EXISTS $DBNAME;" -c "CREATE DATABASE $DBNAME;"
        psql -U postgres -h localhost -d $DBNAME -f $SQLFILE
    else
        echo "error downloading file, check your s3 url (it should look like s3://<bucket_name>/<filename>.sql)"
    fi
    # scp OldInsuranceMaps:/opt/app/ohmg/loc_insurancemaps_20240822.sql . && \
    # psql -U postgres -c "DROP DATABASE IF EXISTS ohmg_prod_replica;" -c "CREATE DATABASE ohmg_prod_replica;" && \
    # psql -U postgres -d ohmg_prod_replica -f loc_insurancemaps_20240822.sql && \
fi

echo "database restored: $DBNAME"
