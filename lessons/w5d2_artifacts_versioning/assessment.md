# W5D2 assessment

Answer in writing before opening `solutions/lessons/w5d2_artifacts_versioning/assessment_answers.md`.

## Reasoning questions (5-10 minutes)

1. A colleague says: "our bucket is private, so loading pickles from it is safe". Give two ways this
   can still go wrong, and one situation in which you would accept pickle anyway.
2. `checksums.json` sits in the same directory as the files it protects, so anyone who can edit a file
   can also edit the checksums. What does the checksum protect against, then, and what would you add
   to protect against a deliberate attacker?
3. Why must a registered version be immutable, given that the `current` pointer already says which
   model is live? Name a record elsewhere in the system that would become wrong if `1.0.0` changed.
4. The bundle format version is 1 and the model version is 1.0.0. A teammate adds a field to `model.json`
   that old loaders would ignore. Which of the two versions changes, and how?
5. The JSON + npz bundle of the logistic candidate is 2.5 times larger and about 15 times slower to load
   than its pickle. When would that cost matter, and what would you change then?

## Design-choice explanation (10 minutes, written)

You chose to store the logistic candidate's coefficients rather than the scikit-learn object. Explain
the choice to a teammate who prefers `joblib.dump`: what you gain, what you give up, and the kind of
model for which you would choose differently.

## Rubric for open answers

| Criterion | Meets | Exceeds |
|---|---|---|
| Threat model | separates accidental corruption from deliberate tampering | names what each control (checksum, signature, access control) does and does not stop |
| Versioning | distinguishes artifact format version from model version | states what bump each kind of change requires and who must react |
| Immutability | ties versions to logged predictions and audits | explains rollback as a pointer change and why it is then safe and fast |
| Trade-offs | names one cost of the safe format | says when the cost would change the decision, with a measured number |

## Interview rep: ML system design (10-15 minutes, timed, reduced assistance)

> "Design the model registry for a team of 15 that ships about 20 models, some retrained weekly. What
> does a registered model contain, how does a service find the model it should serve, how do you roll
> back, and how do you know which model produced a given prediction a month later?"

Draw the components and the flow of one retraining, then score yourself with the rubric in the answers
file before reading the model answer.
