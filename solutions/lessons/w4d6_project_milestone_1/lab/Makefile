# Milestone 1: one command rebuilds every number, table and figure of the evaluation report.
#
#   make evaluate          build whatever is out of date, ending with reports/evaluation.md
#   make clean             remove everything this Makefile builds (never the raw data)
#   make -q evaluate       exit 0 if everything is up to date (nothing would run)
#
# Override any variable on the command line, e.g.  make evaluate N_BOOT=200 BURN_IN=40
# Recipes must start with a TAB character.

PY      ?= python
RAW     ?= data/raw/skab
SPLITS  ?= splits/v2.json
BURN_IN ?= 100
N_BOOT  ?= 2000
SEED    ?= 0

TIDY    := data/interim/skab.csv
RESULTS := results/results.json
REPORT  := reports/evaluation.md
SRC     := $(wildcard src/flowguard/*.py)

export PYTHONPATH := src$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: evaluate clean

evaluate: $(REPORT)

# Make compares timestamps: the tidy table is rebuilt when any raw CSV or the loading code is newer.
$(TIDY): $(wildcard $(RAW)/*/*.csv) src/flowguard/data.py src/flowguard/pipeline.py
	$(PY) -m flowguard ingest --raw-dir $(RAW) --out $@

$(RESULTS): $(TIDY) $(SPLITS) $(SRC)
	$(PY) -m flowguard evaluate --tidy $(TIDY) --splits $(SPLITS) --out $@ \
		--burn-in $(BURN_IN) --n-boot $(N_BOOT) --seed $(SEED)

$(REPORT): $(RESULTS) src/flowguard/pipeline.py src/flowguard/svgplot.py
	$(PY) -m flowguard report --results $(RESULTS) --out $@

clean:
	rm -rf data/interim results reports
