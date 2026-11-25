# Hint 1 — concepts (lab and challenge)

**Lab**

- Think of configuration loading as a pipeline with three separable stages:
  *collect* (defaults, file, overrides → one raw nested dict), *check* (keys, types, ranges),
  *freeze* (build immutable objects). Bugs in this lab are almost always two stages tangled
  together — for example applying overrides after the objects have been built and checked.
- The snapshot question is "what did the computation receive?", not "what did the user type?".
  There is exactly one object that answers it.
- For logging, ask of every line you write: *is this module the application, or a library the
  application uses?* Only the application may decide where records go.
- A seed is an argument. If you cannot point at the function parameter through which it travels
  from the config to the code that draws random numbers, it is not threaded.

**Challenge**

- A nested mapping and a flat mapping with dotted keys carry the same information. Differences are
  much easier to compute on one of the two.
- "The same data" is a claim about content. Which field of your run directory is a statement about
  content, and which is only a statement about location?
- Decide what a *complete* run directory is before reading any file, and check for it in one place.
