FROM ubuntu:18.04 AS base 
USER root

ENV WEB_ROOT=/web_root
ENV ARCHES_ROOT=${WEB_ROOT}/arches
ENV WHEELS=/wheels
ENV PYTHONUNBUFFERED=1

ENV ARCHES_PROJECT=fpan

RUN apt-get update && apt-get install -y make software-properties-common

FROM base AS wheelbuilder

WORKDIR ${WHEELS}

# Install pip requirements files
COPY ./arches/arches/install/requirements.txt ${WHEELS}/requirements.txt
COPY ./arches/arches/install/requirements_dev.txt ${WHEELS}/requirements_dev.txt

# Install packages required to build the python libs, then remove them
RUN set -ex \
    && BUILD_DEPS=" \
        build-essential \
        libxml2-dev \
        libproj-dev \
        libjson-c-dev \
        xsltproc \
        docbook-xsl \
        docbook-mathml \
        libgdal-dev \
        libpq-dev \
        python3.8 \
        python3.8-dev \
        curl \
        python3.8-distutils \
        libldap2-dev libsasl2-dev ldap-utils \
        dos2unix \
        git \
        " \
    && apt-get update -y \
    && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && curl https://bootstrap.pypa.io/pip/3.8/get-pip.py -o get-pip.py \
    && python3.8 get-pip.py \
    # pip <=21.2 is required for the -b command below
    && pip install pip==21.2

RUN pip3 wheel --no-cache-dir -b /tmp -r ${WHEELS}/requirements.txt  \
    && pip3 wheel --no-cache-dir -b /tmp -r ${WHEELS}/requirements_dev.txt  \
    && pip3 wheel --no-cache-dir -b /tmp gunicorn \
    && pip3 wheel --no-cache-dir -b /tmp django-auth-ldap

# Add Docker-related files
RUN chmod -R 700 ${WHEELS}

FROM base 

# Get the pre-built python wheels from the build environment
RUN mkdir ${WEB_ROOT}

COPY --from=wheelbuilder ${WHEELS} /wheels

# Install packages required to run Arches
# Note that the ubuntu/debian package for libgdal1-dev pulls in libgdal1i, which is built
# with everything enabled, and so, it has a huge amount of dependancies (everything that GDAL
# support, directly and indirectly pulling in mysql-common, odbc, jp2, perl! ... )
# a minimised build of GDAL could remove several hundred MB from the container layer.
RUN set -ex \
    && RUN_DEPS=" \
        mime-support \
        libgdal-dev \
        python3-venv \
        postgresql-client-12 \
        python3.8 \
        python3.8-distutils \
        python3.8-venv \
        build-essential \
        libatlas-base-dev \
        gfortran \
        python3-setuptools \
        libxml2-dev \
        libxslt-dev \
        python3.8-dev \
        git \
    " \
    && apt-get install -y --no-install-recommends curl \
    && curl -sL https://deb.nodesource.com/setup_16.x | bash - \
    && curl -sL https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && add-apt-repository "deb http://apt-archive.postgresql.org/pub/repos/apt/ $(lsb_release -sc)-pgdg main" \
    && apt-get update -y \
    && apt-get install -y --no-install-recommends $RUN_DEPS \
    && curl https://bootstrap.pypa.io/pip/3.8/get-pip.py -o get-pip.py \
    && python3.8 get-pip.py \
    && pip install pip==21.2 \
    && apt-get install -y nodejs \
    && npm install -g yarn

# Install Yarn components
COPY ./arches/package.json ${ARCHES_ROOT}/arches/install/package.json
COPY ./arches/.yarnrc ${ARCHES_ROOT}/arches/install/.yarnrc
COPY ./arches/yarn.lock ${ARCHES_ROOT}/arches/install/yarn.lock
WORKDIR ${ARCHES_ROOT}/arches/install
RUN mkdir -p ${ARCHES_ROOT}/arches/app/media/packages
RUN yarn install

WORKDIR ${WEB_ROOT}

RUN python3.8 -m venv ENV \
    && . ENV/bin/activate \
    && pip install --upgrade pip wheel setuptools \
    && pip install cython==0.29.36 \
    && pip install --only-binary=numpy numpy==1.21.3 \
    && pip install shapely==1.8.5 \
    && pip install requests \
    && pip install -f ${WHEELS} django-auth-ldap \
    && pip install -f ${WHEELS} gunicorn \
    && grep -v "mapbox-vector-tile" ${WHEELS}/requirements.txt > ${WHEELS}/requirements_filtered.txt \
    && pip install -r ${WHEELS}/requirements_filtered.txt -f ${WHEELS} \
    && pip install mapbox-vector-tile \
    && pip install -r ${WHEELS}/requirements_dev.txt -f ${WHEELS} \
    && rm -rf ${WHEELS} \
    && rm -rf /root/.cache/pip/*

# Install the Arches application
# FIXME: ADD from github repository instead?
COPY ./arches ${ARCHES_ROOT}

WORKDIR ${ARCHES_ROOT}

RUN . ../ENV/bin/activate \
    && pip install -e . --no-binary :all:

COPY ./arches/docker/gunicorn_config.py ${ARCHES_ROOT}/gunicorn_config.py
COPY ./arches/docker/settings_local.py ${ARCHES_ROOT}/arches/settings_local.py

# Expose port 8000
EXPOSE 8000

# FPAN ===================================================================

# Install legiongis arches extensions
RUN cd /tmp && \
    git clone https://github.com/legiongis/arches-extensions.git && \
    cd arches-extensions && \
    git checkout e349934 && \
    . ${WEB_ROOT}/ENV/bin/activate && \
    pip install -e .


# Install fpan python deps -- must rebuild when python requirements change
# (JS dependencies should be installed via yarn on the host machine, as
# they live in fpan, which gets mounted as a volume)
COPY ./fpan/requirements.txt /tmp/fpan_requirements.txt
RUN . ${WEB_ROOT}/ENV/bin/activate && \
    pip install -r /tmp/fpan_requirements.txt

WORKDIR ${WEB_ROOT}/${ARCHES_PROJECT}
