SHELL := /bin/bash

.DEFAULT_GOAL := help

VENV_DIR ?= .venv
VENV_BOOTSTRAP_PYTHON ?= python3.13
VENV_PYTHON := $(CURDIR)/$(VENV_DIR)/bin/python

TEST_RUNNER_IMAGE ?= medical-platform-python-test-runner:local
PYTEST_ARGS ?= -q -s -p no:cacheprovider

DOCKER_COMPOSE ?= docker compose
E2E_COMPOSE_FILE ?= tests/e2e/docker-compose.yml
E2E_COMPOSE_PROJECT ?= medical-platform-e2e
E2E_NETWORK ?= $(E2E_COMPOSE_PROJECT)_default
CURL_IMAGE ?= curlimages/curl:8.7.1
NEWMAN_IMAGE ?= postman/newman:6-alpine
E2E_PATIENT_SERVICE_URL ?= http://patient-service:8081
E2E_APPOINTMENT_SERVICE_URL ?= http://appointment-service:8082
E2E_PRESCRIPTION_SERVICE_URL ?= http://prescription-service:8083
E2E_NOTIFICATION_SERVICE_URL ?= http://notification-service:8084

LOCAL_REGISTRY_HOST ?= 10.10.10.10
LOCAL_REGISTRY_PORT ?= 5000
IMAGE_REGISTRY ?= $(LOCAL_REGISTRY_HOST):$(LOCAL_REGISTRY_PORT)
IMAGE_NAMESPACE ?=
IMAGE_TAG ?= latest
IMAGE_REPOSITORY_PREFIX := $(IMAGE_REGISTRY)
ifneq ($(strip $(IMAGE_NAMESPACE)),)
IMAGE_REPOSITORY_PREFIX := $(IMAGE_REGISTRY)/$(IMAGE_NAMESPACE)
endif

APP_SERVICES := \
	auth-service \
	patient-service \
	appointment-service \
	prescription-service \
	notification-service

SERVICE_DIRS := $(addprefix services/,$(APP_SERVICES))
DASHBOARD_SERVICE ?= dashboard

.PHONY: help list install test-runner-build test-unit test test-all test-e2e e2e-up e2e-wait e2e-newman e2e-down app-images-build app-images-push

help:
	@printf '%s\n' 'Medical Platform service commands'
	@printf '%s\n' ''
	@printf '%s\n' '기본'
	@printf '  %-30s %s\n' 'make install' 'Python venv를 만들고 서비스 의존성을 설치합니다.'
	@printf '%s\n' ''
	@printf '%s\n' '테스트'
	@printf '  %-30s %s\n' 'make test-unit' 'Docker Python 러너에서 FastAPI 서비스 pytest를 실행합니다.'
	@printf '  %-30s %s\n' 'make test' 'make test-unit과 같은 기본 테스트입니다.'
	@printf '  %-30s %s\n' 'make test-all' '단위 테스트와 Docker Compose E2E 테스트를 실행합니다.'
	@printf '  %-30s %s\n' 'make test-e2e' 'Docker Compose에서 PostgreSQL/MongoDB/Kafka 기반 E2E 시나리오를 실행합니다.'
	@printf '  %-30s %s\n' 'make e2e-up' 'E2E Docker Compose stack을 시작합니다.'
	@printf '  %-30s %s\n' 'make e2e-wait' 'Docker curl 컨테이너로 E2E 서비스 준비 상태를 확인합니다.'
	@printf '  %-30s %s\n' 'make e2e-newman' 'Docker Newman 컨테이너로 E2E collection을 실행합니다.'
	@printf '  %-30s %s\n' 'make e2e-down' 'E2E Docker Compose stack을 정리합니다.'
	@printf '%s\n' ''
	@printf '%s\n' '이미지'
	@printf '  %-30s %s\n' 'make app-images-build' '서비스와 dashboard Docker 이미지를 빌드합니다.'
	@printf '  %-30s %s\n' 'make app-images-push' '이미지를 빌드한 뒤 registry로 push합니다.'
	@printf '%s\n' ''
	@printf '%s\n' '이미지 변수 예시'
	@printf '  %-30s %s\n' 'IMAGE_TAG=dev make app-images-build' '기본 local registry에 dev 태그로 빌드합니다.'
	@printf '  %-30s %s\n' 'IMAGE_REGISTRY=ghcr.io IMAGE_NAMESPACE=org/repo make app-images-push' '외부 registry로 push합니다.'

list: help

