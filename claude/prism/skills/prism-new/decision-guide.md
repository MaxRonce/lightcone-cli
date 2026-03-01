# Decision Guide

## E/N/U Classification

Classify every candidate decision before adding it to the spec.

| Type | Name | In multiverse? | Meaning |
|------|------|---------------|---------|
| **E** | Principled Equivalence | **Yes** | Options expected to produce equivalent results. Genuinely arbitrary. |
| **N** | Principled Nonequivalence | **No** -- fix it | One option is clearly better-justified. Including it dilutes signal. |
| **U** | Uncertainty | **Yes**, flag it | Reasons to suspect non-equivalence but insufficient evidence to pick a winner. |

**Flowchart:**
1. Does literature/domain knowledge clearly favor one option? --> **Type N.** Fix it.
2. Are the options expected to give similar results? --> **Type E.** Include all.
3. Neither clear? --> **Type U.** Include, flag for careful interpretation.

**Type N exception:** If reviewer pushback is likely, fix the better option as default and include the weaker option as a secondary check.

**Embed classification in the rationale field,** e.g.: `"Type U -- literature uses both 2.5 and 3 SD cutoffs with no consensus"`

---

## Stability Test

A decision matters if changing it changes the conclusion. If all options give qualitatively similar results, the choice is cosmetic -- skip it.

---

## Not Decisions

Skip these: fixed requirements (constraints), implementation details (build phase), obvious best practices with no defensible alternative, purely cosmetic choices.

---

## Scoping

A multiverse of trivial decisions is less informative than a focused one.

| Tier | Criterion |
|------|-----------|
| **1 -- Must vary** | Literature/domain knowledge suggests the choice matters. |
| **2 -- Should vary** | Impact uncertain but plausible. Include if feasible. |
| **3 -- Could vary** | Impact likely small. Defer unless core multiverse is manageable. |

---

## Constraint Patterns

Use constraints when decisions are not independent.

- **Conditional existence** (`when` on decision) -- downstream decision only exists given an upstream choice. E.g., `svm_kernel` only exists `when: model.svm`.
- **Incompatibility** (`incompatible_with` on option) -- two options cannot coexist in a universe.
- **Requirement** (`requires` on option) -- selecting one option forces another.
