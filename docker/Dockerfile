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


# Highest python version compatible with legiongis/arches#dev/6.2.x-hms-cli
FROM python:3.10-bookworm

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

# TODO: what is ARCHES_DATA for?
ENV ARCHES_DATA=${ARCHES_ROOT}/arches_data
ENV WHEELS=/wheels
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE 1

# Setup needed directories
RUN mkdir ${ARCHES_ROOT} && mkdir /var/log/supervisor && mkdir /var/log/celery

# Prepare for apt installs
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

# Node-related installs

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

RUN npm install -g yarn

# Install Arches, arches-extensions, and the Arches app
# Later (in docker-compose), we mount over the install locations
# as volumes from the host machine to maintain editability
# without rebuilding this Docker image.

RUN rm -rf /root/.cache/pip/*

RUN pip install --upgrade pip

# Location of arches and arches-extensions repos
WORKDIR ${ARCHES_ROOT}

# Clone the legiongis fork of Arches 6.2
RUN git clone --branch=dev/6.2.x-hms-cli --single-branch https://github.com/legiongis/arches

# psycopg2 2.9.10 supports arm64 architecture
RUN sed -i 's/psycopg2-binary==2.8.4/psycopg2-binary==2.9.10/' arches/arches/install/requirements.txt && \
    pip install -e arches/ && \
    pip install -r arches/arches/install/requirements_dev.txt

RUN pip install supervisor && \
    pip install pytz --upgrade && \
    pip install tzdata --upgrade

# Install legiongis arches extensions
RUN git clone https://github.com/legiongis/arches-extensions.git && \
    cd arches-extensions && \
    git checkout e349934 && \
    pip install -e .

# Project-specific requirements
# Install fpan python deps -- must rebuild when python requirements change
# (JS dependencies should be installed via yarn on the host machine, as
# they live in fpan, which gets mounted as a volume)
COPY ../fpan/requirements.txt ${VIRTUAL_ENV}/fpan_requirements.txt
RUN pip install -r ${VIRTUAL_ENV}/fpan_requirements.txt

# Run forever to allow dev to to run `python manage.py setup_hms` or `python manage.py runserver 0:8000` as desired
CMD ["sleep", "infinity"]

# Django server port
EXPOSE 8000

WORKDIR ${APP_ROOT}
