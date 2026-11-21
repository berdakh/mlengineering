# Mutant: top_level_only

Configs are compared section by section without flattening, so the report says `split` differs and shows both whole sections rather than naming `split.seed`. Caught by the dotted-key check.

Changed file: `src/pumpwatch/compare.py`
