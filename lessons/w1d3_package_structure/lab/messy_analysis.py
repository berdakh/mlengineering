# pump fault analysis -- exported from notebook "pump_v3_FINAL(2).ipynb"
# run from the repository root:  python lessons/w1d3_package_structure/lab/messy_analysis.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import *
from sklearn.model_selection import GroupShuffleSplit

df = pd.read_csv("data/synthetic/pump_vibration.csv")
fs = 256

rows = []
for u in df.unit_id.unique():
    d = df[df.unit_id == u]
    for w in d.window_id.unique():
        x = d[d.window_id == w].vibration.values
        x = pd.Series(x).interpolate(limit_direction="both").values
        f = {}
        f["unit_id"] = u
        f["window_id"] = w
        f["rms"] = np.sqrt(np.mean(x ** 2))
        f["line_length"] = np.sum(np.abs(np.diff(x)))
        f["p2p"] = x.max() - x.min()
        # band power low
        X = np.fft.rfft(x - x.mean())
        freqs = np.fft.rfftfreq(len(x), 1 / fs)
        psd = (np.abs(X) ** 2) / (fs * len(x))
        psd[1:-1] = 2 * psd[1:-1]
        m = (freqs >= 10) & (freqs < 40)
        f["bp_low"] = np.sum(psd[m]) * (freqs[1] - freqs[0])
        # band power high
        X = np.fft.rfft(x - x.mean())
        freqs = np.fft.rfftfreq(len(x), 1 / fs)
        psd = (np.abs(X) ** 2) / (fs * len(x))
        psd[1:-1] = 2 * psd[1:-1]
        m = (freqs >= 70) & (freqs < 110)
        f["bp_high"] = np.sum(psd[m]) * (freqs[1] - freqs[0])
        f["ratio"] = f["bp_high"] / f["bp_low"]
        f["temp"] = d[d.window_id == w].temperature_c.values[0]
        f["label"] = d[d.window_id == w].label.values[0]
        rows.append(f)
feat = pd.DataFrame(rows)
print(feat.shape)

cols = ["rms", "line_length", "p2p", "bp_low", "bp_high", "ratio", "temp"]
X = feat[cols].values
y = feat.label.values
X = StandardScaler().fit_transform(X)

gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=7)
tr, te = next(gss.split(X, y, groups=feat.unit_id))
clf = LogisticRegression(C=1.0, max_iter=1000)
clf.fit(X[tr], y[tr])
p = clf.predict_proba(X[te])[:, 1]
print("test units", sorted(feat.unit_id[te].unique()))
print("auc", roc_auc_score(y[te], p))
print("ap", average_precision_score(y[te], p))
print("acc", accuracy_score(y[te], p > 0.5))
print("f1", f1_score(y[te], p > 0.5))
