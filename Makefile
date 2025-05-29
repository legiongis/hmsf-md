DC_DOWN_V = docker compose down -v
DC_DOWN = docker compose down
DC_UP = docker compose up -d
DC_EXEC = docker compose exec
DC_EXEC_ARCHES = $(DC_EXEC) arches

ACTIVATE_ENV = . /web_root/ENV/bin/activate
MANAGE_PY = python manage.py

DJANGO_LOG_HOST_PATH = ./fpan/logs/django.log
DJANGO_LOG_CONTAINER_PATH = /web_root/fpan/$(DJANGO_LOG_HOST_PATH)

# direct django console output to both console and a log file
RUN_DJANGO_SERVER = $(MANAGE_PY) runserver 0.0.0.0:8000 2>&1 | tee $(DJANGO_LOG_CONTAINER_PATH)

SETUP_HMS_CLEAN_AND_RUNSERVER = touch $(DJANGO_LOG_HOST_PATH) && $(DC_EXEC_ARCHES) bash -c "$(ACTIVATE_ENV) && $(MANAGE_PY) setup_hms && $(RUN_DJANGO_SERVER)"

SETUP_HMS_WITH_TEST_DATA_AND_RUNSERVER = $(DC_EXEC_ARCHES) bash -c "$(ACTIVATE_ENV) && $(MANAGE_PY) setup_hms --test-accounts --test-resources && $(MANAGE_PY) es reindex_database && $(RUN_DJANGO_SERVER)"

# purple/pink log printing
PRINT_MESSAGE = @printf "\n\033[35m%s\033[0m\n\n"


__base_dev:
	$(PRINT_MESSAGE) $(START_MESSAGE)
	touch $(DJANGO_LOG_HOST_PATH)
	cd ./fpan && yarn install


__await_dependencies: WAIT_TIME=30
__await_dependencies:
	$(PRINT_MESSAGE) "Waiting ${WAIT_TIME} seconds for ElasticSearch and Postgres containers to boot up..."
	@sleep $(WAIT_TIME)


__base_init-dev: __base_dev
	$(DC_DOWN_V) && $(DC_UP)  # ‼️wipes persistent volumes (db, elasticsearch, etc...)
	$(MAKE) __await_dependencies


init-dev: START_MESSAGE="Initializing fpan with test accounts and resources. This will take 10 - 20 minutes..."
init-dev: __base_init-dev
	$(SETUP_HMS_WITH_TEST_DATA_AND_RUNSERVER)


init-dev-clean: START_MESSAGE="Initializing fpan with no test data. This will take 5 - 10 minutes..."
init-dev-clean: __base_init-dev
	$(SETUP_HMS_CLEAN_AND_RUNSERVER)


# Watch Django logs if you somehow lost the terminal session from some `dev` command in this file
django-logs:
	tail -f $(DJANGO_LOG_HOST_PATH)


# Run the dev environment using exisiting data (don't wipe the db and elasticsearch)
dev:
	$(DC_UP)
	$(MAKE) __await_dependencies
	$(DC_EXEC_ARCHES) bash -c "$(ACTIVATE_ENV) && $(RUN_DJANGO_SERVER)"


# Stop running the dev environment and allow data to persist
dev-down:
	$(DC_DOWN)


# Stop running the dev environment and wipe all persistant data 
dev-down-rm:
	$(DC_DOWN_V)


# Run the test suite (assumes the containers are running)
test:
	$(DC_EXEC_ARCHES) bash -c "$(ACTIVATE_ENV) && $(MANAGE_PY) test tests.test_suite"
