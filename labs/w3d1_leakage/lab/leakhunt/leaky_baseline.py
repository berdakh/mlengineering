"""The analysis you inherited. It runs, and it reports an excellent number. Do not trust it.

    python labs/w3d1_leakage/lab/leakhunt/leaky_baseline.py

Task: predict, when an invoice is ISSUED, whether it will be paid late (``paid_late``), so that
the credit team can call the customer early. The model will score invoices issued in the months
after the export. Data: labs/w3d1_leakage/data/invoices.csv (SYNTHETIC).
"""
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DATA = Path(__file__).resolve().parents[2] / "data" / "invoices.csv"


def main() -> None:
    df = pd.read_csv(DATA, parse_dates=["issue_date"])
    y = df["paid_late"]
    X = df.drop(columns=["paid_late", "invoice_id", "customer_id", "issue_date"])
    X = pd.get_dummies(X, columns=["segment", "industry"]).fillna(0.0)
    X = pd.DataFrame(StandardScaler().fit_transform(X), columns=X.columns, index=X.index)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0, stratify=y)
    model = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_train, y_train)
    ap = average_precision_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"rows {len(df)}, late rate {y.mean():.3f}")
    print(f"test average precision: {ap:.3f}")
    top = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False).head(5)
    print("top features:\n" + top.round(3).to_string())


if __name__ == "__main__":
    main()
