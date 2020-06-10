SHELL := /bin/bash
.DEFAULT_GOAL := help
MAKE_NPROCS ?= $(shell nproc)
CREME_LANGUAGE ?= fr


## Upgrade the Python requirements
.PHONY: update-requirements
update-requirements:
	pip install --upgrade -r creme/requirements-dev.txt


## Upgrade the Python requirements, run the migrations, the creme_populate and generatemedia commands
.PHONY: update
update: update-requirements
	python manage.py migrate
	python manage.py creme_populate
	python manage.py generatemedia


## Generate the media files
.PHONY: media
media:
	python manage.py generatemedia


## Run the Django test suite
.PHONY: test
test:
	python manage.py test --noinput --parallel=${MAKE_NPROCS} $(filter-out $@,$(MAKECMDGOALS))


## Run the Django test suite and generate coverage reports
.PHONY: test-cov
test-cov:
	COVERAGE_PROCESS_START=.coveragerc coverage run --source creme/ manage.py test --noinput --parallel=${MAKE_NPROCS} $(filter-out $@,$(MAKECMDGOALS))
	coverage combine
	coverage report
	coverage html


## Run the Javascript test suite
.PHONY: karma
karma: media
	node_modules/.bin/karma start .karma.conf.js --browsers=FirefoxHeadless --targets=$(filter-out $@,$(MAKECMDGOALS))


## Run the Javascript test suite in CI
.PHONY: karma-ci
karma-ci: media
	node_modules/.bin/karma start .circleci/.karma.conf.js --targets=$(filter-out $@,$(MAKECMDGOALS))


## Run the application
.PHONY: serve
serve: media
	python manage.py runserver


## Run the Javascript linters
.PHONY: eslint
eslint:
	git diff --name-only origin/master creme/ | { grep '.js$$' || true; } | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--format stylish \
			--quiet


## Validates the Python imports with isort
.PHONY: isort-check
isort-check:
	git diff --name-only origin/master creme/ | { grep '.py$$' || true; } | xargs --no-run-if-empty \
		isort --check --diff --atomic --verbose


## Sort the Python imports with isort
.PHONY: isort-fix
isort-fix:
	git diff --name-only origin/master creme/ | { grep '.py$$' || true; } | xargs --no-run-if-empty \
		isort --atomic --verbose


## Validates the Python code with flake8
.PHONY: flake8
flake8:
	flake8 creme


## Run all the Python linters
.PHONY: lint
lint: isort-check flake8


## Collect the messages to translate
.PHONY: gettext-collect
gettext-collect:
	$(eval appdirs := $(or $(filter-out $@,$(MAKECMDGOALS)), $(shell find creme/ -maxdepth 1 -type d|grep -E 'creme/[^_]+')))

	@for appdir in ${appdirs}; do (\
		pushd $${appdir} && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" -i "tests.py" -e "html,txt,py,xml" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} -i "*/js/tests/*" -e js && \
		popd \
	); done


## Compile the translation files
.PHONY: gettext-compile
gettext-compile:
	django-admin.py compilemessages -l ${CREME_LANGUAGE}


## Print this message
.PHONY: help
help:
	@printf "Usage\n";

	@awk '{ \
			if ($$0 ~ /^.PHONY: [a-zA-Z\-\\_0-9]+$$/) { \
				helpCommand = substr($$0, index($$0, ":") + 2); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^[a-zA-Z\-\\_0-9.]+:/) { \
				helpCommand = substr($$0, 0, index($$0, ":")); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^##/) { \
				if (helpMessage) { \
					helpMessage = helpMessage"\n                     "substr($$0, 3); \
				} else { \
					helpMessage = substr($$0, 3); \
				} \
			} else { \
				if (helpMessage) { \
					print "\n                     "helpMessage"\n" \
				} \
				helpMessage = ""; \
			} \
		}' \
		$(MAKEFILE_LIST)
