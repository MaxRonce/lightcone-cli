# Perlmutter Friction Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate six friction points discovered running `prism run --target perlmutter` by adding a default walltime in code and improving skill/template guidance.

**Architecture:** One code change in `runner.py` (default walltime fallback), plus documentation fixes in the `/prism-run` skill and `CLAUDE.md` template. All changes are backward-compatible — existing specs with explicit `time_limit` are unaffected.

**Tech Stack:** Python (Prism runner), Markdown (skills, templates)

---

### Task 1: Default walltime for SLURM — test

**Files:**
- Modify: `tests/test_runner.py`

**Step 1: Write the failing tests**

Add two tests to `TestSlurmResourceTranslation`:

```python
def test_default_time_when_slurm(self):
    """When no time_limit is set and slurm=True, inject 30min default."""
    dirs = translate_resources_to_slurm_directives(
        {}, scheduler_config={"account": "m1234"}, slurm=True,
    )
    assert "--time=00:30:00" in dirs

def test_no_default_time_when_not_slurm(self):
    """When slurm flag is not set, no default time injected."""
    dirs = translate_resources_to_slurm_directives(
        {}, scheduler_config={"account": "m1234"},
    )
    assert all("--time" not in d for d in dirs)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_runner.py::TestSlurmResourceTranslation::test_default_time_when_slurm tests/test_runner.py::TestSlurmResourceTranslation::test_no_default_time_when_not_slurm -v`
Expected: FAIL (slurm parameter doesn't exist yet)

---

### Task 2: Default walltime for SLURM — implementation

**Files:**
- Modify: `src/prism/dagster/runner.py:331-362`

**Step 1: Add `slurm` parameter and default time logic**

In `translate_resources_to_slurm_directives()`, add a `slurm: bool = False` parameter. After processing all resource fields, if no `--time` directive was added and `slurm` is True, append `--time=00:30:00` and log a warning.

```python
def translate_resources_to_slurm_directives(
    resources: dict[str, Any],
    scheduler_config: dict[str, Any] | None = None,
    *,
    slurm: bool = False,
) -> list[str]:
    """Translate ASP resource requirements to SLURM #SBATCH directives."""
    scheduler_config = scheduler_config or {}
    directives: list[str] = []

    # ... existing scheduler_config and resource directives ...

    if time_limit := resources.get("time_limit"):
        directives.append(f"--time={_normalise_time_limit(time_limit)}")
    elif slurm:
        logger.warning(
            "No time_limit in recipe resources — using 30-minute default. "
            "Set resources.time_limit in asp.yaml for longer jobs."
        )
        directives.append("--time=00:30:00")

    return directives
```

Update the call site in `generate_sbatch_script()` (line 423) to pass `slurm=True`:

```python
directives = translate_resources_to_slurm_directives(resources, scheduler_config, slurm=True)
```

**Step 2: Run all runner tests**

Run: `pytest tests/test_runner.py -v`
Expected: All PASS (including existing tests — `slurm=False` default preserves old behavior)

**Step 3: Commit**

```bash
git add src/prism/dagster/runner.py tests/test_runner.py
git commit -m "feat: add 30-minute default walltime for SLURM jobs without time_limit"
```

---

### Task 3: Fix `/prism-run` skill — remove `nodes` from example, add NERSC guidance

**Files:**
- Modify: `claude/prism/skills/prism-run/SKILL.md`

**Step 1: Fix the GPU example recipe (line ~207)**

Remove `nodes: 1` from the example. Change:
```yaml
      resources:
        nodes: 1
        cpus: 64
        gpus: 4
        memory: 256GB
        time_limit: 2h
```
To:
```yaml
      resources:
        cpus: 64
        gpus: 4
        memory: 256GB
        time_limit: 2h
```

**Step 2: Add Common NERSC Issues rows**

Add these to the existing "Common NERSC Issues" table (after line ~234):

| Problem | Solution |
|---------|----------|
| SLURM rejects job (no time limit) | Prism defaults to 30 minutes. For longer jobs, add `resources: { time_limit: 2h }` to the recipe. |
| `--prior_range` not recognized by script | Decision IDs use underscores → Prism passes `--prior_range`. Scripts must use underscores in argparse: `parser.add_argument('--prior_range')` |
| GPU allocation for CPU-only work | Edit target: `prism remote edit <name>`, set `partition: cpu` and `constraint: cpu`. GPU partitions waste allocation hours on CPU workloads. |
| `prism status` shows "Container: not built" | Expected when targeting HPC — `prism run --target` builds/migrates containers automatically on the target. Run `prism build` locally only for local Docker execution. |

**Step 3: Add a "Local vs Container Execution" note**

Add after the "Running" subsection (after line ~196), before "Monitoring SLURM jobs":

```markdown
### Local Environment vs Container Execution

Scripts run inside containers on compute nodes. You do **not** need to install Python packages locally for HPC execution — `requirements.txt` and the `Containerfile` define the execution environment. A local `.venv` is useful for IDE support and linting, but `prism run --target` uses the container image exclusively.
```

**Step 4: Commit**

```bash
git add claude/prism/skills/prism-run/SKILL.md
git commit -m "docs: fix prism-run skill — remove invalid nodes field, add NERSC friction guidance"
```

---

### Task 4: Update CLAUDE.md template — underscore convention

**Files:**
- Modify: `claude/prism/templates/CLAUDE.md`

**Step 1: Add underscore note to Decision Parameterization section**

After the existing "How to handle each decision type" list (after line ~68), add:

```markdown
**Naming convention:** Decision IDs in `asp.yaml` use underscores (e.g.,
`prior_range`). Prism passes these as CLI arguments with underscores
(`--prior_range wide`). Scripts must define argparse arguments with underscores
to match: `parser.add_argument('--prior_range')`, not `--prior-range`.
```

**Step 2: Commit**

```bash
git add claude/prism/templates/CLAUDE.md
git commit -m "docs: add underscore convention note to CLAUDE.md template"
```

---

### Task 5: Run full test suite

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 2: Run linter**

Run: `ruff check src/ tests/`
Expected: No errors
