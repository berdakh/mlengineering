# Hint 1 — concept

**Lab.** Write the two statistics in words before coding. T² asks "how far along the directions normal
data varies in, measured in units of how much it usually varies there?". Q asks "how much of this row is
left over after projecting it onto those directions?". Both are computed on rows standardised with the
*fit* rows' mean and SD — the rows you are scoring must not influence the standardisation.

**Challenge.** Ask how the labels were produced and who the model will score. Labels come from reviewing
whole accounts; the model will score new customers. What does that imply for how you split the labelled
rows when you estimate performance? Then ask how many *independent* fraud examples the supervised model
really has: count fraudulent accounts, not fraudulent rows.
