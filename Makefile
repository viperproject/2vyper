
env:
	virtualenv --always-copy env

init:
	env/bin/pip install -r requirements.txt

run:
	nagini $(file)

test:
	env/bin/pytest test/run_tests.py

clean:
	rm -r env

.PHONY: env init run test clean