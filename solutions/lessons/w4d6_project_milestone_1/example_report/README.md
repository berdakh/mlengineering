# Reference report, generated on the real SKAB data

`evaluation.md`, `figures/dev_differences.svg` and `results.json` were produced by the reference
solution in `../lab` with

```bash
cd solutions/lessons/w4d6_project_milestone_1/lab
make evaluate RAW=<repository>/data/raw/skab        # about 1 minute
```

on 2026-11-22 (Python 3.13.18; package versions in the report's Provenance table). They were copied
here unchanged. The code version is the repository commit checked out at generation time (`git
describe --always --dirty`); a `-dirty` suffix would mean uncommitted changes. In your own
milestone, commit first and then build (see the challenge).

A clean rebuild (`make clean && make evaluate`) in the authoring session gave byte-identical
`results.json` and `evaluation.md`. The development table equals the one printed by
`lessons/w4d5_model_choice/lab/decision_table.py`.
