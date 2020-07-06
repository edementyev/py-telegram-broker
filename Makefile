# original file https://github.com/aiogram/bot/blob/master/Makefile
include .env

tail := 200
PYTHONPATH := $(shell pwd):${PYTHONPATH}

PROJECT := py-telegram-broker
LOCALES_DOMAIN := bot
LOCALES_DIR := locales
VERSION := 0.1.0
PIPENV_VERBOSITY := -1

py := pipenv run
python := $(py) python

reports_dir := reports

package_dir := app
code_dir := $(package_dir) tests

# =================================================================================================
# Base
# =================================================================================================

default:help

help:
	@echo "py-telegram-broker"

# =================================================================================================
# Development
# =================================================================================================

requirements:
	pipenv lock -r > ./requirements.txt

seed-isort-config:
	$(py) seed-isort-config

isort:
	$(py) isort --recursive .

black:
	$(py) black .

flake8:
	$(py) flake8 .

mypy:
	$(py) mypy $(package_dir)

mypy-report:
	$(py) mypy $(package_dir) --html-report $(reports_dir)/typechecking

lint: black flake8 seed-isort-config isort

entrypoint:
	pipenv run bash ../docker-entrypoint.sh ${args}

texts-update:
	$(py) pybabel extract . \
    	-o ${LOCALES_DIR}/${LOCALES_DOMAIN}.pot \
    	--project=${PROJECT} \
    	--version=${VERSION} \
    	--copyright-holder=Illemius \
    	-k __:1,2 \
    	--sort-by-file -w 99
	$(py) pybabel update \
		-d ${LOCALES_DIR} \
		-D ${LOCALES_DOMAIN} \
		--update-header-comment \
		-i ${LOCALES_DIR}/${LOCALES_DOMAIN}.pot

texts-compile:
	$(py) pybabel compile -d locales -D bot

texts-create-language:
	$(py) pybabel init -i locales/bot.pot -d locales -D bot -l ${language}

crawl:
	$(py) scrapy crawl sets

scrape:
	$(py) scrapy shell ${url}

alembic:
	PYTHONPATH=$(shell pwd):${PYTHONPATH} $(py) alembic ${args}

migrate:
	PYTHONPATH=$(shell pwd):${PYTHONPATH} $(py) alembic upgrade head

migration:
	PYTHONPATH=$(shell pwd):${PYTHONPATH} $(py) alembic revision --autogenerate -m "${message}"

downgrade:
	PYTHONPATH=$(shell pwd):${PYTHONPATH} $(py) alembic downgrade -1

_beforeStart: docker-db migrate requirements

_app:
	$(py) python -m core

start:
	$(MAKE) _beforeStart
	$(MAKE) _app

# =================================================================================================
# Docker
# =================================================================================================

docker-config:
	docker-compose config

docker-ps:
	docker-compose ps

docker-build:
	docker-compose build

docker-db:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d redis db

docker-db-stop:
	docker-compose stop redis db

docker-up:
	docker-compose up -d --remove-orphans

docker-stop:
	docker-compose stop

docker-down:
	docker-compose down

docker-destroy:
	docker-compose down -v --remove-orphans

docker-logs:
	docker-compose logs -f --tail=${tail} ${args}

# =================================================================================================
# Application in Docker
# =================================================================================================

app-create: _beforeStart docker-db-stop docker-build docker-stop docker-up

app-logs:
	$(MAKE) docker-logs args="bot"

app-stop: docker-stop

app-down: docker-down

app-start: docker-stop docker-up

app-destroy: docker-destroy
