# Mutant: random 80/20 row split

The default of every tutorial. Here it trains on invoices issued after the ones it is tested on,
during a period when the late rate was rising, and it puts each customer's invoices on both sides.
It answers 'how well can I fill in missing outcomes in the past', which nobody asked.

Rejected by the split checks and `test_run_reports_sizes_and_prevalence`.
