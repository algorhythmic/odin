PYTHON ?= python3
GO ?= go

.PHONY: check docs contracts test demo orchestration-demo compatibility
check: docs contracts test

docs:
	$(PYTHON) scripts/validate_docs.py
	$(PYTHON) -m unittest discover -s scripts -p 'test_validate_docs.py' -v

contracts:
	$(PYTHON) scripts/validate_runtime.py
	$(GO) test ./...

test:
	PYTHONPATH=python $(PYTHON) -m unittest discover -s tests -v

demo:
	@test -n "$(STATE)" || (echo 'Set STATE to a new private directory outside this checkout'; exit 1)
	PYTHONPATH=python $(PYTHON) -m odin --state "$(STATE)" demo

orchestration-demo:
	@test -n "$(STATE)" || (echo 'Set STATE to a new private directory outside this checkout'; exit 1)
	PYTHONPATH=python $(PYTHON) -m odin --state "$(STATE)" orchestration-demo

compatibility:
	$(PYTHON) scripts/check_runtime.py --go "$(GO)"
