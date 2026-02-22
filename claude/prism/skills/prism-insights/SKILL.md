---
name: prism-insights
description: Extract and verify insights from scientific papers to justify analysis decisions. Use when working with papers, PDFs, DOIs, or adding evidence to an ASP analysis. Triggers on "paper", "insight", "evidence", "literature", "DOI", "quote".
allowed-tools: Read, Edit(asp.yaml), Glob, Grep, Bash(asp:*), WebSearch, WebFetch, AskUserQuestion, Task
---

# /prism-insights

Extract insights from scientific literature and link them to analysis decisions. This skill orchestrates **parallel subagents** — one per paper — to efficiently process multiple sources.

## References

- [UI Brand](./../ui-brand.md) — visual formatting patterns

**Key principle**: The agent writes evidence, but `asp validate --verify-evidence` is the gatekeeper. Quotes that don't exist in the PDF will fail validation.

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: Coordinator — Identify Papers                             │
│  → Web search, collect DOIs, understand analysis decisions          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: Coordinator — Download Papers                             │
│  → asp paper add <doi> for each paper                               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: Spawn Subagents — One Per Paper (PARALLEL)                │
│  → Each subagent reads PDF, extracts insights, returns YAML         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4: Coordinator — Consolidate & Verify                        │
│  → Merge insights into asp.yaml, run asp validate --verify-evidence │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 5: Coordinator — Link to Decisions                           │
│  → Add insight references to decision options                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Setup

1. Read the Prism reference guide: `.claude/skills/prism/SKILL.md`
2. Read `asp.yaml` to understand:
   - What problem is being solved?
   - What decisions exist that need justification?
   - What insights already exist?

Build a summary of the analysis context to pass to subagents.

## Step 1: Identify Papers

Print: `## Step 1: Identify Papers`

Find relevant literature for the analysis decisions.

**If the user provides papers:**
- Extract DOIs from URLs, PDF metadata, or citations
- DOI format: `10.XXXX/...` (e.g., `10.1038/s41586-023-06221-2`)
- arXiv DOI format: `10.48550/arXiv.{id}` (e.g., `10.48550/arXiv.1706.03762`)

**If searching for papers:**
- Use `WebSearch` to find relevant papers on arXiv, Semantic Scholar, Google Scholar
- Search for papers related to specific decisions that need evidence
- Note which decisions each paper might inform

Ask the user if needed: "Which decisions need literature support?" Present options from the analysis.

**Output of this step:** A list of papers with:
- DOI
- Version (for arXiv)
- Which decisions it might inform

## Step 2: Download Papers

Print: `## Step 2: Download Papers`

Download all papers to the local cache:

```bash
# Standard paper
asp paper add 10.1038/s41586-023-06221-2

# arXiv paper with specific version
asp paper add 10.48550/arXiv.1706.03762 --version 7
```

Run `asp paper add` for each paper. Papers must be cached before subagents can read them.

After downloading, get the PDF paths:
```bash
asp paper path <doi>
```

## Step 3: Spawn Subagents for Insight Extraction

Print: `## Step 3: Extract Insights (Parallel)`

**IMPORTANT**: For each paper, spawn a separate subagent using the `Task` tool. Process papers in parallel by making multiple Task calls in a single message.

### Subagent Instructions Template (with Self-Validation)

For each paper, call the Task tool with `subagent_type: "general-purpose"` and a prompt containing:

