# SETTING UP THE DOCKER DEV ENVIRONMENT

> ⚠️ This process is a work in progress. `make` and `docker compose` work together to run `fpan` so the dev can run a single command to get a dev environment up and running, without installing legacy dependencies directly on the dev's machine. Both are needed to keep the `arches` Docker container flexible on startup.

> ⚠️ If you're running this on an Apple Silicon machine, set the following in Docker Desktop: Settings > General > Virtual Machine Options > Docker VMM

> ⚠️ If you're running this on an older version of Docker, you may need to replace all instances of `docker compose` with `docker-compose` in fpan-workspace/fpan/Makefile.

## Bugs

- Once you've set everything up, have shut down, and run `make dev` to continue working, you may see the following error at the bottom of the stack trace in the console output, after logging in using the browser. _There has been no meaningful impact as a result of this error_:

```
  File "/web_root/ENV/lib/python3.8/site-packages/django/db/models/query.py", line 439, in get
    raise self.model.MultipleObjectsReturned(
arches.app.models.models.UserXNotificationType.MultipleObjectsReturned: get() returned more than one UserXNotificationType -- it returned 2!
```

## Tip

After you've [Set Up A Workspace From Scratch](#set-up-a-workspace-from-scratch), you probably want to run these two commands only, unless something goes wrong or you need to start fresh:

```sh
cd fpan-workspace/fpan

# start working
make dev

# stop working
make dev-down
```

## Set Up A Workspace From Scratch

This will download the repos and docker images, and run the containers with test data. If you've already initialized (setup the database and elasticsearch), this will wipe everything and start fresh.

If you don't need test accounts and resources, run `make init-dev-clean` instead of the make command, below. This will save ~10-15 minutes on container startup time.

```sh
mkdir fpan-workspace && cd fpan-workspace

# clone our Arches 6.2 fork
git clone https://github.com/legiongis/arches
cd arches
git fetch --all
git checkout dev/6.2.x-hms-cli
cd ..

# clone this project and copy the Docker files to the workspace
git clone https://github.com/legiongis/fpan
cp fpan/docker/* .
mv ./settings_local.py fpan/fpan/

# run the fpan / Arches docker containers with mock accounts and resources
cd fpan
make init-dev
```

> `fpan` source code is mounted as a volume to the `arches` docker service, so open `fpan-workspace/fpan` in your host machine's IDE to make code changes. You should see your changes in the browser after reloading the page.

## Shut Down the Dev Environment and Persist Data

This will shut down the dev environment without wiping the database.

```sh
cd fpan-workspace/fpan

make dev-down
```

## Run the Dev Environment with Persisted Data

This will run the dev environment using an already-initialized database (or after running [Set Up A Workspace From Scratch](#set-up-a-workspace-from-scratch), or really `make init-dev` or `make init-dev-clean`). Also use this command when you want to keep working with data you've already created.

```sh
cd fpan-workspace/fpan

make dev
```

## Initialize the Dev Environment with No Test Data

This will set everything up from scratch, without adding test accounts and resources. This is much faster than the `make init-dev` command.

```sh
cd fpan-workspace/fpan

make init-dev-clean
```

## Running Tests

This will run all tests, assuming the dev environment is already running.

```sh
cd fpan-workspace/fpan

make test
```
