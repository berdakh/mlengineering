# w8d3 hint 1 — concept

**Estimation worksheet.** Every function is one line of arithmetic once the units are clear. Write the
units next to each quantity before you write code: requests per day ÷ seconds per day = requests per
second; requests per second × seconds of service per request = busy servers (Little's law, `L = λW`).

**Labels available.** A prediction made `a` days ago is labelled only if `a ≥ delay`. If predictions are
spread evenly over the last `window` days, what fraction of those days are old enough?

**Design review (challenge).** Before you comment on anything, ask of every input to the model: *does it
exist at the moment the prediction is made?* Then ask of the evaluation: *does it measure what the
system will face after launch?* Those two questions find the blockers in most design docs.
