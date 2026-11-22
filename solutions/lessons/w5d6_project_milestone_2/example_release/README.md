# Example release evidence (reference solution, real SKAB data)

Produced on 2026-11-22 from `../lab` (the reference project) with Python 3.13.18, FastAPI 0.165.0,
uvicorn 0.54.0, numpy 2.5.3, pandas 3.0.5, against the SKAB files fetched by `project/get_skab.py`.

| File | What it shows |
|---|---|
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | the release note a reviewer reads first |
| [API_TRANSCRIPT.md](API_TRANSCRIPT.md) | a real uvicorn process on 127.0.0.1 answering curl, then stopped |
| [parity.json](parity.json) | evaluation, batch CSV and API scores compared on all 46,806 rows of 35 experiments |

Commands (from `../lab`, `R` = path of the SKAB data):

```bash
make model RAW=$R            # 0.5 s
make test                    # 10 passed
make predict RAW=$R          # 7,359 rows, 7 test experiments -> predictions/test.csv
PYTHONPATH=src python scripts/parity_report.py --model models/current --raw $R --out parity.json
```
