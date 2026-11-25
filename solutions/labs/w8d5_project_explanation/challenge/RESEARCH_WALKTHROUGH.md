# 5-minute walkthrough of one of my research projects (reference - FICTIONAL example)

**This reference is a made-up study, written only to show the structure.** It does not describe any
real publication; all numbers are illustrative and labelled as such. Your own version must use your
own project and your own numbers.

Project (title, year, your role): "Cross-patient seizure-onset detection from intracranial EEG"
(fictional), lead analyst.

## Problem

Clinicians reviewing long intracranial recordings need to find seizure onsets quickly. The question
was whether a detector trained on some patients can flag onsets in a new patient without per-patient
retuning, because retuning needs annotated seizures that a new patient does not yet have. Success
meant onsets flagged within a short window, with a false-detection rate a reviewer would accept per
hour of recording. Practically, a reviewer jumps to each flagged time: a missed onset costs a manual
search through hours of signal, while a false flag costs a few seconds of attention, so the two
errors were never weighted equally.

## Constraint

Few patients (in this illustrative case, fourteen) with very different electrode placements, so the
patient, not the window, is the unit of generalisation. Seizures are rare, so event counts per
patient are small. Annotations come from clinicians and the onset time itself is uncertain by several
seconds. Compute was not the constraint; label quality and the number of independent patients were.
Recordings were also long and mostly seizure-free, so evaluating on balanced windows would have
measured a problem nobody has: the reviewer sees the whole recording, with its imbalance, and that is
what the evaluation had to reproduce.

## Decision

I used leave-one-patient-out evaluation throughout, never mixing windows of one patient across train
and test, and scored at the event level with an explicit onset tolerance. I compared a line-length
threshold, a band-power logistic model and a small convolutional network under the same protocol and
chose thresholds on training patients only. I reported per-patient results, not only pooled ones.
Every preprocessing step, including normalisation, was fitted inside the training patients of each
fold, and the onset tolerance was fixed before any result was seen, so that it could not be tuned
towards a better number afterwards.

## Evidence

Illustrative numbers: the logistic model detected 0.71 [0.58, 0.82] of seizures across held-out
patients, with a median latency of eight seconds; the network was not better within the patient-level
interval, and the line-length threshold detected fewer seizures with more false detections. Two of the
fourteen patients accounted for most false detections. Pooled over patients the false-detection rate
looked acceptable; per patient it ranged from almost none to several per hour, which is the number a
reviewer of one particular patient actually experiences. Within each held-out patient, I also
looked at the missed seizures one by one: most were short, low-amplitude onsets on electrodes far
from the main focus, which tells me where a better detector would need to look.

## Limitation

Fourteen patients from one centre and one electrode type; onset annotations from one reviewer per
patient; no prospective test. The interval covers patient sampling, not centre or hardware changes.
The two patients with many false detections had artefact-heavy recordings, which the evaluation could
not separate from model error. And the latency figure inherits the uncertainty of the onset
annotations, so differences of a few seconds between models are not interpretable.

## Next step

Validate on recordings from a second centre, add a second annotator to measure label uncertainty, and
test a per-patient calibration step that uses the first recorded seizure, measuring how much it helps
against the cost of waiting for one. Only then would a clinical review-time study make sense,
comparing how long reviewers take with and without the flags on the same recordings, which is the
outcome the original question was really about.

## Translation to industry

The same structure is equipment monitoring with few machines: the machine is the patient, a fault is
a seizure, the onset tolerance is the allowed detection delay, and false detections per hour are
alarm fatigue. In an industrial role I would add what the study never needed: a service that scores
continuously, monitoring of input changes such as a replaced sensor, delayed labels from maintenance
logs, and a rollback path when a new model behaves worse.

## What was not established

That the detector works prospectively, in another hospital, or with other electrodes. That detection
helps clinicians review faster - we measured detection, not workflow. That the network is worse than
the logistic model: the evidence only failed to show it better.
