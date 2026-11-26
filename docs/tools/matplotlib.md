---
title: "Plotting with matplotlib"
parent: Tool guides
nav_order: 7
---

# Plotting with matplotlib

matplotlib is Python's standard plotting library. Almost every other plotting tool in the Python world (pandas'
`.plot()`, seaborn, many dashboards) is built on top of it, so the ideas here carry over everywhere. This guide covers
what you need in Week 4 and for most day-to-day work as an ML engineer: looking at distributions, comparing groups,
showing trends over time, and producing a clear figure for a report.

## What matplotlib is, and why engineers use it

A table of numbers hides shape. A plot shows in one second whether values are bunched or spread, whether there are
outliers, whether a trend goes up or down, whether two groups differ. On the job you plot for two audiences:

* **yourself**, while exploring: quick, rough plots that answer one question each;
* **other people**, in a report or a pull request: fewer plots, every axis labelled, a title that states the point.

matplotlib does both. It is not the prettiest library by default, but it is everywhere, it is stable, and it can
draw anything.

## Opening it

**In Google Colab** matplotlib is already installed. Import it at the top of a notebook:

```python
import matplotlib.pyplot as plt
```

`pyplot` is the part of matplotlib you use directly; `plt` is the universal nickname. Plots appear below the cell
that draws them.

**On your own computer** (Week 10 onwards), install it into your environment with
`python -m pip install matplotlib` (the course's `requirements.txt` already includes it). In Jupyter or VS Code
notebooks plots appear inline as in Colab. In a plain Python script, call `plt.show()` to open a window, or save the
figure to a file (see "Saving a figure").

## The one idea: figures and axes

Every matplotlib picture has two kinds of objects:

* the **figure** (`fig`): the whole canvas, the thing that gets saved to a file;
* one or more **axes** (`ax`): a single plot inside the figure, with an x axis, a y axis, a title and the data.

(The word *axes* is matplotlib's name for "one plot area"; it is not the plural of *axis*, which is confusing at
first.) You create both with one call, then draw by calling methods on `ax`:

```python
fig, ax = plt.subplots(figsize=(6, 4))   # width, height in inches
ax.plot([1, 2, 3, 4], [10, 20, 15, 30])  # draw on the axes
ax.set_title("A first plot")
ax.set_xlabel("x")
ax.set_ylabel("y")
plt.show()
```

This "figure and axes" style (also called the object-oriented style) is the one to learn. You will also see code
that calls `plt.plot(...)`, `plt.title(...)` directly. That style draws on "the current axes" behind the scenes. It
is fine for one quick plot and confusing as soon as there are several, so this course always uses `fig, ax`.

Several plots side by side:

```python
fig, axes = plt.subplots(1, 2, figsize=(10, 4))   # 1 row, 2 columns: axes is an array of 2 axes
axes[0].hist(values, bins=30)
axes[1].bar(["a", "b"], [3, 5])
fig.tight_layout()                                 # stop labels from overlapping
plt.show()
```

## The five plots you will use most

Pick the plot from the question, not the other way round.

| Question | Plot | Method |
|---|---|---|
| How is one numeric variable distributed? | histogram | `ax.hist(values, bins=30)` |
| How do groups compare on one number? | bar chart | `ax.bar(names, heights)` |
| How does something change over time? | line chart | `ax.plot(dates, values)` |
| How do two numeric variables relate? | scatter plot | `ax.scatter(x, y)` |
| How do distributions differ between groups? | box plot | `ax.boxplot([group_a, group_b])` |

### Histogram: distributions

A histogram cuts the range of a variable into `bins` equal intervals and draws one bar per interval, as tall as the
number of values inside it.

```python
fig, ax = plt.subplots()
ax.hist(order_values.dropna(), bins=40)
ax.set_title("Order values are right-skewed")
ax.set_xlabel("order value")
ax.set_ylabel("number of orders")
plt.show()
```

* Too few bins hide the shape; too many make it noisy. Try a few values.
* `ax.hist` does not accept missing values well: call `.dropna()` first.
* For very skewed data, a log scale on x helps: `ax.set_xscale("log")` (values must be positive).

### Bar chart: comparing groups

```python
rates = table.groupby("segment")["churned"].mean().sort_values(ascending=False)
fig, ax = plt.subplots()
ax.bar(rates.index, rates.values)
ax.set_ylabel("churn rate")
ax.set_title("Churn rate by segment")
plt.show()
```

* Sort the bars by height unless the categories have a natural order.
* Long category names: rotate them with `ax.tick_params(axis="x", rotation=45)` or use horizontal bars,
  `ax.barh(names, values)`.
* Bars should start at zero; a bar chart with a cut y axis exaggerates differences.

### Line chart: time

```python
monthly = orders.groupby(orders["order_date"].dt.to_period("M")).size()
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.plot(monthly.index.to_timestamp(), monthly.values, marker="o")
ax.axvline(pd.Timestamp("2025-09-30"), color="black", linestyle="--")  # mark a date
ax.set_xlabel("month")
ax.set_ylabel("orders")
plt.show()
```

* A pandas `Period` index (from `to_period("M")`) must be turned into dates with `.to_timestamp()` before plotting.
* `marker="o"` draws a dot on each point, useful when there are few points.
* Several lines on one axes: call `ax.plot` several times with `label="..."`, then `ax.legend()`.

### Scatter plot: relationships

```python
fig, ax = plt.subplots()
ax.scatter(table["recency_days"], table["orders_365d"], s=8, alpha=0.5)
ax.set_xlabel("days since last order")
ax.set_ylabel("orders in the last year")
plt.show()
```

* `s` is the dot size, `alpha` the transparency (0 to 1). With many points, small transparent dots show where
  points pile up.
* Colour by a third variable: `ax.scatter(x, y, c=labels, cmap="coolwarm")`.

### Box plot: distributions per group

```python
groups = [table.loc[table["churned"] == v, "recency_days"] for v in (False, True)]
fig, ax = plt.subplots()
ax.boxplot(groups)
ax.set_xticks([1, 2], ["retained", "churned"])
ax.set_ylabel("days since last order")
plt.show()
```

The box spans the middle half of the values (25th to 75th percentile), the line inside is the median, and dots
beyond the "whiskers" are unusual values.

## Labels, titles and legends

A plot someone else reads needs:

* **axis labels with units**: `ax.set_xlabel("order value (USD)")`;
* **a title that states the point**, not just the variables: "Recent buyers churn less" beats "recency vs churn";
* **a legend** when there is more than one series: pass `label=` to each drawing call, then `ax.legend()`.

Other useful settings:

```python
ax.set_xlim(0, 500)          # zoom the x axis
ax.set_ylim(bottom=0)        # start y at zero
ax.grid(alpha=0.3)           # light grid lines
ax.axhline(0.47, color="grey", linestyle=":")   # horizontal reference line (e.g. the overall rate)
```

## Plotting straight from pandas

pandas Series and DataFrames have a `.plot` method that calls matplotlib for you. It is handy while exploring, and
it accepts an `ax=` so you can still label things:

```python
fig, ax = plt.subplots()
rates.plot.bar(ax=ax)                  # same as ax.bar(rates.index, rates.values)
ax.set_ylabel("churn rate")
plt.show()

table["spend_365d"].plot.hist(bins=30)  # quick look, default axes
```

## Saving a figure

```python
fig.savefig("churn_by_segment.png", dpi=150, bbox_inches="tight")
```

* `dpi` sets the resolution; 150 is good for documents.
* `bbox_inches="tight"` trims empty margins so labels are not cut off.
* Save before `plt.show()` in scripts: in some setups `show` clears the figure.
* In Colab the file appears in the Files panel on the left (and disappears when the runtime is recycled; download
  it or save to Drive).

## Returning a figure from a function

When plotting code lives in a function (as in the Week 4 exercises), create the figure inside, draw, and **return**
`fig, ax` without calling `plt.show()`. The caller decides whether to show, save or test it:

```python
def value_histogram(values, bins):
    fig, ax = plt.subplots()
    ax.hist(values.dropna(), bins=bins)
    ax.set_title("Distribution of order values")
    ax.set_xlabel("order value")
    ax.set_ylabel("number of orders")
    return fig, ax
```

Tests can then inspect the axes: `len(ax.patches)` is the number of bars, `ax.get_xlabel()` the label. Close
figures you no longer need with `plt.close(fig)`: notebooks that create hundreds of figures in a loop otherwise run
out of memory.

## Common errors and how to read them

| Message or symptom | What it means | Fix |
|---|---|---|
| `ValueError: x and y must have same first dimension` | `ax.plot(x, y)` got lists of different lengths | check `len(x)`, `len(y)`; you probably filtered one and not the other |
| `TypeError: float() argument must be a string or a real number, not 'Period'` | plotting a pandas `Period` index | use `index.to_timestamp()` |
| A histogram with one giant bar | a few huge values stretch the range | look at `describe()`; use more bins, `ax.set_xlim`, or a log scale |
| Labels overlap or are cut off | too little room | `fig.tight_layout()`, rotate tick labels, or a larger `figsize` |
| Two plots drawn on top of each other | drawing with `plt.*` after creating several axes | draw on a specific `ax` |
| `<Figure size 640x480 with 1 Axes>` printed and no picture | the figure was created but not displayed (scripts) | `plt.show()`, or make `fig` the last value of the cell |
| `ValueError: ... could not convert string to float` in `hist` | the column holds text, not numbers | convert with `pd.to_numeric`, or you picked the wrong column |

## Cheat sheet

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 4))          # one plot
fig, axes = plt.subplots(2, 2, figsize=(10, 8))  # grid of plots: axes[row, col]

