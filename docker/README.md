# SETTING UP THE DOCKER DEV ENVIRONMENT

`make` and `docker compose` work together to simplify the process of setting up a dev environment and running `fpan`, specifically in development. Docker is currently not being used in production.

Core Arches (and thus Django) runs in the `arches` container defined in [docker-compose.yml](./docker-compose.yml). Django/Arches and `fpan` commands run inside this container. Postgres, Elastic Search, and RabbitMQ run in their own containers.

`legiongis/arches#dev/6.2.x-hms-cli`, `legiongis/arches-extensions`, and `fpan` repos are mounted as volumes to the `arches` docker service so they can all be edited. Open these directories on your host machine to make code changes. You should see your changes to `fpan`, `arches`, and `arches-extensions` reflected immediately after reloading the page.

> ⚠️ If you're running the Docker dev environment on an Apple Silicon machine, set the following in Docker Desktop: Settings > General > Virtual Machine Options: ✅ Apple Virtualization Framework, ✅ Use Rosetta for x86_64/amd64 emulation on Apple Silicon, ✅ VirtioFS.

## Bugs

- 25.06.23 - As of a recent PR merge, `python manage.py setup_hms --test-resources` is broken. Until this is fixed, `make init-dev` only creates test accounts and no test resources.

- Once you've set everything up, have shut down, and run `make dev` to continue working, you may see the following error at the bottom of the stack trace in the Django console output, after logging into the main site. _You can ignore this error_:

```
  File "/web_root/ENV/lib/python3.8/site-packages/django/db/models/query.py", line 439, in get
    raise self.model.MultipleObjectsReturned(
arches.app.models.models.UserXNotificationType.MultipleObjectsReturned: get() returned more than one UserXNotificationType -- it returned 2!
```

## Start and Stop the Dev Environment

After you've [Set Up A Workspace From Scratch](#set-up-a-workspace-from-scratch), you'll mostly be running these two commands:

```sh
cd fpan-workspace/fpan

# start working
# spins up the docker containers and runs the django server
make dev

# stop working
# shuts down the docker containers
make dev-down
```

## Set Up A Workspace From Scratch

This will download the repos and docker images, initialize the containers with test accounts and resources, and install javascript dependencies. The first time you do this, it will take several minutes, as Docker has to download large images. After the first time, Docker will use its local cache.

> If you've already set up the dev environment, any make command containing `init-dev` will wipe all persistent data from the db and elasticsearch.

> If you don't need test accounts and resources, run `make init-dev-clean` instead of the make command, below. This will save several minutes on container startup time.

After setting up the workspace, you can start and stop the containers with [these commands](#start-and-stop-the-dev-environment).

Run Docker, then paste the following code block into your terminal after `cd`ing to an appropriate directory:

```sh
# create the workspace
mkdir fpan-workspace && cd fpan-workspace

# clone our Arches 6.2 fork
git clone \
  --branch=dev/6.2.x-hms-cli \
  --single-branch \
  https://github.com/legiongis/arches

# clone our Arches extensions
git clone https://github.com/legiongis/arches-extensions
cd arches-extensions
git checkout e349934
cd ..

# clone this project and copy the Docker and files and local settings
git clone https://github.com/legiongis/fpan
cp ./fpan/docker/* .
mv ./settings_local.py fpan/fpan/
cp ./edit_dot_env .env

# download docker images and initialize fpan
cd fpan
make init-dev
```

## Running Tests

This will run all tests, assuming you've already run `make dev` to spin up the dev environment.

```sh
cd fpan-workspace/fpan

make test
```

## Additional Make Commands

- Run a celery auto-reloader, if you want to work on a celery task:
  - `make autoreload-celery`
- Run the Django shell in your terminal:
  - `make django-shell`
- Wipe all db and elasticsearch data. Afterwards, you'll want to run some `init-dev` command again.
  - `make dev-down-delete-data`
- Open a bash shell in the `arches` container to run arbitrary commands, like Django management commands and `pip install`:
  - `make arches-bash`
- Watch logs for `db`, `elasticsearch`, and `rabbitmq` containers.
  - `make logs-db`, `make logs-elasticsearch`, `make logs-rabbitmq`

## Configuring Pyright LSP

This is bit odd. The issue is that the python environment is inside the arches docker container, but fpan is on the host machine. On Mac and Windows*, to allow the LSP to work as intended (allow for jump to definition, docs, completion), we must have a copy of the container's venv directory on the host machine, since that's where the LSP is running. This copy will only be used for its site-packages directory, which pyright is configured to inspect.

```sh
cd fpan-workspace

docker cp fpan_arches:/opt/venv ./local_venv
```

You'll want to run this command after either of the following has occurred:
- The Docker dev environment has been set up
- The Python dependencies in the `arches` container have changed (either `arches` or `fpan` dependencies)

> `pip` commands should be run from within the `arches` container. See [Additional Make Commands](#additional-make-commands) to open a shell.

> *It's possible that on a Linux machine you could point pyright to the actual directory in the container, as it's really a directory on the host machine, though we have yet to successfully figure this out. To try this, edit pyrightconfig.json to look like this:

```json
{
  "venvPath": "path/to/parent/directory/of/venv/in/container",
  "venv": "name-of-venv-directory-found-in-venvPath",
  "extraPaths": [
    "../arches",
    "../arches-extensions"
  ]
}
```
