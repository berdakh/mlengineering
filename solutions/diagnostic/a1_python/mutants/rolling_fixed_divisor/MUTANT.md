Rolling mean includes the current element but always divides by `window`, so the first `window-1`
outputs are too small. Plausible "fixed the off-by-one, missed the warm-up" submission.
