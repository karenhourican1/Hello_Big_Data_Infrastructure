.PHONY: \
	build \
	deploy \
	run_local \
	test \
	test_api \
	logs \

.DEFAULT_GOAL:=help

SHELL=bash

export DOCKER_REPOSITORY=XXXX.dkr.ecr.us-east-1.amazonaws.com
export DOCKER_FILE=docker/Dockerfile
export DOCKER_COMPOSE_FILE=docker/docker-compose.yml

export IMAGE_TAG=$(shell poetry version -s)
export SERVICE_NAME=$(poetry version | awk '{print $1}')
export IMAGE_NAME=${DOCKER_REPOSITORY}/${SERVICE_NAME}
export GIT_REPO=$(shell git config --get remote.origin.url | sed -E 's/^\s*.*:\/\///g')
export GIT_COMMIT=$(shell git rev-parse HEAD)

test:
	pytest -cov=bdi_api --cov-report=html

build:
	@echo "Building image $(IMAGE_NAME):$(IMAGE_TAG)"
	docker compose -f ${DOCKER_COMPOSE_FILE} build ${SERVICE_NAME}
	IMAGE_TAG=latest docker compose -f ${DOCKER_COMPOSE_FILE} build ${SERVICE_NAME}


run_local: build
	docker compose -f ${DOCKER_COMPOSE_FILE} stop
	docker compose -f ${DOCKER_COMPOSE_FILE} up -d
	@echo "You can check now http://localhost:8080/docs"

test_api: run_local
	st run --checks all http://localhost:8080/openapi.json -H "Authorization: Bearer TOKEN"

logs:
	docker compose -f ${DOCKER_COMPOSE_FILE} logs ${SERVICE_NAME}

config:
	docker compose -f ${DOCKER_COMPOSE_FILE} config
