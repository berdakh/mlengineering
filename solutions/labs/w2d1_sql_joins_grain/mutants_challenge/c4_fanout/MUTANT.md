# Mutant: c4_fanout

One big join across three independent one-to-many branches, then SUM. The key is still unique (one row per
site), so the grain *of the output* is right while every sum is inflated: the declared key says nothing
about the grain of the intermediate rows being aggregated.

Changed file: `queries/c4_site_scorecard.sql`
