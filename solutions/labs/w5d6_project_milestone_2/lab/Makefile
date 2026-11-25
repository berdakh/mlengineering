# flowguard release candidate: build the model bundle, test every layer, serve, predict.
#
#   make model      package configs/model.toml + splits/v2.json as models/current/
#   make test       run the test suite (unit, integration, API, parity)
#   make predict    score the test experiments to predictions/test.csv
#   make serve      serve models/current on http://127.0.0.1:8000 (Ctrl-C to stop)
#
# Variables can be overridden:  make model RAW=/path/to/skab
# Recipes start with a TAB.

PY        ?= python
RAW       ?= data/raw/skab
SPLITS    ?= splits/v2.json
CONFIG    ?= configs/model.toml
MODEL_DIR ?= models/current
PORT      ?= 8000

export PYTHONPATH := src$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: model test predict serve clean

model: $(MODEL_DIR)/MANIFEST.json

$(MODEL_DIR)/MANIFEST.json: $(CONFIG) $(SPLITS) $(wildcard src/flowguard/*.py)
	$(PY) -m flowguard build-model --config $(CONFIG) --splits $(SPLITS) --raw $(RAW) --out $(MODEL_DIR)

test:
	$(PY) -m pytest tests -q

predict: model
	$(PY) -m flowguard predict-batch --model $(MODEL_DIR) --raw $(RAW) --splits $(SPLITS) --split test --out predictions/test.csv

serve: model
	FLOWGUARD_MODEL_DIR=$(MODEL_DIR) $(PY) -m uvicorn --factory flowguard.api:app_from_env --host 127.0.0.1 --port $(PORT)

clean:
	rm -rf models predictions
