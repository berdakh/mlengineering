# Hint 3 - partial

A complete answer to Q03 ("seven test experiments") in the expected shape:

> It is small, and I do not claim precise numbers from it. Event recall of 5 of 7 has an interval of
> roughly 0.36 to 0.92. What makes the result interpretable is the protocol: every choice was made on 27
> development experiments, the test set was looked at once, and the chosen detector is compared with
> the clock baseline and chance, where the gap is large. So my claims are relative, not precise.
>
> Evidence: `labs/w4d5_model_choice/figures/test_look.csv` `labs/w3d5_uncertainty/README.md`

And the Evidence beat of a 5-minute script:

> On the seven test experiments the detector caught 5 of 7 faults, interval 0.36 to 0.92, with no
> false-alarm events; on development data its PR-AUC was 0.76 [0.68, 0.84], level with the supervised
> alternative within the interval, at a fraction of the cost.

For the challenge, if your project was, say, a medical detection study, the Translation section could start like this:

> The same structure is equipment monitoring with few machines: the machine is the patient, a fault
> is a seizure, the allowed detection delay is the onset tolerance ...