install:
	@set -e; \
	if ! command -v $(VENV_BOOTSTRAP_PYTHON) >/dev/null 2>&1; then \
		printf '%s\n' '$(VENV_BOOTSTRAP_PYTHON) command not found. Set VENV_BOOTSTRAP_PYTHON=python3 to use another interpreter.' >&2; \
		exit 1; \
	fi; \
	$(VENV_BOOTSTRAP_PYTHON) -m venv $(VENV_DIR); \
	$(VENV_PYTHON) -m pip install --upgrade pip; \
	$(VENV_PYTHON) -m pip install \
		-r services/auth-service/requirements.txt \
		-r services/patient-service/requirements.txt \
		-r services/appointment-service/requirements.txt \
		-r services/prescription-service/requirements.txt \
		-r services/notification-service/requirements.txt; \
	printf '%s\n' 'Python venv is ready at $(VENV_DIR).'

test-runner-build:
	docker build -f tests/docker/Dockerfile -t $(TEST_RUNNER_IMAGE) .

test-unit: test-runner-build
	docker run --rm -v "$(CURDIR)":/workspace -w /workspace $(TEST_RUNNER_IMAGE) sh -c 'set -e; for service in $(SERVICE_DIRS); do printf "%s\n" "Running pytest for $$service"; (cd "$$service" && PYTHONPATH=. python -m pytest $(PYTEST_ARGS)); done'

test: test-unit

test-all: test-unit test-e2e

test-e2e:
	@set -e; \
	trap '$(DOCKER_COMPOSE) -p $(E2E_COMPOSE_PROJECT) -f $(E2E_COMPOSE_FILE) down -v --remove-orphans' EXIT INT TERM; \
	$(MAKE) e2e-up; \
	$(MAKE) e2e-wait; \
	$(MAKE) e2e-newman

e2e-up:
	$(DOCKER_COMPOSE) -p $(E2E_COMPOSE_PROJECT) -f $(E2E_COMPOSE_FILE) up -d --build

e2e-wait:
	docker run --rm --network $(E2E_NETWORK) \
		-v "$(CURDIR)/tests/e2e/scripts":/scripts:ro \
		-e E2E_PATIENT_SERVICE_URL="$(E2E_PATIENT_SERVICE_URL)" \
		-e E2E_APPOINTMENT_SERVICE_URL="$(E2E_APPOINTMENT_SERVICE_URL)" \
		-e E2E_PRESCRIPTION_SERVICE_URL="$(E2E_PRESCRIPTION_SERVICE_URL)" \
		-e E2E_NOTIFICATION_SERVICE_URL="$(E2E_NOTIFICATION_SERVICE_URL)" \
		-e E2E_WAIT_TIMEOUT_SECONDS \
		-e E2E_WAIT_SLEEP_SECONDS \
		$(CURL_IMAGE) sh /scripts/wait-for-services.sh

e2e-newman:
	mkdir -p tests/e2e/newman/reports
	docker run --rm --network $(E2E_NETWORK) -v "$(CURDIR)/tests/e2e":/etc/newman -w /etc/newman $(NEWMAN_IMAGE) run postman/medical-platform.postman_collection.json \
		-e newman/docker.postman_environment.json \
		--env-var patientServiceUrl="$(E2E_PATIENT_SERVICE_URL)" \
		--env-var appointmentServiceUrl="$(E2E_APPOINTMENT_SERVICE_URL)" \
		--env-var prescriptionServiceUrl="$(E2E_PRESCRIPTION_SERVICE_URL)" \
		--env-var notificationServiceUrl="$(E2E_NOTIFICATION_SERVICE_URL)" \
		--reporters cli,junit \
		--delay-request 1000 \
		--reporter-junit-export newman/reports/e2e.xml

e2e-down:
	$(DOCKER_COMPOSE) -p $(E2E_COMPOSE_PROJECT) -f $(E2E_COMPOSE_FILE) down -v --remove-orphans

app-images-build:
	@set -euo pipefail; \
	for service in $(APP_SERVICES); do \
		printf 'building %s/%s:%s\n' '$(IMAGE_REPOSITORY_PREFIX)' "$$service" '$(IMAGE_TAG)'; \
		docker build -t "$(IMAGE_REPOSITORY_PREFIX)/$$service:$(IMAGE_TAG)" "services/$$service"; \
	done; \
	printf 'building %s/%s:%s\n' '$(IMAGE_REPOSITORY_PREFIX)' '$(DASHBOARD_SERVICE)' '$(IMAGE_TAG)'; \
	docker build -t "$(IMAGE_REPOSITORY_PREFIX)/$(DASHBOARD_SERVICE):$(IMAGE_TAG)" "$(DASHBOARD_SERVICE)"

app-images-push: app-images-build
	@set -euo pipefail; \
	for service in $(APP_SERVICES) $(DASHBOARD_SERVICE); do \
		printf 'pushing %s/%s:%s\n' '$(IMAGE_REPOSITORY_PREFIX)' "$$service" '$(IMAGE_TAG)'; \
		docker push "$(IMAGE_REPOSITORY_PREFIX)/$$service:$(IMAGE_TAG)"; \
	done