```
You are an ASP insight extraction agent with SELF-VALIDATION capability. Your task is to extract scientific insights from a single paper and format them for an ASP analysis.

## Analysis Context

[PASTE THE ANALYSIS SUMMARY HERE - problem statement, decisions needing evidence]

## Your Paper

- DOI: [DOI]
- Version: [VERSION if arXiv]
- PDF Path: [PATH from `asp paper path`]
- Target decisions: [WHICH DECISIONS THIS PAPER MIGHT INFORM]

## Instructions

1. Read the PDF at the path above using the Read tool
2. Identify findings relevant to the target decisions
3. For each relevant finding, extract:
   - A clear claim (1-2 sentences)
   - An exact quote from the paper (verbatim, 1-3 sentences)
   - The page number where the quote appears (as a hint)
   - **REQUIRED: prefix and suffix context** (~20-100 chars each) for robust matching

4. **VALIDATE all quotes at once** using batch verification:

   After extracting all quotes, build a JSON object and verify them in a single call:

   ```bash
   echo '{"quotes": [
     {"text": "exact quote 1", "page": 5, "prefix": "context before", "suffix": "context after"},
     {"text": "exact quote 2", "page": 12}
   ]}' | asp paper verify-quotes "<DOI>" [--version N]
   ```

   This extracts the PDF text ONCE and verifies all quotes, which is much faster than individual calls.

   Parse the JSON response:
   - Check each result's `status`: "verified" or "not_found"
   - For any "not_found" quotes: re-read the relevant PDF section, correct the quote
   - Repeat batch verification with corrected quotes (max 3 iterations)

5. Return ONLY verified insights as YAML in this exact format:

```yaml
insights:
  <insight_id>:
    id: <insight_id>
    claim: "<What we learned from this finding>"
    created_at: "<current ISO timestamp>"
    verified: true  # All quotes verified before returning
    evidence:
      - id: ev1
        doi: "<paper DOI>"
        version: <version if arXiv>
        quote:
          type: TextQuoteSelector
          exact: "<VERIFIED exact quote from paper>"
          prefix: "<~20-100 chars BEFORE the quote>"   # REQUIRED for robust matching
          suffix: "<~20-100 chars AFTER the quote>"    # REQUIRED for robust matching
        location:
          type: FragmentSelector
          page: <page number hint>
    scope: "<when this applies, optional>"

decision_links:
  <decision_id>:
    <option_id>:
      - <insight_id>
```

**Why prefix/suffix are required**: The verification system uses fuzzy matching (RapidFuzz) to handle OCR errors, Unicode variations, and inline citations in PDFs. The prefix/suffix provide disambiguation context per the W3C TextQuoteSelector standard, ensuring the correct quote instance is matched even when similar text appears multiple times in the paper.

## Batch Verification Loop

After extracting all quotes from the paper:

1. Build a JSON object with all quotes:
   ```json
   {"quotes": [
     {"text": "quote 1", "page": 5, "prefix": "before...", "suffix": "after..."},
     {"text": "quote 2", "page": 12}
   ]}
   ```

2. Run batch verification (extracts PDF once, verifies all quotes):
   ```bash
   echo '<json>' | asp paper verify-quotes "<DOI>" [--version N]
   ```

3. Parse JSON results to identify any failures (status: "not_found")

4. For failures: re-read relevant PDF sections and correct quotes

5. Repeat batch verification with corrected quotes (max 3 iterations)

6. If still failing after 3 attempts, skip those quotes and note in output

## Rules

- Use lowercase_with_underscores for insight IDs
- Quotes must be EXACT - copy verbatim from the PDF
- One claim per insight - don't combine multiple findings
- Only extract insights relevant to the target decisions
- **Only include insights that passed verification**
- If no relevant insights found, return empty insights: {}
```

### Parallel Execution

**Spawn all paper subagents in parallel** by including multiple Task tool calls in a single message:

```
[Task call for Paper 1]
[Task call for Paper 2]
[Task call for Paper 3]
...
```

Each subagent works independently, reading its assigned PDF and returning structured insights.

## Step 4: Consolidate and Verify

Print: `## Step 4: Consolidate and Verify`

After all subagents complete:

1. **Collect results** from each subagent
2. **Merge insights** into `asp.yaml`:
   - Add all insights to the `insights:` section
   - Ensure no ID conflicts (prefix with paper reference if needed)
3. **Run verification**:
   ```bash
   asp validate asp.yaml --verify-evidence
   ```

