
env:
	virtualenv --always-copy env

init:
	env/bin/pip install -r requirements.txt
	env/bin/pip install -e .

run:
	nagini $(file)

test:
	env/bin/pytest tests/run_tests.py

clean:
	rm -r env

.PHONY: env init run test clean