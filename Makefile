DC_UP_D = docker compose up -d
DC_DOWN = docker compose down
DC_DOWN_V = docker compose down -v
DC_EXEC_ARCHES = docker compose exec arches
DC_LOGS_F = docker compose logs -f

MANAGE_PY = python manage.py
RUN_DJANGO_SERVER = $(MANAGE_PY) runserver 0:8000

MKDIR_FPAN_LOGS = mkdir -p ./fpan/logs

YARN_INSTALL = yarn install

# purple/pink log printing
PRINT_MESSAGE = @printf "\n\033[35m%s\033[0m\n\n"


__await_dependencies: WAIT_TIME=30
__await_dependencies:
	$(PRINT_MESSAGE) "Waiting ${WAIT_TIME} seconds for Postgres, ElasticSearch, and RabbitMQ containers to boot up..."
	@sleep $(WAIT_TIME)

# TODO: should `MKDIR_FPAN_LOGS` be moved to setup_hms.py?

# Run once -- Initial setup of dev environment and fpan with test data -- postgres && elasticsearch config, migrations, indexing
# ⚠️ This will delete all pre-existing data from the db and elasticsearch, if any exists -- accounts, resources, indexes
init-dev:
	$(DC_DOWN_V) && $(DC_UP_D)
	$(MAKE) __await_dependencies
	$(MKDIR_FPAN_LOGS)
	$(DC_EXEC_ARCHES) $(MANAGE_PY) setup_hms \
		--test-accounts \
		# --test-resources  # NOTE: as of the merging of PR #295, `--test-resources` fails
	$(YARN_INSTALL)

# Run once -- Initial setup of dev environment and fpan, without test data -- clean slate
# ⚠️ This will delete all pre-existing data from the db and elasticsearch, if any exists -- accounts, resources, indexes
init-dev-clean:
	$(DC_DOWN_V) && $(DC_UP_D)
	$(MAKE) __await_dependencies
	$(MKDIR_FPAN_LOGS)
	$(DC_EXEC_ARCHES) $(MANAGE_PY) setup_hms
	$(YARN_INSTALL)


HOST_DJANGO_PORT=8004

# Run the dev environment using an already-initialized fpan environment (after running init-dev or init-dev-clean once)
dev:
	$(DC_UP_D)
	$(PRINT_MESSAGE) "View fpan in the browser at http://localhost:${HOST_DJANGO_PORT}"
	$(DC_EXEC_ARCHES) $(RUN_DJANGO_SERVER)


# Stop running the dev environment and allow data to persist
dev-down:
	$(DC_DOWN)


# Stop running the dev environment and wipe all persistant data 
dev-down-delete-data:
	$(DC_DOWN_V)


# Run the test suite (assumes the containers are running)
test:
	$(DC_EXEC_ARCHES) $(MANAGE_PY) test tests.test_suite


# Access django/arches python management shell
django-shell:
	$(DC_EXEC_ARCHES) $(MANAGE_PY) shell


# Open a bash shell in the arches container to run arbitrary commands.
arches-bash:
	$(DC_EXEC_ARCHES) bash


# Run a foreground process that auto-reloads celery when celery tasks are changed
autoreload-celery:
	$(DC_EXEC_ARCHES) $(MANAGE_PY) autoreload_celery


# Log commands -- watch logs for db, elasticsearch, and rabbitmq

logs-db:
	$(DC_LOGS_F) db


logs-elasticsearch:
	$(DC_LOGS_F) elasticsearch


logs-rabbitmq:
	$(DC_LOGS_F) rabbitmq
