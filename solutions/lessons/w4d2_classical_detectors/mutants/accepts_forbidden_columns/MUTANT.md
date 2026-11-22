# No check on feature columns

check_columns only lists the columns. A frame that still contains t, datetime or the label is accepted,
and a tree model will happily learn the experimental protocol (elapsed time) or the label itself.
