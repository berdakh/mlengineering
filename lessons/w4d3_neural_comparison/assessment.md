# Assessment — w4d3 neural comparison

Answer in writing before opening `solutions/lessons/w4d3_neural_comparison/assessment_answers.md`.

## A. Reasoning questions (about 15 minutes)

1. SKAB has one labelled fault segment per experiment and 27 development experiments. Why does that
   favour a reconstruction or forecasting objective over a window classifier? Name one situation in which
   you would switch to a classifier.

2. Your autoencoder's training loss keeps falling for 30 epochs while the validation loss is flat after
   epoch 10. Early stopping with patience 4 stops at epoch 14. What does the model you return contain,
   and what would be wrong with reporting the epoch-30 model's TEST score instead?

3. A colleague standardises each experiment with the mean and sd of the *whole* experiment before
   windowing, "because the burn-in is only 100 rows". What does that do to a fault that starts at row
   600, and why will the offline result not hold in deployment?

4. Seed 3 had the lowest validation loss and the lowest TEST PR-AUC. Give a mechanism by which a better
   reconstruction can make a worse detector.

5. You reran `compare_seeds.py` on a laptop and the seed-0 TEST PR-AUC changed in the third decimal. List
   three things that could explain it, and what you would record to make the next comparison
   reproducible.

## B. Design-choice explanation (about 10 minutes)

Explain, as you would to a reviewer, why this lesson pins `torch.set_num_threads(1)` for the comparison,
and what you would have to change about that choice for a production training job on a large model.

## C. Rubric for open-ended answers (and for the challenge's PROTOCOL.md)

| Criterion | Weak | Solid | Strong |
|---|---|---|---|
| Unit of analysis | rows or windows | experiments/pumps named as the unit | unit named, consequences for splits *and* intervals stated |
| What is held equal | "same data" | data, rows scored, metric, budget | also states what cannot be equal and how that limits the claim |
| Uncertainty | one number | seed spread or interval | both, with which question each answers |
| Selection | not mentioned | test read once | selection procedure, budget and stopping rule fixed in advance |
| Cost | ignored | training/inference time | operational burden: dependencies, retraining, debugging, explanation |
| Decision | "the better model" | rule stated | rule stated before results, including what "cannot tell" leads to |

## D. Interview rep — debugging (15 minutes, closed book)

You inherit this training script. On the team's dashboard the autoencoder's validation loss drops to
almost zero after two epochs and the detector's precision is excellent offline. In shadow deployment it
misses most faults. Talk through, in order, what you would check and why. You may assume the code below
is everything relevant.

```python
train = tidy[tidy.experiment_id.isin(dev)]
x = burn_in_z(train, 100)
x = (x - x.mean(0)) / x.std(0)
windows = make_windows(x, 32)                                # whole frame, all experiments at once
train_w, val_w = sklearn.model_selection.train_test_split(windows, test_size=0.2, random_state=0)
loader = DataLoader(TensorDataset(torch.from_numpy(train_w)), batch_size=256, shuffle=True, num_workers=4)
for epoch in range(50):
    for (xb,) in loader:
        loss = ((model(xb) - xb) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
    val = ((model(torch.from_numpy(val_w)) - torch.from_numpy(val_w)) ** 2).mean()
    if val < best: best, best_state = val, model.state_dict()
model.load_state_dict(best_state)
```

Score yourself with the rubric in the answers file after writing your narrative.
