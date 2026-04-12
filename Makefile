.PHONY: install test

install:
	poetry lock
	poetry install

test:
	poetry run pytest -v
