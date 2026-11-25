# flowguard release candidate. TODO (milestone 2): fill in the recipes.
#
#   make model      package configs/model.toml + splits/v2.json as models/current/
#   make test       run the test suite
#   make predict    score the test experiments to predictions/test.csv
#   make serve      serve models/current on http://127.0.0.1:8000
#
# Variables can be overridden:  make model RAW=/path/to/skab        Recipes start with a TAB.

PY        ?= python
RAW       ?= data/raw/skab
SPLITS    ?= splits/v2.json
CONFIG    ?= configs/model.toml
MODEL_DIR ?= models/current
PORT      ?= 8000

export PYTHONPATH := src$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: model test predict serve clean

model:
	@echo "TODO: build $(MODEL_DIR) with python -m flowguard build-model"; exit 1

test:
	@echo "TODO: run the tests"; exit 1

predict:
	@echo "TODO"; exit 1

serve:
	@echo "TODO"; exit 1

clean:
	rm -rf models predictions
