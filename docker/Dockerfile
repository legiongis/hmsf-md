FROM ubuntu:22.04

USER root

RUN apt-get update && && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    make software-properties-common \
    curl \
    gcc \
    build-essential \
    mime-support \
    libgdal-dev \
    dos2unix \
    nano
RUN apt-get update --fix-missing && apt-get install -y git

RUN apt-get update
RUN apt-get install -y postgresql-client-14


# Highest version compatible with legiongis/arches#dev/6.2.x-hms-cli
FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set up a virual environment to use for all later commands.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip

## Setting default environment variables
ARG ARCHES_ROOT
# The name of the arches project
ARG ARCHES_PROJECT
# Project specific paths
ARG APP_ROOT
ARG APP_COMP_FOLDER

# settings_local.py provides the DB credentials, etc. to the Arches project.
ENV SETTINGS_LOCAL_PATH=${APP_COMP_FOLDER}/settings_local.py
ENV CELERY_PATH=${APP_COMP_FOLDER}/celery.py
ENV URLS_PATH=${APP_COMP_FOLDER}/urls.py
# ENV GUNICORN_CONFIG_PATH=${APP_COMP_FOLDER}/gunicorn_config.py
ENV ARCHES_DATA=${ARCHES_ROOT}/arches_data
ENV PACKAGE_PATH=${APP_COMP_FOLDER}/package.json
ENV WHEELS=/wheels
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE 1

# Setup needed directories
RUN mkdir ${ARCHES_ROOT} && mkdir /var/log/supervisor && mkdir /var/log/celery

# Get ready to do some code installation
RUN apt-get update && apt-get install -y make software-properties-common

# Install packages required to run Arches
# Note that the ubuntu/debian package for libgdal1-dev pulls in libgdal1i, which is built
# with everything enabled, and so, it has a huge amount of dependancies (everything that GDAL
# support, directly and indirectly pulling in mysql-common, odbc, jp2, perl! ... )
# a minimised build of GDAL could remove several hundred MB from the container layer.
RUN set -ex \
    && RUN_DEPS=" \
        build-essential \
        libxml2-dev \
        libproj-dev \
        libjson-c-dev \
        xsltproc \
        docbook-xsl \
        docbook-mathml \
        libgdal-dev \
        libpq-dev \
        mime-support \
        python3-dev \
        postgresql-client-14 \
        dos2unix \
        gettext \
    " \
    && apt-get install -y --no-install-recommends curl \
    && curl -sL https://deb.nodesource.com/setup_16.x | bash - \
    && curl -sL https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && add-apt-repository "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -sc)-pgdg main" \
    && apt-get update -y \
    && apt-get install -y "wait-for-it" \
    && apt-get install -y nano \
    && apt-get install -y --no-install-recommends $RUN_DEPS



# ----------------------------------------------
# Do installs relating to Node
# ----------------------------------------------

ENV NODE_MAJOR=18

# Update package lists and install necessary packages
RUN apt-get update \
    && apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
    && mkdir -p /etc/apt/keyrings

# Add nodesource GPG key
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

# Add nodesource repository
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update

RUN apt-get install -y nodejs

# Clean up
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Arches

WORKDIR ${ARCHES_ROOT}

RUN rm -rf /root/.cache/pip/*

RUN pip install --upgrade pip

# Install legiongis fork of Arches 6.2
RUN git clone https://github.com/legiongis/arches && \
    cd arches && \
    git fetch --all && \
    git checkout dev/6.2.x-hms-cli

RUN sed -i 's/psycopg2-binary==2.8.4/psycopg2-binary==2.9.10/' arches/arches/install/requirements.txt && \
    pip install arches/ && \
    pip install -r arches/arches/install/requirements_dev.txt

RUN pip install supervisor && \
    pip install pytz --upgrade && \
    pip install tzdata --upgrade
    # pip install Redis && \
    # pip install gunicorn

# TODO: determine if this is necessary for fpan
# # copy in local settings to our newly created Arches project.
# WORKDIR ${APP_ROOT}
# COPY ./arches/settings_local.py ${SETTINGS_LOCAL_PATH}
# RUN sed -i 's/\r$//g' ${SETTINGS_LOCAL_PATH}
# # copy the celery.py file into out arches project. This hopefully makes the workers and beat work:
# COPY ./arches/celery.py ${CELERY_PATH}
# RUN sed -i 's/\r$//g' ${CELERY_PATH}

# TODO: determine if this is necessary for fpan
# # copy the urls.py into our new Arches project. This is part of
# # customization for internationalization
# RUN echo "copied urls to ${URLS_PATH}";
# COPY ./arches/urls.py ${URLS_PATH}
# RUN sed -i 's/\r$//g' ${URLS_PATH}

# NOTE: [legiongis] this is currently unused as this image is only intended for development
# (gunicorn is only needed when Django mode = production)
# ------------
# Copy the gunicorn_config.py file into our new Arches project. This is used
# for running Arches in production (not DEBUG mode)
# NOTE: We're NOT actually using this, because it will throw an error with urls.py 
# So this is here for reference only in case someone wants to edit gunicorn_config.py
# and figure out how to make it work.
# RUN echo "copy gunicorn_config.py to ${GUNICORN_CONFIG_PATH}";
# COPY ./arches/gunicorn_config.py ${GUNICORN_CONFIG_PATH}
# RUN sed -i 's/\r$//g' ${GUNICORN_CONFIG_PATH}

# NOTE: currently unused -- doesn't appear to be an issue
# Copy customized package until the issue with datatables.net is resolved.
# COPY ./arches/package.json ${PACKAGE_PATH}

# TODO: get rabbitmq working
# # copy the celery supervisor
# COPY /arches/conf.d/ ${APP_ROOT}/conf.d/
# RUN chmod -R 700 ${APP_ROOT}/conf.d/
# COPY /arches/arches_proj-supervisor.conf ${APP_ROOT}/arches_proj-supervisor.conf
# RUN chmod -R 700 ${APP_ROOT}/arches_proj-supervisor.conf
# RUN mkdir -p /var/log/supervisor
# RUN mkdir -p /var/log/celery

# NOTE: currently unused -- django command setup_hms seems to do the init of arches+fpan for us
# Make sure the entry point is available and lacks weird characters
# that don't work in a Linux OS
# COPY /arches/entrypoint.sh ${APP_ROOT}/entrypoint.sh
# RUN chmod -R 700 ${APP_ROOT}/entrypoint.sh &&\
#   dos2unix ${APP_ROOT}/entrypoint.sh

WORKDIR ${APP_ROOT}

# Run forever to allow dev to to run `python manage.py setup_hms` or `python manage.py runserver 0:8000` as desired
CMD ["sleep", "infinity"]

# Django server port
EXPOSE 8000
# Webpack port
EXPOSE 8021

# NOTE: currently unused -- fpan does not use couchdb
# # CouchDB port
# EXPOSE 5984


# Project-specific requirements

# Install legiongis arches extensions
RUN cd ${VIRTUAL_ENV} && \
    git clone https://github.com/legiongis/arches-extensions.git && \
    cd arches-extensions && \
    git checkout e349934 && \
    pip install -e .


# Install fpan python deps -- must rebuild when python requirements change
# (JS dependencies should be installed via yarn on the host machine, as
# they live in fpan, which gets mounted as a volume)
COPY ../fpan/requirements.txt ${VIRTUAL_ENV}/fpan_requirements.txt
RUN pip install -r ${VIRTUAL_ENV}/fpan_requirements.txt