ax.hist(x, bins=30)                  # distribution
ax.bar(names, heights)               # one number per group   (ax.barh for horizontal)
ax.plot(x, y, marker="o", label="a") # line / time series
ax.scatter(x, y, s=8, alpha=0.5)     # two numeric variables
ax.boxplot([g1, g2])                 # distributions per group

ax.set_title("What the plot shows")
ax.set_xlabel("x (units)"); ax.set_ylabel("y (units)")
ax.legend()                          # after passing label= to drawing calls
ax.set_xlim(a, b); ax.set_ylim(bottom=0)
ax.set_xscale("log")
ax.axvline(x0, linestyle="--"); ax.axhline(y0, color="grey")
ax.tick_params(axis="x", rotation=45)
ax.grid(alpha=0.3)

fig.tight_layout()
fig.savefig("plot.png", dpi=150, bbox_inches="tight")
plt.show()
plt.close(fig)

series.plot.hist(bins=30, ax=ax); series.plot.bar(ax=ax); df.plot(x="date", y="value", ax=ax)
```

**Choosing a plot:** one numeric variable → histogram; number per group → bar; over time → line; two numbers →
scatter; distribution per group → box plot.

## Where to go next

* The official [matplotlib tutorials](https://matplotlib.org/stable/tutorials/index.html), especially "Quick
  start guide".
* The [plot types gallery](https://matplotlib.org/stable/plot_types/index.html): every kind of plot with its code.
* [pandas visualisation](https://pandas.pydata.org/docs/user_guide/visualization.html) for `.plot`.
* Used in: [13 · Exploratory analysis with a purpose](../notebooks/13_eda_with_purpose.html) and every later
  notebook that draws a chart.
