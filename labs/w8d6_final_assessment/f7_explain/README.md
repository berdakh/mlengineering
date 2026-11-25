# f7 - Explain and defend an ML decision (parallel form of b4)

**Time box: 20 minutes.** Sitting B, section 4 of 4. Written only; no code, no automated check.

## Scenario

You join a team that forecasts daily demand for a grocery chain: 120 stores, about 4,000 fresh
products, two years of daily sales. Store managers order fresh products every morning from the
forecast. Today the forecast is a *seasonal-naive* rule (same weekday last week, adjusted for known
holidays). Store managers complain about waste in summer; head office worries about empty shelves
during the coming December holidays, of which the data contains exactly two.

A teammate presents this result and the operations director wants a decision this week:

> "I trained a deep sequence model on all store-product-day rows. On a random 80/20 split of those
> rows the mean absolute percentage error (MAPE) is **9 %**; a gradient-boosted model gets 12 %.
> I propose we replace the forecaster in all stores before the holidays."

## Task

Write a memo to the operations director and the teammate in `lab/MEMO.md`, **at most 350 words**:

1. Your recommendation (replace / do not replace yet / replace in a limited form) in the first two sentences.
2. The two or three most important reasons, each tied to a specific property of this data or this
   evaluation - not generic caveats.
3. The smallest additional piece of evidence that would change or confirm your recommendation, and
   how long you estimate it takes to produce.
4. One tradeoff you are making deliberately.

Write for a reader who is technically literate but not an ML specialist. Prioritise.

## Acceptance criteria

Graded by rubric after you submit (see `../SUBMISSION.md`). The rubric looks at: correctness of the
technical reasoning, prioritisation, whether the recommendation is actionable, and clarity.

## Submit

`lab/MEMO.md`, time used.
