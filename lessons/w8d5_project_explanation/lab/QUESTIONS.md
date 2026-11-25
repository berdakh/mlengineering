# Twenty hard questions about flowguard

An interviewer who has read your README asks these. Answer each in `ANSWERS.md`: 40-130 words
(about 20-50 seconds spoken), and cite at least one artifact that backs the answer. The questions are
deliberately uncomfortable; most are about the places where the project did *not* go as hoped.

| # | Question |
|---|---|
| Q01 | Your dataset has rows duplicated across files, some with contradictory labels. How did you find that, and what did you change? |
| Q02 | A "detector" that only looks at the clock scores F1 0.835. What does that tell you about the benchmark, and about your other numbers? |
| Q03 | Your test set has seven experiments. Why should anyone believe your numbers? |
| Q04 | Gradient-boosted trees had the best test score. Why didn't you ship them? |
| Q05 | Why not a neural network? You have a PyTorch background. |
| Q06 | You shipped a single-sensor z-score. Isn't that too simple to be a portfolio project? |
| Q07 | How did you choose the alarm threshold, and how many times did you look at the test set? |
| Q08 | Do you report point-level or event-level metrics, and why? |
| Q09 | Your drift monitor flags only a small share of fault windows. Isn't the monitoring useless? |
| Q10 | What happens when the model cannot load or the input is garbage? |
| Q11 | With two workers your API's median latency was about 52 ms. What was going on? |
| Q12 | How do you know the service computes the same scores as your offline evaluation? |
| Q13 | Many samples scored exactly at the threshold. Why should anyone care? |
| Q14 | Labels arrive late. How would you know in production that the model has stopped working? |
| Q15 | How would you roll out a new model version safely? |
| Q16 | What would you do with three more months? |
| Q17 | What does this dataset not let you claim about a real plant? |
| Q18 | Why split by experiment rather than by row? What did it cost you? |
| Q19 | Why resample experiments, not samples, for your intervals? |
| Q20 | Isn't this just your EEG work with a different dataset? What is actually new? |
