# Hint 1 — conceptual

**For every function, ask three questions before writing a test.**

1. *Is there an input for which I can derive the output on paper?* (known answer)
2. *What transformation of the input has a predictable effect on the output?* (invariance)
3. *What does the function promise about shape, membership or errors?* (contract)

**For every test, ask one question after writing it:** *what is the most plausible wrong
implementation, and would this test fail on it?* If you cannot name a wrong implementation
that fails, the test is decoration.

Families of defect and what detects them:

| Defect family | Detected by |
|---|---|
| wrong formula with the right "shape" (mean square vs root mean square, mean-abs vs RMS) | a known answer with a tight tolerance, on an input where the formulas differ |
| missing `abs`, missing sign handling | an input that goes **up and down**, or a negative scale factor |
| wrong normalisation constant in a spectrum | a conservation law (total power = variance), or a tone of known power |
| `<` vs `<=`, off-by-one | an input placed **exactly on the boundary** |
| hidden dependence on row order | permute the input, expect the same output |
| missing validation | `pytest.raises` on the invalid input |
| leaking split | set arithmetic on group ids — no numbers needed |
| ignored parameter | vary the parameter and require the output to change |
| mis-wired training/evaluation | a problem so easy that only a wiring error can fail |

**For the challenge:** each numbered clause of the specification contains at least one
comparison or one boundary. Count them. Each needs a case on the boundary and one on either side.
