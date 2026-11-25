# Milestone 1: one command rebuilds every number, table and figure of the evaluation report.
#
#   make evaluate          build whatever is out of date, ending with reports/evaluation.md
#   make clean             remove everything this Makefile builds (never the raw data)
#   make -q evaluate       exit 0 if everything is up to date
#
# Variables can be overridden on the command line:  make evaluate N_BOOT=200 BURN_IN=40
# The checks do exactly that, and they also pass PY=<the python running them>.
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

export PYTHONPATH := src$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: evaluate clean

evaluate: $(REPORT)

# TODO: the tidy table. Prerequisites: every raw CSV, and the code that reads them.
#       Recipe: $(PY) -m flowguard ingest --raw-dir $(RAW) --out $@
$(TIDY):
	@echo "TODO: write the rule for $@"; exit 1

# TODO: the results. Which files can change them? (Think: data, split, code.)
$(RESULTS):
	@echo "TODO: write the rule for $@"; exit 1

# TODO: the report. It must depend on the results and on the code that renders them, nothing else.
$(REPORT):
	@echo "TODO: write the rule for $@"; exit 1

clean:
	@echo "TODO: remove the three build directories"; exit 1
