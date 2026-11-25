# Hint 1 - concept

**Lab.**

* Every threshold-free metric is a walk down the list of rows sorted by score. At each *distinct*
  score value you have a (TP, FP) pair. Everything else is arithmetic on those pairs. Rows with equal
  scores cannot be ordered, so they must be consumed together.
* A scorer has two phases with different data rights. `fit` may look at the rows it is given.
  `score` may look at one row and at what `fit` stored. If `score` computes a mean, something is wrong.
* Mahalanobis distance is the Euclidean norm *after whitening*. Whitening divides by the square roots
  of eigenvalues; an eigenvalue of zero is a division by zero. Decide what replaces it.
* The benchmark function has three row sets (dev, test, ignored) and one fitted quantity (the
  threshold). Ask of every line: which set does this line read?

**Challenge.**

* The decision compares a probability with a ratio of money. That only works if the probability is a
  probability. Which training choices change the average predicted value?
* The benefit of acting is not "customer value". It is customer value times the chance the action
  works, and only for customers who would have churned.
* The test months come after the training months. What should validation look like so that it warns
  you about what test will do?
