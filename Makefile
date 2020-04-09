
.DEFAULT_GOAL := test

ifeq (, $(shell which pip3))
	pip := $(shell which pip3)
else
	pip := $(shell which pip)
endif

pytest := $(shell which pytest)

env:
	conda create --name 2vyper python=3.6
	conda activate 2vyper

install:
	${pip} install .

dev-install:
	${pip} install -r requirements.txt
	${pip} install -e .

run:
	2vyper $(file)

test:
	${pytest} tests/run_tests.py

test-carbon:
	${pytest} --verifier carbon tests/run_tests.py

clean:
	find ./src -type d -name __pycache__ -exec rm -r {} \+

clean-egg:
	find ./src/ -type d -name *.egg-info -exec rm -r {} \+

clean-env: clean clean-egg
	conda env remove --name 2vyper

.PHONY: env install dev-install run test test-carbon clean clean-egg clean-env
