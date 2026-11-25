# Hint 3 — partial implementation (w4d3)

```python
def make_windows(x, window):
    x = np.asarray(x, dtype=np.float32)
    # ... validate ...
    padded = np.concatenate([np.repeat(x[:1], window - 1, axis=0), x], axis=0)
    index = np.arange(len(x))[:, None] + np.arange(window)[None, :]
    return padded[index]
```

```python
# inside train_autoencoder, per epoch
model.train()
order = torch.randperm(len(train_x), generator=generator).numpy()
for start in range(0, len(order), batch_size):
    xb = torch.from_numpy(train_x[order[start:start + batch_size]])
    loss = ((model(xb) - xb) ** 2).mean()
    optimiser.zero_grad(); loss.backward(); optimiser.step()
val_loss = _mean_loss(model, val_x, batch_size)
if val_loss < best_loss:
    best_loss, best_epoch, since_best = val_loss, epoch, 0
    best_state = copy.deepcopy(model.state_dict())
else:
    since_best += 1
    if since_best >= patience:
        break
# after the loop: model.load_state_dict(best_state)
```

```python
def _usable_rows(self, tidy):
    return (tidy["t"].to_numpy() >= self.n_burn) & (tidy["anomaly"].to_numpy() == 0)
```

The remaining pieces (`fit` bookkeeping, `score`'s per-experiment loop) follow the docstrings.
For the challenge's verdict:

```python
margin = max(2.0 * seed_se, test_halfwidth)
verdict = "A better" if diff > margin else "B better" if diff < -margin else "cannot tell"
```
