# flowguard milestone 4: the monitoring demonstration.
#
#   make monitor-demo     replay scenarios/demo.toml through the service, write reports/monitoring_demo.md
#   make test             run the test suite
#   make clean            remove reports/
#
# Without make:  PYTHONPATH=src python -m flowguard monitor-demo --raw $(RAW) --splits splits/v2.json \
#                    --scenario scenarios/demo.toml --out reports
# Recipes start with a TAB.

PY       ?= python
RAW      ?= data/raw/skab
SPLITS   ?= splits/v2.json
SCENARIO ?= scenarios/demo.toml
OUT      ?= reports

export PYTHONPATH := src$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: monitor-demo test clean

monitor-demo:
	$(PY) -m flowguard monitor-demo --raw $(RAW) --splits $(SPLITS) --scenario $(SCENARIO) --out $(OUT)

test:
	$(PY) -m pytest tests -q

clean:
	rm -rf $(OUT)
