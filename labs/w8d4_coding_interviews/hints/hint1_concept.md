# w8d4 hint 1 — which pattern?

Read only the line for the problem you are stuck on.

* **P1** What do you need to remember per sample, and per annotator within a sample?
* **P2** Both lists are sorted. Can a pointer into `alarms` ever need to move backwards?
* **P3** What is the only fact about the past you need for a key?
* **P4** Variance needs count, mean and spread per sensor. Is there a way to update them one value at a
  time without the cancellation of "mean of squares minus square of mean"?
* **P5** If someone gave you a candidate answer `X`, could you check quickly whether `X` is achievable?
* **P6** Which steps can run first? After one runs, which become available? How do you always pick the
  smallest available one cheaply?
* **Q1** What is the grain of `payments`? What happens to a trip row when it meets three payment rows?
* **Q2** A window function that numbers rows within each city, never giving two rows the same number.
* **Q3** For consecutive days, `day - (its position in the sorted list)` is constant.
