.PHONY: install gen collect test run server loop reconcile

install:
	pip install --quiet pyyaml pytest jsonschema

gen:
	python -m factory.generate_capabilities --root $${FACTORY_ROOT:-$$HOME/Documents/code} --force

collect:
	python -m factory.main collect

test:
	pytest factory/tests/ -q

run:
	python -m factory.main run

server:
	python -m factory.server

loop:
	python -m factory.main loop --seconds 3600 --interval 2

reconcile:
	python -m factory.reconcile --once --verbose
