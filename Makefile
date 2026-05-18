DOCKER   = /Applications/Docker.app/Contents/Resources/bin/docker
COMPOSE  = $(DOCKER) compose
PYTEST   = backend/.venv/bin/pytest
UV       = $(HOME)/.local/bin/uv

.PHONY: dev dev-down test test-v test-k install help

## Поднять весь стек локально (бэк + фронт + postgres)
dev:
	$(COMPOSE) up

dev-down:
	$(COMPOSE) down

## Установить/обновить dev-зависимости бэкенда
install:
	cd backend && $(UV) venv .venv --python 3.12 && $(UV) pip install -r requirements-dev.txt

## Запустить все тесты (требует запущенного Docker)
test:
	cd backend && .venv/bin/pytest

## Запустить тесты с подробным выводом
test-v:
	cd backend && .venv/bin/pytest -v

## Запустить конкретный тест: make test-k k=test_name
test-k:
	cd backend && .venv/bin/pytest -k "$(k)" -v

help:
	@grep -E '^##' Makefile | sed 's/## //'
