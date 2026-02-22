# Decision Guide

How to identify and structure decisions in an ASP analysis.

## What is a Decision?

A decision is a choice point in your analysis where multiple valid options exist. Each choice could lead to different results — this is the "garden of forking paths."

**Good decisions to capture:**
- Algorithm/method choice (SVM vs Random Forest)
- Prior specification (informative vs weakly informative)
- Data handling (how to treat missing values)
- Evaluation strategy (which metrics, what baseline)

**Not decisions:**
- Fixed requirements ("must use Python") — these are constraints, not choices
- Implementation details ("use pandas") — these belong in the build phase, not the spec
- Obvious best practices — only capture choices that could reasonably go either way

## Decision Types

| Type | When to Use | Examples |
|------|-------------|----------|
| `method` | Algorithmic/methodological choices | model family, normalization approach, sampling strategy |
| `data` | Data handling choices | missing value treatment, train/test split, filtering criteria |
| `parameter` | Numeric/categorical parameters | learning rate, prior width, threshold values |

## Structure

```yaml
decisions:
  decision_id:           # lowercase_with_underscores
    label: "Human Name"  # Short, descriptive
    type: method         # method | data | parameter
    importance: 2        # 1=critical, 5=minor
    reviewed: false      # Has user weighed in?
    rationale: "Why this matters for the analysis"
    default: option_a    # Required — what to use if not specified
    options:
      option_a:
        label: "Option A"
        description: "What this does and when to use it"
        insights: []     # References to supporting literature
      option_b:
        label: "Option B"
        description: "Alternative approach"
```

## Identifying Decisions

### From the Research Question

Ask: "What could I do differently that would change the answer?"

Example: "Estimate cosmological parameters from galaxy surveys"
- Decisions: likelihood model, prior choice, sampler, summary statistics

### From Domain Knowledge

Each domain has common decision points:

| Domain | Common Decisions |
|--------|------------------|
| ML Classification | model family, feature scaling, train/test split, class imbalance handling |
| Bayesian Inference | prior specification, sampler choice, convergence criteria |
| Causal Inference | identification strategy, matching method, sensitivity analysis |
| SBI/ABC | summary statistics, distance metric, acceptance threshold |
| Deep Learning | architecture, optimizer, regularization, learning rate schedule |

### From Literature

Papers often compare approaches — these comparisons reveal decision points:
- "Method A vs Method B" → decision with two options
- "We found X outperforms Y when Z" → decision with literature support

### From User Uncertainty

When the user says:
- "I'm not sure whether to..." → decision
- "It depends on..." → decision
- "I've seen people do it both ways" → decision

## Importance Levels

| Level | Meaning | Example |
|-------|---------|---------|
| 1 | Critical — changes conclusions | prior specification in Bayesian analysis |
| 2 | Major — affects quality significantly | model architecture choice |
| 3 | Moderate — noticeable impact | normalization method |
| 4 | Minor — small effect | random seed, minor hyperparameters |
| 5 | Trivial — negligible impact | logging verbosity |

Focus on levels 1-3. Don't clutter with level 4-5 decisions unless the user cares.

## Constraints Between Decisions

Some options don't work together or require each other:

```yaml
options:
  gpu_training:
    label: "GPU Training"
    incompatible_with: ["hardware.cpu_only"]  # Can't combine
    requires: ["framework.pytorch"]            # Must have this
```

Constraints reference other decisions in the same analysis (or sub-analysis).

## Reviewed vs Unreviewed

- **reviewed: true** — User explicitly discussed and chose this
- **reviewed: false** — Agent inferred or used sensible default

During the build phase, unreviewed decisions get surfaced for confirmation before implementation.

## Common Mistakes

- **Too many decisions** — Not every choice needs to be a decision. Capture the ones that matter.
- **Too few options** — If there's only one valid option, it's not really a decision.
- **Vague options** — "Standard approach" vs "Alternative approach" — be specific.
- **Missing rationale** — Why does this decision matter? What changes if you choose differently?
- **No default** — Every decision needs a default for universe generation.

## Examples

### Good Decision

```yaml
prior_width:
  label: "Prior Width"
  type: parameter
  importance: 1
  rationale: "Wide priors favor null in Bayes factors; narrow priors assume more prior knowledge"
  default: weakly_informative
  options:
    informative:
      label: "Informative (σ=0.1)"
      description: "Strong prior based on previous measurements"
      insights: [previous_measurement_precision]
    weakly_informative:
      label: "Weakly Informative (σ=1)"
      description: "Regularizing prior that allows data to dominate"
    diffuse:
      label: "Diffuse (σ=10)"
      description: "Nearly flat prior — use with caution"
```

### Bad Decision

```yaml
use_pandas:  # Too implementation-focused
  label: "Use Pandas"
  type: method
  options:
    yes:
      label: "Yes"
    no:
      label: "No"
```

This isn't a scientific decision — it's an implementation choice for the build phase.
