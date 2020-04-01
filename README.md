## Florida Public Archaeology Network - Heritage Monitoring Scouts

This an app based on [Arches](http://archesproject.org/) designed to facilitate the collection of condition assessments for historic cemeteries, historic structures, and archaeological sites all around the state of Florida. Arches is an web-based inventory and mapping system for cultural heritage management.

### Installation

This is an Arches v5 "project" that works in conjunction with two other repos, the `stable/5.0.x-fpan` branch of the [legiongis/arches](https://github.com/legiongis/arches) repo (a slightly modified fork of the Arches 5.0 release), and legiongis/fpan-data(https://github.com/legiongis/fpan-data) (a complete Arches package). To install your own version of this project, begin by following the ([official v4 installation documentation](https://arches.readthedocs.io/en/stable/requirements-and-dependencies/)). After you have all dependencies installed and a virtual environment created, come back here.

With your virtual environment activated, enter a new directory and

- clone this project repo
       
        git clone https://github.com/legiongis/fpan
       
- clone the package repo [legiongis/fpan-data](https://github.com/legiongis/fpan-data)
       
        git clone https://github.com/legiongis/fpan-data
       
- clone the [legiongis/arches](https://github.com/legiongis/arches) repo and checkout the `stable/5.0.x-fpan` branch
       
        git clone https://github.com/legiongis/arches
        cd arches
        git fetch --all
        git checkout stable/5.0.x-fpan
        cd ..
       
- make settings_local.py in the project (place in `fpan/fpan`)

    this should contain all of your normal environment-specific variables, like database credentials, as well as two new variables:
   
       SECRET_LOG = "path/to/some/dir/outside/of/version/control"
       PACKAGE_PATH = "full/local/path/to/the/location/of/fpan-data/repo"
       
- enter the project directory and load the package (make sure elasticsearch is running)
    
        cd fpan
        python manage.py load_package -db

    - if that command ends in an error, run the following series of commands:
            
            python manage.py migrate
            python manage.py load_system_settings
            python manage.py load_package
        
- once loading is complete, you should be able to run the django dev server and view the database in a browser at `localhost:8000`
        
        python manage.py runserver
