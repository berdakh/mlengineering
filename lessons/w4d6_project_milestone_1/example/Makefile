# Worked example (w4d6): a two-step report pipeline in 15 lines of make.
#
#   make -C lessons/w4d6_project_milestone_1/example            # build report.md
#   make -C lessons/w4d6_project_milestone_1/example -n         # show what WOULD run
#   make -C lessons/w4d6_project_milestone_1/example -q; echo $? # 0 = up to date
#
# Input: the SYNTHETIC churn case from w4d5 (../../w4d5_model_choice/challenge/case/predictions.csv).

PY   ?= python
DATA := ../../w4d5_model_choice/challenge/case/predictions.csv

.PHONY: all clean
all: build/report.md

build/summary.json: $(DATA) summarise.py
	@mkdir -p build
	$(PY) summarise.py $(DATA) $@

build/report.md: build/summary.json render.py
	$(PY) render.py $< $@

clean:
	rm -rf build
