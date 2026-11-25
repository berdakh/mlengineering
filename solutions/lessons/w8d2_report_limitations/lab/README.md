# w8d2 lab files

* `report/check_report.py`: the report checker. `strip_markup`, `traced` and `check` raise
  `NotImplementedError`; the module docstring states the five rules and their finding codes.
* `report/TEMPLATE.md`: the section structure the checker expects. Copy it to your repository as
  `reports/TECHNICAL_REPORT.md` and write your report there.

Grade the checker with `python wb.py check w8d2`. Then run it on your own report:

```bash
python lessons/w8d2_report_limitations/lab/report/check_report.py ~/projects/flowguard/reports/TECHNICAL_REPORT.md \
    --results ~/projects/flowguard/reports/results.json
```