**If verification fails:**
- `Quote not found` — the subagent may have paraphrased; re-read the PDF and correct
- `Paper not in cache` — run `asp paper add <doi>` first
- `Wrong page` — update the page number

Keep iterating until all evidence verifies. This is the gatekeeper.

## Step 5: Link to Decisions

Print: `## Step 5: Link to Decisions`

Using the `decision_links` from subagent outputs, add insight references to decision options:

```yaml
decisions:
  normalization:
    options:
      layer_norm:
        insights:
          - layer_norm_stability    # Reference to insight ID
```

## Step 6: Final Validation

Print: `## Step 6: Final Validation`

Run full validation:

```bash
asp validate asp.yaml --verify-evidence
```

If all passes:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► INSIGHTS VERIFIED ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Report: "[N] insights extracted from [P] papers. [M] evidence items verified. Linked to [K] decision options."

---

## Evidence Format Reference

### Quote Evidence (W3C TextQuoteSelector)

```yaml
quote:
  type: TextQuoteSelector
  exact: "The exact quoted text from the paper"
  prefix: "Context before..."    # REQUIRED: ~20-100 chars before quote
  suffix: "Context after..."     # REQUIRED: ~20-100 chars after quote
```

**Best practices for prefix/suffix:**
- Include distinctive text (figure refs, theorem numbers, unique phrases)
- Avoid common words that appear throughout the paper
- Copy verbatim from the PDF, including punctuation
- Longer context (50-100 chars) is more robust than shorter

### Figure Evidence (FigureSelector)

```yaml
figure:
  type: FigureSelector
  label: "Figure 3a"
  caption: "Optional caption text"
```

### Table Evidence (TableSelector)

```yaml
table:
  type: TableSelector
  label: "Table 1"
  caption: "Optional header text"
  region: "row 3, accuracy column"
```

### Location Hint (FragmentSelector)

```yaml
location:
  type: FragmentSelector
  page: 5                        # 1-indexed page number
```

---

## CLI Reference

```bash
# Paper management
asp paper add <doi> [--version N] [--pdf path]   # Download/cache paper
asp paper list                                    # List cached papers
asp paper show <doi>                              # Show paper metadata
asp paper path <doi>                              # Get path to PDF
asp paper remove <doi>                            # Remove from cache

# Quote verification (single quote)
asp paper verify-quote <doi> --quote "..." [--version N] [--page P] [--json]
# Exit codes: 0=verified, 1=not found, 2=error
# JSON output: {"status": "verified|not_found|error", "found_pages": [...], "expected_page": N, "message": "..."}

# Batch quote verification (PREFERRED - extracts PDF once)
echo '{"quotes": [{"text": "...", "page": N, "prefix": "...", "suffix": "..."}]}' | \
  asp paper verify-quotes <doi> [--version N]
# Exit codes: 0=all verified, 1=some not found, 2=error
# JSON output: {"doi": "...", "results": [...], "summary": {"total": N, "verified": N, "not_found": N}}

# Validation
asp validate asp.yaml                             # Schema + semantic validation
asp validate asp.yaml --verify-evidence           # + evidence verification
```

---

## Restrictions

**You are an insights coordinator, not an implementation agent.**

- ONLY modify `asp.yaml` (insights section and decision option references)
- NEVER fabricate quotes — all evidence must pass `asp validate --verify-evidence`
- ALWAYS spawn subagents for paper processing when multiple papers are involved
- If a quote doesn't verify, fix it — don't skip verification

## Tips

1. **Spawn in parallel** — Use multiple Task calls in one message for efficiency
2. **Rich context** — Give subagents full analysis context so they extract relevant insights
3. **One paper per subagent** — Don't overload subagents with multiple papers
4. **Subagent self-validation** — Subagents use `asp paper verify-quote` to validate quotes before returning, catching errors early while they still have PDF context
5. **Verify early** — Run validation after consolidating, before linking to decisions
6. **arXiv versions** — Always specify version for reproducibility
7. **Iterate on failures** — If verification fails, the quote needs correction
