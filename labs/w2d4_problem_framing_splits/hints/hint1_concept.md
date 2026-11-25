# Hint 1 - concept (challenge)

Two different clocks are attached to every row of the churn table:

* the **feature clock**: when the snapshot was taken (`month`);
* the **label clock**: when the outcome it records became *fully* known.

A split is honest when it could have been carried out by someone standing at the training date with
no knowledge of later events. Ask of every row: *on the day the model was fitted, had this row's
label finished happening?* and of every evaluation row: *is its label finished happening now, for
positives and negatives alike?*

For the lab's SKAB split the two clocks coincide (the label of a timestamp is known with it), which
is why only the *group* question mattered there. Here both questions matter, and they are independent:
answer the time question and the customer question separately, then intersect.

For the framing: start from the sentence "Because of the model, ___ will ___ instead of ___." If you
cannot fill it in, you do not yet have a decision, and nothing else in the document can be right.
The capacity limit in the brief (5 %) is the strongest clue about which metric matches the decision.
