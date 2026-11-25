# Hint 1: concepts

* A structured log line is a dictionary serialised once. Build the dictionary, then `json.dumps` it;
  never build JSON by string concatenation.
* Prometheus histogram buckets answer "how many observations were <= this bound". Each line therefore
  includes all the smaller buckets. Keep per-interval counts internally if you like, but render running
  totals.
* In Starlette, an exception raised inside the endpoint is handled by the *outermost* middleware.
  From your middleware's point of view `call_next` raises; it does not return a 500.
* A label value must come from a small set you could write down in advance.
* For the challenge: an SLI is good events / valid events. Ask "whose fault was it?" to decide validity,
  and "what does the user feel?" to decide what good means.
