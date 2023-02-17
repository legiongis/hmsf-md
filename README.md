# HMS Florida - Monitoring Database 

HMS Florida is a program from the [Florida Public Archaeological Network](https://fpan.us) that facilitates the crowdsourced collection of condition assessments for historic cemeteries, historic structures, and archaeological sites all around the state of Florida. This is the Monitoring Database component of that program, which manages particiation by citizen scientists ("Heritage Monitoring Scouts", a.k.a. **Scouts**) alongside employees of various public agencies (for example, State Park employees, a.k.a. **Land Managers**).

You can view the platform in production at [hms.fpan.us](https://hms.fpan.us), and learn more about the HMS Florida program at [fpan.us/projects/hms-florida/](https://www.fpan.us/projects/hms-florida/)

## Software Architecture

The HMS Florida - Monitoring Database is an implementation of the open source cultural heritage inventory system [Arches](http://archesproject.org/). Arches uses the Django web framework, and is designed as a Django project + app. This particular implementation extends Arches with a few [Arches extensions](https://arches.readthedocs.io/en/latest/developing/extending/creating-extensions/), as well as some custom Django apps.

```
fpan/
    fpan/           # Arches project + Django app
        pkg/        # Arches package
    hms/            # New Django app
    reporting/      # New Django app 
    site_theme/     # New Django app 
    legacy/         # New Django app 
```

`fpan` - This is the main Arches [project](https://arches.readthedocs.io/en/latest/installing/projects-and-packages/#project-structure) (and by extension the base Django project), which holds a number of CSS/JS/HTML template overrides, as well as a number of custom [Arches extensions](https://arches.readthedocs.io/en/latest/developing/extending/creating-extensions/) for this implementation.
`pkg` - The Arches [package](https://arches.readthedocs.io/en/latest/installing/projects-and-packages/#understanding-packages) that holds the database schema, and a custom basemap style.
`hms` - Holds the majority of custom work that sits outside of a normal Arches project. For example, Scount and LandManager profile models, and the `ManagementArea` and `ManagementAreaGroup` classes that are attached to user profiles to drive archaeological site permissions.
`reporting` - Some simple utils for collecting data and sending reports to admins (WIP).
`site_theme` - Holds models and some templates to allow db admins to create custom content for the front-end (WIP).
`legacy` - Over the years numerous management commands and utilities have been written for one-off migration/transformation operations. They are now in this app, which should generally NOT be included in `INSTALLED_APPS`.

## Dependencies

In addition to all [core Arches dependencies](https://arches.readthedocs.io/en/latest/installing/requirements-and-dependencies/#software-dependencies), the following Python requirements have been added:

- `grapelli` - Nice admin theme
- `django-tinymce` - WISIWYG admin editor for custom profile content
- `pygments` - Text formatting in admin to show JSON
- `django-storages`/`boto3` - Media storage on AWS S3

This implementation also uses a slightly modified fork of the core Arches code base:

- [legiongis/arches/dev/6.2.x-hms-cli](https://github.com/legiongis/arches/tree/dev/6.2.x-hms-cli)

## Making a dev installation

This will get a fully function (if empty of real site data) installation of the HMS Florida Monitoring Database

### Install core Arches

- Create and activate a virtual environment:

    ```
    python3 -m venv env
    source env/bin/activate
    ```

 - Clone our fork of core Arches and checkout the modified branch:

    ```
    git clone https://github.com/legiongis/arches
    cd arches
    git fetch --all
    git checkout dev/6.2.x-hms-cli
    cd ..
    ```

- Install Arches into the virtual environment:

    ```
    python -m pip install --upgrade pip
    pip install -e arches
    pip install -r arches/arches/install/requirements_dev.txt
    ```

### Install this project's dependencies

- Clone this project repo:

    ```
    git clone https://github.com/legiongis/fpan
    ```

- Enter the project and install js dependencies:

    ```
    cd fpan/fpan
    yarn install
    cd ..
    ```

### Setup the database

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
    python manage.py setup_hms
    ```
    - This command:
        1. Wraps the default `setup_db` command from Arches
        2. Load the included "package" (graphs, concepts, etc) stored in `fpan/pkg`
        3. Loads a number of database fixtures
        4. Modifies some default Arches content, like map layer names, etc.
    - Add `--test-accounts` to create a few dummy Scout and LandManager accounts for testing

### View

- Run the development server to view at http://localhost:8000.

    ```
    python manage.py runserver
    ```
    - You may need to add `0:8000` on remote server instances.