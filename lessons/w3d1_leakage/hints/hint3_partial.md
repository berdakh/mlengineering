# Hint 3 - partial implementation

## `find_overlap_groups`

```python
ROW_KEY = ["datetime", *SENSOR_COLUMNS]          # no labels in the key

def find_overlap_groups(tidy, min_shared_rows=1):
    h = pd.util.hash_pandas_object(tidy[ROW_KEY], index=False)
    pairs = pd.DataFrame({"h": h.to_numpy(), "e": tidy["experiment_id"].to_numpy()}).drop_duplicates()
    shared = pairs[pairs.duplicated("h", keep=False)]
    counts = {}
    for _, members in shared.groupby("h")["e"]:
        ids = sorted(members)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                counts[(a, b)] = counts.get((a, b), 0) + 1
    # ... union-find over pairs with count >= min_shared_rows, then collect components of size > 1
```

## `honest_eval.py`

```python
LEAKY_COLUMNS = [...]                 # the three you found; justify each in LEAK_REPORT.md
REISSUE_KEY = ["customer_id", ...]    # columns a re-issue copies unchanged from the original

def prepare(df):
    df = df.sort_values(["issue_date", "invoice_id"], kind="stable")
    df = df.drop_duplicates(subset=REISSUE_KEY, keep="first")      # the first issue is the real one
    return df.drop(columns=LEAKY_COLUMNS).reset_index(drop=True)

def split(df):
    return df[df["issue_date"] < CUTOFF], df[df["issue_date"] >= CUTOFF]

def fit_model(train):
    pre = ColumnTransformer([
        ("num", SimpleImputer(strategy="median", add_indicator=True), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return make_pipeline(pre, RandomForestClassifier(...)).fit(train[FEATURES], train["paid_late"])
```

`evaluate` returns the dictionary described in the file's docstring; `scores` must be a Series indexed by
`invoice_id`. Left for you: which columns, which de-duplication key, and why `prior_late_rate` needs an
imputer (new customers have no history).
