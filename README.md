## Florida Public Archaeology Network - Heritage Monitoring Scouts

This web app is an implementation of [Arches](http://archesproject.org/) designed to facilitate the crowdsourced collection of condition assessments for historic cemeteries, historic structures, and archaeological sites all around the state of Florida. To learn more about FPAN, visit [fpan.us](https://fpan.us). You can view this app in production (and sign up to be a Heritage Monitoring Scout if you live in Florida) at [hms.fpan.us](https://hms.fpan.us).

### Installation

This [Arches project](https://arches.readthedocs.io/en/stable/projects-and-packages/) works in conjunction with two other repos, [legiongis/arches](https://github.com/legiongis/arches) and [legiongis/fpan-data](https://github.com/legiongis/fpan-data). The former is a fork of the core Arches codebase with a few small changes, and the latter is an Arches package that defines the database schema and contains some initial data. To install locally, first [install the Arches dependencies](https://arches.readthedocs.io/en/stable/requirements-and-dependencies/)). After you have all dependencies installed, come back here. The following steps are basically the same as the recommended [Arches developer installation](https://arches.readthedocs.io/en/stable/creating-a-development-environment/).

- Create and activate a virtual environment:

    ```
    python3 -m venv env
    source env/bin/activate
    ```

 - Clone our fork of the core Arches repo [legiongis/arches](https://github.com/legiongis/arches) and checkout the `stable/5.1.x-fpan` branch:

    ```
    git clone https://github.com/legiongis/arches
    cd arches
    git fetch --all
    git checkout stable/5.1.x-fpan
    cd ..
    ```

- Clone this project repo:

    ```
    git clone https://github.com/legiongis/fpan
    ```

- Clone the package repo:

    ```
    git clone https://github.com/legiongis/fpan-data
    ```

- Install the python dependencies into your virtual environment:

    ```
    python -m pip install --upgrade pip
    pip install -r arches/arches/install/requirements.txt
    pip install -r arches/arches/install/requirements_dev.txt
    pip install -e arches
    pip install -r fpan/requirements.txt
    ```

- Enter the project and install js dependencies:

    ```
    cd fpan/fpan
    yarn install
    cd ..
    ```

- Create `settings_local.py` in `fpan/fpan/`, alongside the existing `settings.py`:

    This should contain all of your normal Django environment-specific variables, like database credentials. A basic example would be:

    ```
    from .settings import DATABASES

    DATABASES['default']['USER'] = "username"
    DATABASES['default']['PASSWORD'] = "password"
    DATABASES['default']['POSTGIS_TEMPLATE'] = "template_postgis"
    ```


- Initialize the database:

    ```
    python manage.py setup_db
    ```

- Add the test hms user accounts (helpful for development purposes):

    ```
    python manage.py create_test_hms_accounts
    ```

- Load the package (which includes test data for development purposes):

    ```
    python manage.py packages -o load_package -s ../fpan-data -ow overwrite
    ```

    Say yes to overriding settings.

- Run the development server to view at http://localhost:8000.

    ```
    python manage.py runserver
    ```