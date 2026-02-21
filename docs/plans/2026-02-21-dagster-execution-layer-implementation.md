# Dagster Execution Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate a Dagster-based execution layer into Prism where ASP outputs become Dagster assets, recipes are inline on outputs, and universes map to Dagster partitions.

**Architecture:** Asset factory reads `asp.yaml`, generates one `@asset` per output with a recipe. `ASPContainerRunner` resource dispatches to Docker or SLURM. `ASPIOManager` maps `(asset, universe)` to `results/<universe>/<output>/` paths. Existing remote/HPC/canvas/navigator code is removed and replaced.

**Tech Stack:** Python 3.11+, Dagster 1.9+, dagster-docker, Click, Rich, PyYAML, Pydantic 2.x

**Design doc:** `docs/plans/2026-02-21-dagster-execution-layer-design.md`

---

## Phase 1: ASP Schema Changes

These tasks modify `extern/ASP`. Run ASP tests with `cd extern/ASP && pytest`.

---

### Task 1: Update Recipe Pydantic Model

**Files:**
- Modify: `extern/ASP/models/analysis.py:107-133`
- Test: `extern/ASP/tests/test_validation.py`

**Step 1: Write failing test for new Recipe model**

Create a test that validates the new Recipe shape (no `outputs` field, `inputs` instead of `depends_on`):

```python
# Add to extern/ASP/tests/test_validation.py or a new test file
def test_new_recipe_model_has_inputs_not_depends_on():
    """Recipe model should have 'inputs' field, not 'outputs' or 'depends_on'."""
    from models.analysis import Recipe
    recipe = Recipe(command="python train.py", inputs=["cleaned_data"])
    assert recipe.inputs == ["cleaned_data"]
    assert recipe.command == "python train.py"
    assert not hasattr(recipe, "outputs") or "outputs" not in recipe.model_fields
    assert not hasattr(recipe, "depends_on") or "depends_on" not in recipe.model_fields
```

**Step 2: Run test to verify it fails**

Run: `cd extern/ASP && python -m pytest tests/test_validation.py::test_new_recipe_model_has_inputs_not_depends_on -v`
Expected: FAIL — `Recipe` still has `outputs` and `depends_on`

**Step 3: Update the Recipe model**

In `extern/ASP/models/analysis.py`, replace the Recipe class:

```python
class Recipe(BaseModel):
    """A build rule that produces an output.

    Recipes are the execution contract: run this command (optionally in a
    container) to produce the parent output. Dependencies on other outputs
    are declared via ``inputs``.
    """

    model_config = ConfigDict(extra="forbid")

    command: str = Field(description="Command to execute (e.g., 'python src/train.py')")
    inputs: list[str] | None = Field(
        default=None,
        description="Output IDs that must be materialized before this recipe runs",
    )
    container: str | None = Field(
        default=None,
        description="Container image override (defaults to node-level container)",
    )
    resources: Resources | None = Field(
        default=None,
        description="Compute resource requirements",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd extern/ASP && python -m pytest tests/test_validation.py::test_new_recipe_model_has_inputs_not_depends_on -v`
Expected: PASS

**Step 5: Commit**

```bash
cd extern/ASP && git add models/analysis.py tests/test_validation.py
git commit -m "refactor: update Recipe model — inputs instead of outputs/depends_on"
```

---

### Task 2: Add Recipe Field to Output Model

**Files:**
- Modify: `extern/ASP/models/analysis.py:67-91`
- Test: `extern/ASP/tests/test_validation.py`

**Step 1: Write failing test**

```python
def test_output_model_accepts_inline_recipe():
    """Output should accept an optional inline Recipe."""
    from models.analysis import Output, Recipe
    output = Output(
        id="trained_model",
        type="data",
        recipe=Recipe(command="python train.py", inputs=["cleaned_data"]),
    )
    assert output.recipe is not None
    assert output.recipe.command == "python train.py"

def test_output_model_recipe_is_optional():
    """Output recipe should be optional (external/manual artifacts)."""
    from models.analysis import Output
    output = Output(id="external_data", type="data")
    assert output.recipe is None
```

**Step 2: Run test — expect FAIL**

**Step 3: Add recipe field to Output**

In `extern/ASP/models/analysis.py`, update the Output class to add a `recipe` field:

```python
class Output(BaseModel):
    """An expected output from the analysis.

    Outputs can declare their provenance via ``from`` to trace which
    sub-analysis produces them (e.g., ``from: inference.posterior``).

    Outputs can optionally include an inline ``recipe`` that describes
    how to produce them (command, container, resources, input dependencies).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique identifier for the output",
    )
    type: Literal["metric", "figure", "table", "data", "report"] = Field(
        description="Type of output"
    )
    description: str | None = Field(default=None, description="Description of the output")

    # Provenance: which sub-analysis produces this output
    from_: str | None = Field(
        default=None,
        alias="from",
        description="Sub-analysis output that produces this "
        "(e.g., 'sub_analysis.output_id')",
    )

    # Execution: how to produce this output
    recipe: Recipe | None = Field(
        default=None,
        description="Inline recipe describing how to produce this output",
    )
```

Note: `Recipe` is defined before `Output` in the file, so no forward reference issue.

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
cd extern/ASP && git add models/analysis.py tests/test_validation.py
git commit -m "feat: add optional recipe field to Output model"
```

---

### Task 3: Remove Top-Level Recipes from Analysis Model

**Files:**
- Modify: `extern/ASP/models/analysis.py:240-243`
- Test: `extern/ASP/tests/test_validation.py`

**Step 1: Write failing test**

```python
def test_analysis_model_rejects_top_level_recipes():
    """Analysis should no longer accept a top-level 'recipes' field."""
    from models.analysis import Analysis
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        Analysis(
            version="1.0",
            name="test",
            inputs=[],
            outputs=[],
            recipes={"train": {"command": "python train.py", "outputs": ["x"]}},
        )
```

**Step 2: Run test — expect FAIL** (recipes field still exists)

**Step 3: Remove recipes from Analysis**

In `extern/ASP/models/analysis.py`, delete lines 240-243:

```python
    # DELETE these lines:
    recipes: dict[str, Recipe] | None = Field(
        default=None,
        description="Map of recipe IDs to build rules that produce outputs",
    )
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
cd extern/ASP && git add models/analysis.py tests/test_validation.py
git commit -m "refactor: remove top-level recipes from Analysis model"
```

---

### Task 4: Regenerate JSON Schemas

**Files:**
- Modify: `extern/ASP/spec/draft/analysis.schema.json`
- Run: `extern/ASP/tools/generate_schemas.py`

**Step 1: Regenerate schemas**

Run: `cd extern/ASP && python tools/generate_schemas.py`

**Step 2: Verify the generated schema**

Check that `spec/draft/analysis.schema.json`:
- Has `recipe` as an optional property inside output definitions
- Does NOT have a top-level `recipes` property on Analysis
- Recipe schema has `command`, `inputs`, `container`, `resources` (no `outputs`, no `depends_on`)

**Step 3: Commit**

```bash
cd extern/ASP && git add spec/draft/
git commit -m "chore: regenerate JSON schemas for new recipe format"
```

---

### Task 5: Rewrite Recipe Validation in semantic.py

**Files:**
- Modify: `extern/ASP/src/asp/validation/semantic.py:96-98,196-199,280-388`
- Test: `extern/ASP/tests/test_validation.py`

This is the largest ASP change. The old `_validate_recipes()` and `_detect_recipe_cycle()` functions are replaced with output-to-output validation.

**Step 1: Write failing tests for new validation**

```python
def test_recipe_inputs_must_reference_declared_outputs():
    """Recipe inputs must reference outputs declared in the same analysis."""
    data = {
        "version": "1.0",
        "name": "test",
        "inputs": [],
        "outputs": [
            {"id": "result", "type": "metric", "recipe": {
                "command": "python run.py",
                "inputs": ["nonexistent"],
            }},
        ],
    }
    errors = validate_analysis(data)
    codes = [e.code for e in errors]
    assert "INVALID_RECIPE_INPUT" in codes

def test_recipe_output_dependency_cycle():
    """Cycle in output dependencies should be caught."""
    data = {
        "version": "1.0",
        "name": "test",
        "inputs": [],
        "outputs": [
            {"id": "a", "type": "data", "recipe": {"command": "run_a", "inputs": ["b"]}},
            {"id": "b", "type": "data", "recipe": {"command": "run_b", "inputs": ["a"]}},
        ],
    }
    errors = validate_analysis(data)
    codes = [e.code for e in errors]
    assert "RECIPE_CYCLE" in codes

def test_valid_recipe_on_output():
    """Valid inline recipe should pass validation."""
    data = {
        "version": "1.0",
        "name": "test",
        "inputs": [],
        "outputs": [
            {"id": "cleaned", "type": "data", "recipe": {"command": "python clean.py"}},
            {"id": "result", "type": "metric", "recipe": {
                "command": "python analyze.py",
                "inputs": ["cleaned"],
            }},
        ],
    }
    errors = validate_analysis(data)
    assert len(errors) == 0
```

**Step 2: Run tests — expect FAIL**

**Step 3: Rewrite validation**

In `extern/ASP/src/asp/validation/semantic.py`:

1. Replace the old recipe validation call in `validate_analysis()` (lines 96-98) with:

```python
    # Validate output recipes
    errors.extend(_validate_output_recipes(outputs, ""))
```

2. Replace the old call in `_validate_analysis_node()` (lines 196-199) with:

```python
    # Validate output recipes
    node_outputs = node.get("outputs") or []
    errors.extend(_validate_output_recipes(node_outputs, node_path))
```

3. Delete `_validate_recipes()` and `_detect_recipe_cycle()` functions entirely.

4. Add new functions:

```python
def _validate_output_recipes(
    outputs: list[dict[str, Any]],
    path_prefix: str,
) -> list[SemanticError]:
    """Validate inline recipes on outputs.

    Checks:
    - Recipe inputs reference declared output IDs
    - No cycles in the output dependency graph
    """
    errors: list[SemanticError] = []
    outputs_prefix = f"{path_prefix}.outputs" if path_prefix else "outputs"

    # Collect all output IDs at this level
    output_ids = {out.get("id") for out in outputs if out.get("id")}

    # Build dependency graph and validate inputs
    dep_graph: dict[str, list[str]] = {}
    for out in outputs:
        out_id = out.get("id")
        if not out_id:
            continue
        recipe = out.get("recipe")
        if not recipe:
            dep_graph[out_id] = []
            continue
        inputs = recipe.get("inputs") or []
        dep_graph[out_id] = inputs
        for inp_id in inputs:
            if inp_id not in output_ids:
                errors.append(
                    SemanticError(
                        "INVALID_RECIPE_INPUT",
                        f"Recipe input '{inp_id}' is not a declared output",
                        f"{outputs_prefix}.{out_id}.recipe",
                    )
                )

    # Check for cycles
    cycle = _detect_output_cycle(dep_graph)
    if cycle:
        errors.append(
            SemanticError(
                "RECIPE_CYCLE",
                f"Dependency cycle detected: {' -> '.join(cycle)}",
                outputs_prefix,
            )
        )

    return errors


def _detect_output_cycle(dep_graph: dict[str, list[str]]) -> list[str] | None:
    """Detect cycles in output dependency graph. Returns cycle path or None."""
    _white, _gray, _black = 0, 1, 2
    color: dict[str, int] = {oid: _white for oid in dep_graph}
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = _gray
        path.append(node)
        for dep in dep_graph.get(node, []):
            if dep not in color:
                continue  # invalid ref, caught elsewhere
            if color[dep] == _gray:
                cycle_start = path.index(dep)
                return path[cycle_start:] + [dep]
            if color[dep] == _white:
                result = dfs(dep)
                if result:
                    return result
        path.pop()
        color[node] = _black
        return None

    for oid in dep_graph:
        if color[oid] == _white:
            result = dfs(oid)
            if result:
                return result
    return None
```

**Step 4: Run tests — expect PASS**

Run: `cd extern/ASP && python -m pytest tests/test_validation.py -v`

**Step 5: Commit**

```bash
cd extern/ASP && git add src/asp/validation/semantic.py tests/test_validation.py
git commit -m "refactor: output-to-output recipe validation replacing recipe-centric"
```

---

### Task 6: Add Recipe Helpers

**Files:**
- Modify: `extern/ASP/src/asp/helpers.py`
- Modify: `extern/ASP/src/asp/__init__.py`
- Test: `extern/ASP/tests/test_validation.py` (or new helper test file)

**Step 1: Write failing tests**

```python
def test_get_output_dependencies():
    """get_output_dependencies should return output-to-output DAG."""
    from asp.helpers import get_output_dependencies
    data = {
        "outputs": [
            {"id": "clean", "type": "data", "recipe": {"command": "clean.py"}},
            {"id": "train", "type": "data", "recipe": {"command": "train.py", "inputs": ["clean"]}},
            {"id": "eval", "type": "metric", "recipe": {"command": "eval.py", "inputs": ["train"]}},
            {"id": "external", "type": "data"},  # no recipe
        ],
    }
    deps = get_output_dependencies(data)
    assert deps == {"clean": [], "train": ["clean"], "eval": ["train"], "external": []}

def test_get_outputs_with_recipes():
    """get_outputs_with_recipes should return only outputs that have recipes."""
    from asp.helpers import get_outputs_with_recipes
    data = {
        "outputs": [
            {"id": "a", "type": "data", "recipe": {"command": "run_a"}},
            {"id": "b", "type": "data"},
        ],
    }
    result = get_outputs_with_recipes(data)
    assert len(result) == 1
    assert result[0]["id"] == "a"
```

**Step 2: Run tests — expect FAIL**

**Step 3: Add helpers to `extern/ASP/src/asp/helpers.py`**

```python
def get_output_dependencies(data: dict[str, Any]) -> dict[str, list[str]]:
    """Build the output-to-output dependency graph from inline recipes.

    Args:
        data: Analysis data as a dict.

    Returns:
        Dict mapping output_id to list of input output_ids (from recipe.inputs).
        Outputs without recipes have an empty dependency list.
    """
    result: dict[str, list[str]] = {}
    for out in data.get("outputs") or []:
        out_id = out.get("id")
        if not out_id:
            continue
        recipe = out.get("recipe")
        if recipe:
            result[out_id] = recipe.get("inputs") or []
        else:
            result[out_id] = []
    return result


def get_outputs_with_recipes(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Get outputs that have inline recipes.

    Args:
        data: Analysis data as a dict.

    Returns:
        List of output dicts that have a 'recipe' key.
    """
    return [out for out in (data.get("outputs") or []) if out.get("recipe")]
```

**Step 4: Export from `extern/ASP/src/asp/__init__.py`**

Add `get_output_dependencies` and `get_outputs_with_recipes` to the imports.

**Step 5: Run tests — expect PASS**

**Step 6: Commit**

```bash
cd extern/ASP && git add src/asp/helpers.py src/asp/__init__.py tests/
git commit -m "feat: add get_output_dependencies and get_outputs_with_recipes helpers"
```

---

### Task 7: Update Iris Example

**Files:**
- Modify: `extern/ASP/examples/iris/asp.yaml`

**Step 1: Rewrite iris example with inline recipes on outputs**

```yaml
$schema: "https://asp-spec.org/v1/schema.json"
version: "1.0"
name: "Iris Classification Study"
description: |
  A demonstration analysis that builds a classifier for the classic
  Iris dataset, exploring different preprocessing and model choices.
authors:
  - "ASP Examples"
tags:
  - classification
  - sklearn
  - example

inputs:
  - id: iris_data
    type: data
    source: "sklearn.datasets.load_iris"
    description: "Fisher's classic 150-sample, 3-class dataset"

  - id: preprocessing_study
    type: analysis
    ref: "analyses/scaling_comparison_2024"
    description: "Our previous study on scaling methods"

outputs:
  - id: trained_output
    type: data
    description: "Best performing classifier"
    recipe:
      command: python src/train.py

  - id: accuracy
    type: metric
    description: "Classification accuracy on held-out test set"
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

  - id: f1_score
    type: metric
    description: "Macro-averaged F1 score"
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

  - id: confusion_matrix
    type: figure
    description: "Confusion matrix heatmap"
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

  - id: model_comparison
    type: table
    description: "Accuracy by model and preprocessing combination"
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

  - id: conclusion
    type: report
    description: "Summary of classifier performance and suitability for the application"
    recipe:
      command: python src/evaluate.py
      inputs: [trained_output]

decisions:
  scaling:
    label: "Feature Scaling"
    type: method
    rationale: "Scaling affects distance-based algorithms like SVM"
    default: standard
    options:
      none:
        label: "No Scaling"
        description: "Use raw feature values"
      standard:
        label: "StandardScaler"
        description: "Z-score normalization (mean=0, std=1)"
      minmax:
        label: "MinMaxScaler"
        description: "Scale to [0, 1] range"
        incompatible_with:
          - model.svm

  model:
    label: "Classification Model"
    type: method
    rationale: "Core algorithmic choice affecting accuracy and interpretability"
    default: random_forest
    options:
      svm:
        label: "Support Vector Machine"
        description: "Maximum margin classifier"
        requires:
          - scaling.standard
      random_forest:
        label: "Random Forest"
        description: "Ensemble of decision trees"
      logistic:
        label: "Logistic Regression"
        description: "Linear classifier with probabilistic output"

  test_size:
    label: "Test Set Proportion"
    type: parameter
    rationale: "Trade-off between training data and evaluation reliability"
    default: small
    options:
      small:
        label: "20%"
      medium:
        label: "30%"

  random_seed:
    label: "Random Seed"
    type: parameter
    rationale: "For reproducibility and stability testing"
    default: seed_42
    options:
      seed_42:
        label: "42"
      seed_123:
        label: "123"
```

**Step 2: Run ASP validation on the updated example**

Run: `cd extern/ASP && python -m asp.cli validate examples/iris/asp.yaml`
Expected: Validation passes (or minor adjustments needed for schema)

**Step 3: Commit**

```bash
cd extern/ASP && git add examples/iris/asp.yaml
git commit -m "refactor: update iris example to inline recipe format"
```

---

### Task 8: Update ASP Test Fixtures

**Files:**
- Modify: `extern/ASP/tests/fixtures/valid/full.yaml`
- Modify: `extern/ASP/tests/fixtures/valid/nested.yaml`
- Remove: `extern/ASP/tests/fixtures/invalid/recipe_cycle.yaml`
- Remove: `extern/ASP/tests/fixtures/invalid/recipe_duplicate_output.yaml`
- Remove: `extern/ASP/tests/fixtures/invalid/recipe_invalid_dep.yaml`
- Remove: `extern/ASP/tests/fixtures/invalid/recipe_orphan_output.yaml`
- Create: `extern/ASP/tests/fixtures/invalid/recipe_invalid_input.yaml`
- Create: `extern/ASP/tests/fixtures/invalid/recipe_output_cycle.yaml`
- Modify: `extern/ASP/tests/test_validation.py`

**Step 1: Read the existing valid/invalid fixtures to understand current format**

Read all fixture YAML files to understand what needs changing.

**Step 2: Update valid fixtures to use inline recipes on outputs**

Convert any `recipes:` top-level blocks to inline `recipe:` on each output.

**Step 3: Replace invalid recipe fixtures**

Delete the 4 old invalid recipe fixtures. Create 2 new ones:

`recipe_invalid_input.yaml`:
```yaml
version: "1.0"
name: "Invalid recipe input"
inputs: []
outputs:
  - id: result
    type: metric
    recipe:
      command: python run.py
      inputs: [nonexistent_output]
```

`recipe_output_cycle.yaml`:
```yaml
version: "1.0"
name: "Recipe cycle"
inputs: []
outputs:
  - id: a
    type: data
    recipe:
      command: python a.py
      inputs: [b]
  - id: b
    type: data
    recipe:
      command: python b.py
      inputs: [a]
```

**Step 4: Update test_validation.py**

Update test cases that reference old recipe error codes (`ORPHAN_RECIPE_OUTPUT`, `DUPLICATE_RECIPE_OUTPUT`, `INVALID_RECIPE_DEP`) to use new codes (`INVALID_RECIPE_INPUT`, `RECIPE_CYCLE`).

**Step 5: Run full test suite**

Run: `cd extern/ASP && python -m pytest -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
cd extern/ASP && git add tests/ && git add -u tests/
git commit -m "test: update fixtures and tests for inline recipe format"
```

---

## Phase 2: Prism Cleanup

These tasks modify the Prism repo. Run Prism tests with `pytest` from repo root.

---

### Task 9: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

Replace canvas optional dependency with dagster. The full file should have:

```toml
[project.optional-dependencies]
dagster = [
    "dagster>=1.9",
    "dagster-webserver>=1.9",
    "dagster-docker>=0.25",
]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "ruff",
    "mypy",
    "types-PyYAML",
]
```

Remove the `canvas` optional dependency entirely.

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: replace canvas dep with dagster optional dependency"
```

---

### Task 10: Remove Old Files

**Files:**
- Remove: `src/prism/remote.py`
- Remove: `claude/prism/scripts/hpc-guard.sh`
- Remove: `claude/prism/scripts/hpc-session-start.sh`
- Remove: `tests/test_remote.py`

**Step 1: Delete files**

```bash
git rm src/prism/remote.py
git rm claude/prism/scripts/hpc-guard.sh
git rm claude/prism/scripts/hpc-session-start.sh
git rm tests/test_remote.py
```

**Step 2: Commit**

```bash
git commit -m "refactor: remove remote.py, HPC hooks, and remote tests

Replaced by Dagster execution layer (dagster/targets.py, runner resource limits)."
```

---

### Task 11: Rewrite CLI — Remove Canvas/Navigator, HPC References

**Files:**
- Modify: `src/prism/cli.py`

This task strips the CLI down to just `init` and `remote` (placeholder), removing canvas, navigator, and old HPC logic. New commands are added in Phase 4.

**Step 1: Write the stripped CLI**

Remove from `src/prism/cli.py`:
- The entire `canvas` command (lines 809-843)
- The entire `navigator` command and its helpers (lines 851-978)
- All HPC-related code in `_create_claude_settings()` (lines 376-404)
- `_create_project_hpc_config()` function (lines 437-449)
- `_resolve_target_config()` function (lines 410-434)
- HPC gitignore additions in `init` (lines 116-120)
- Target config handling in `init` (lines 76-78, 133-134, 144-146)
- The `--target` option from `init` command
- References to `prism canvas` in the success message (lines 149-150)
- Remove the `from prism.remote import ...` lazy imports throughout
- Remove the old `remote` command group and its subcommands (lines 544-671)
- Remove all remote helper functions (lines 678-801)

Keep:
- `main()` group
- `init` command (simplified — no target)
- `_get_plugin_source_dir()`
- `_create_boilerplate_asp_yaml()`
- `_create_readme()`
- `_create_claude_md()` (simplified — no target_config)
- `_create_claude_settings()` (simplified — no HPC)
- `_init_git_repo()`
- `_create_venv()`

Update `init` success message to reference `prism run` and `claude` instead of canvas.

Update `_create_claude_settings()` to remove HPC guard and HPC session start hooks.

**Step 2: Update conftest.py**

Remove the `targets_dir` and `sample_config` fixtures from `tests/conftest.py` since they reference `prism.remote`.

**Step 3: Update test_cli.py**

Remove `test_remote_help` from TestHelpOption since the remote command group is temporarily gone (re-added in Phase 4).

**Step 4: Run tests**

Run: `pytest -v`
Expected: ALL PASS (minus any tests referencing removed code)

**Step 5: Commit**

```bash
git add src/prism/cli.py tests/conftest.py tests/test_cli.py
git commit -m "refactor: strip CLI to init only, remove canvas/navigator/old-remote"
```

---

## Phase 3: Dagster Core Subpackage

These tasks create `src/prism/dagster/`. All code in this package is guarded by optional dagster imports.

---

### Task 12: Target Configuration

**Files:**
- Create: `src/prism/dagster/__init__.py`
- Create: `src/prism/dagster/targets.py`
- Create: `tests/test_targets.py`

**Step 1: Write failing tests**

```python
# tests/test_targets.py
"""Tests for Dagster target configuration."""
from __future__ import annotations
from pathlib import Path
import pytest
from prism.dagster.targets import (
    get_targets_dir,
    list_targets,
    load_target,
    save_target,
)


@pytest.fixture
def targets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    targets = tmp_path / "targets"
    targets.mkdir()
    monkeypatch.setattr("prism.dagster.targets.get_targets_dir", lambda: targets)
    return targets


@pytest.fixture
def sample_target() -> dict:
    return {
        "name": "perlmutter",
        "backend": "slurm",
        "connection": {
            "hostname": "perlmutter.nersc.gov",
            "username": "testuser",
        },
        "scheduler": {
            "account": "m1234",
            "partition": "gpu",
            "container_runtime": "shifter",
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 240,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 32,
        },
    }


class TestTargetConfig:
    def test_save_then_load(self, targets_dir, sample_target):
        save_target("perlmutter", sample_target)
        loaded = load_target("perlmutter")
        assert loaded is not None
        assert loaded["backend"] == "slurm"
        assert loaded["connection"]["hostname"] == "perlmutter.nersc.gov"

    def test_load_nonexistent(self, targets_dir):
        assert load_target("nonexistent") is None

    def test_list_empty(self, targets_dir):
        assert list_targets() == []

    def test_list_with_targets(self, targets_dir, sample_target):
        save_target("perlmutter", sample_target)
        save_target("other", {"name": "other", "backend": "slurm"})
        assert list_targets() == ["other", "perlmutter"]
```

**Step 2: Run tests — expect FAIL** (module doesn't exist)

**Step 3: Create `src/prism/dagster/__init__.py`**

```python
"""Dagster execution layer for Prism."""
```

**Step 4: Create `src/prism/dagster/targets.py`**

```python
"""Target configuration management for Dagster execution backends."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_targets_dir() -> Path:
    """Return the user-level targets directory (~/.prism/targets/)."""
    return Path.home() / ".prism" / "targets"


def list_targets() -> list[str]:
    """Return names of saved target configurations."""
    targets_dir = get_targets_dir()
    if not targets_dir.exists():
        return []
    return sorted(p.stem for p in targets_dir.glob("*.yaml"))


def load_target(name: str) -> dict[str, Any] | None:
    """Load a saved target configuration by name.

    Returns None if the target config doesn't exist.
    """
    config_path = get_targets_dir() / f"{name}.yaml"
    if not config_path.exists():
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)


def save_target(name: str, config: dict[str, Any]) -> Path:
    """Save a target configuration to ~/.prism/targets/{name}.yaml.

    Returns the path where it was saved.
    """
    targets_dir = get_targets_dir()
    targets_dir.mkdir(parents=True, exist_ok=True)
    config_path = targets_dir / f"{name}.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    return config_path
```

**Step 5: Run tests — expect PASS**

Run: `pytest tests/test_targets.py -v`

**Step 6: Commit**

```bash
git add src/prism/dagster/__init__.py src/prism/dagster/targets.py tests/test_targets.py
git commit -m "feat: add dagster target configuration (replaces remote.py)"
```

---

### Task 13: IO Manager

**Files:**
- Create: `src/prism/dagster/io_manager.py`
- Create: `tests/test_io_manager.py`

**Step 1: Write failing tests**

```python
# tests/test_io_manager.py
"""Tests for ASP IO Manager."""
from __future__ import annotations
from pathlib import Path
import pytest

pytest.importorskip("dagster")

from prism.dagster.io_manager import ASPIOManager


class TestASPIOManager:
    def test_get_path_basic(self, tmp_path):
        mgr = ASPIOManager(project_root=str(tmp_path))
        path = mgr.get_output_path("accuracy", "baseline")
        assert path == tmp_path / "results" / "baseline" / "accuracy"

    def test_get_path_different_universe(self, tmp_path):
        mgr = ASPIOManager(project_root=str(tmp_path))
        path = mgr.get_output_path("accuracy", "experiment1")
        assert path == tmp_path / "results" / "experiment1" / "accuracy"

    def test_get_input_paths(self, tmp_path):
        mgr = ASPIOManager(project_root=str(tmp_path))
        paths = mgr.get_input_paths(["cleaned_data", "params"], "baseline")
        assert paths == {
            "cleaned_data": tmp_path / "results" / "baseline" / "cleaned_data",
            "params": tmp_path / "results" / "baseline" / "params",
        }
```

**Step 2: Run tests — expect FAIL**

**Step 3: Create `src/prism/dagster/io_manager.py`**

```python
"""ASP IO Manager for Dagster — maps (asset, universe) to filesystem paths."""
from __future__ import annotations

from pathlib import Path

try:
    import dagster as dg
    HAS_DAGSTER = True
except ImportError:
    HAS_DAGSTER = False


class ASPIOManager:
    """Maps ASP outputs to filesystem paths following ASP conventions.

    Path convention: results/<universe_id>/<output_id>/
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def get_output_path(self, output_id: str, universe_id: str) -> Path:
        """Get the filesystem path for an output in a given universe."""
        return self.project_root / "results" / universe_id / output_id

    def get_input_paths(
        self, input_ids: list[str], universe_id: str
    ) -> dict[str, Path]:
        """Get filesystem paths for input dependencies."""
        return {
            inp_id: self.get_output_path(inp_id, universe_id)
            for inp_id in input_ids
        }
```

Note: The full Dagster `ConfigurableIOManager` integration (with `handle_output`/`load_input`) will be wired in when we build the asset factory. This provides the core path logic.

**Step 4: Run tests — expect PASS**

Run: `pytest tests/test_io_manager.py -v`

**Step 5: Commit**

```bash
git add src/prism/dagster/io_manager.py tests/test_io_manager.py
git commit -m "feat: add ASP IO Manager with results/<universe>/<output> path convention"
```

---

### Task 14: Container Runner — Docker Backend

**Files:**
- Create: `src/prism/dagster/runner.py`
- Create: `tests/test_runner.py`

**Step 1: Write failing tests**

```python
# tests/test_runner.py
"""Tests for ASP Container Runner."""
from __future__ import annotations
from pathlib import Path
import pytest
from prism.dagster.runner import (
    ASPContainerRunner,
    translate_resources_to_docker_flags,
)


class TestResourceTranslation:
    def test_translate_cpus(self):
        flags = translate_resources_to_docker_flags({"cpus": 4})
        assert "--cpus=4" in flags

    def test_translate_memory(self):
        flags = translate_resources_to_docker_flags({"memory": "16GB"})
        assert "--memory=16g" in flags or "--memory=16gb" in flags

    def test_translate_gpus(self):
        flags = translate_resources_to_docker_flags({"gpus": 1})
        assert "--gpus=1" in flags

    def test_translate_empty(self):
        flags = translate_resources_to_docker_flags({})
        assert flags == []

    def test_translate_time_limit(self):
        flags = translate_resources_to_docker_flags({"time_limit": "2h"})
        # Docker uses --stop-timeout or similar, or we just ignore for docker
        # time_limit is primarily for SLURM
        assert isinstance(flags, list)


class TestDockerRunner:
    def test_build_docker_command(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
        )
        cmd = runner.build_docker_command(
            command="python train.py",
            container="myimage:latest",
            input_ids=["cleaned_data"],
            output_id="trained_model",
            universe_id="baseline",
            resources={},
        )
        assert "docker" in cmd[0]
        assert "myimage:latest" in cmd
        assert "python train.py" in " ".join(cmd)

    def test_build_docker_mounts(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
        )
        mounts = runner.build_docker_mounts(
            input_ids=["cleaned_data"],
            output_id="trained_model",
            universe_id="baseline",
        )
        # Should have input mount (read-only) and output mount
        assert any("/workspace/inputs/cleaned_data" in m for m in mounts)
        assert any("/workspace/outputs/trained_model" in m for m in mounts)
```

**Step 2: Run tests — expect FAIL**

**Step 3: Create `src/prism/dagster/runner.py`**

```python
"""ASP Container Runner — executes recipes in Docker or SLURM containers."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prism.dagster.io_manager import ASPIOManager


@dataclass
class ExecutionResult:
    """Result of executing a recipe."""
    exit_code: int
    output_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


def translate_resources_to_docker_flags(resources: dict[str, Any]) -> list[str]:
    """Translate ASP resource requirements to Docker CLI flags."""
    flags: list[str] = []
    if cpus := resources.get("cpus"):
        flags.append(f"--cpus={cpus}")
    if memory := resources.get("memory"):
        flags.append(f"--memory={memory.lower()}")
    if gpus := resources.get("gpus"):
        flags.append(f"--gpus={gpus}")
    return flags


class ASPContainerRunner:
    """Executes ASP recipes in containers.

    Dispatches to Docker (local) or SLURM (remote) based on backend config.
    """

    def __init__(
        self,
        project_root: str,
        backend: str = "docker",
        default_container: str | None = None,
        target_config: dict[str, Any] | None = None,
    ):
        self.project_root = Path(project_root)
        self.backend = backend
        self.default_container = default_container
        self.target_config = target_config or {}
        self.io_manager = ASPIOManager(project_root)

    def execute(
        self,
        command: str,
        output_id: str,
        universe_id: str,
        container: str | None = None,
        inputs: list[str] | None = None,
        resources: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a recipe, dispatching to the configured backend."""
        if self.backend == "docker":
            return self._run_docker(
                command=command,
                container=container or self.default_container,
                input_ids=inputs or [],
                output_id=output_id,
                universe_id=universe_id,
                resources=resources or {},
            )
        elif self.backend == "slurm":
            return self._run_slurm(
                command=command,
                container=container or self.default_container,
                input_ids=inputs or [],
                output_id=output_id,
                universe_id=universe_id,
                resources=resources or {},
            )
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def build_docker_mounts(
        self,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
    ) -> list[str]:
        """Build Docker volume mount arguments."""
        mounts: list[str] = []
        for inp_id in input_ids:
            host_path = self.io_manager.get_output_path(inp_id, universe_id)
            mounts.extend([
                "-v", f"{host_path}:/workspace/inputs/{inp_id}:ro"
            ])
        output_path = self.io_manager.get_output_path(output_id, universe_id)
        output_path.mkdir(parents=True, exist_ok=True)
        mounts.extend([
            "-v", f"{output_path}:/workspace/outputs/{output_id}"
        ])
        return mounts

    def build_docker_command(
        self,
        command: str,
        container: str | None,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        resources: dict[str, Any],
    ) -> list[str]:
        """Build the full docker run command."""
        if container is None:
            raise ValueError(
                f"No container specified for output '{output_id}' "
                "and no default_container configured"
            )
        cmd = ["docker", "run", "--rm"]
        cmd.extend(translate_resources_to_docker_flags(resources))
        cmd.extend(self.build_docker_mounts(input_ids, output_id, universe_id))
        cmd.extend([container, "sh", "-c", command])
        return cmd

    def _run_docker(
        self,
        command: str,
        container: str | None,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        resources: dict[str, Any],
    ) -> ExecutionResult:
        """Execute a recipe in a Docker container."""
        docker_cmd = self.build_docker_command(
            command=command,
            container=container,
            input_ids=input_ids,
            output_id=output_id,
            universe_id=universe_id,
            resources=resources,
        )
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
        )
        output_path = self.io_manager.get_output_path(output_id, universe_id)
        return ExecutionResult(
            exit_code=result.returncode,
            output_path=output_path,
            metadata={
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "docker_command": " ".join(docker_cmd),
            },
        )

    def _run_slurm(
        self,
        command: str,
        container: str | None,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        resources: dict[str, Any],
    ) -> ExecutionResult:
        """Execute a recipe via SLURM. Placeholder for Phase 2."""
        raise NotImplementedError("SLURM backend not yet implemented")
```

**Step 4: Run tests — expect PASS**

Run: `pytest tests/test_runner.py -v`

**Step 5: Commit**

```bash
git add src/prism/dagster/runner.py tests/test_runner.py
git commit -m "feat: add ASP Container Runner with Docker backend"
```

---

### Task 15: Asset Factory

**Files:**
- Create: `src/prism/dagster/assets.py`
- Create: `tests/test_assets.py`

This is the core of the Dagster integration. It reads `asp.yaml` and generates Dagster asset definitions.

**Step 1: Write failing tests**

```python
# tests/test_assets.py
"""Tests for ASP asset factory."""
from __future__ import annotations
from pathlib import Path
import pytest

pytest.importorskip("dagster")

import dagster as dg
from prism.dagster.assets import build_asset_definitions, build_definitions


@pytest.fixture
def sample_asp_yaml(tmp_path):
    """Create a sample asp.yaml with inline recipes."""
    asp_yaml = tmp_path / "asp.yaml"
    asp_yaml.write_text("""
version: "1.0"
name: "Test Analysis"
inputs:
  - id: raw_data
    type: data
outputs:
  - id: cleaned
    type: data
    recipe:
      command: python clean.py
      container: test:latest
  - id: result
    type: metric
    recipe:
      command: python analyze.py
      inputs: [cleaned]
      container: test:latest
  - id: external
    type: data
decisions: {}
""")
    (tmp_path / "universes").mkdir()
    baseline = tmp_path / "universes" / "baseline.yaml"
    baseline.write_text("id: baseline\\ndecisions: {}\\n")
    return tmp_path


class TestBuildAssetDefinitions:
    def test_generates_assets_for_outputs_with_recipes(self, sample_asp_yaml):
        assets = build_asset_definitions(sample_asp_yaml)
        asset_keys = {a.key.path[-1] for a in assets}
        assert "cleaned" in asset_keys
        assert "result" in asset_keys

    def test_skips_outputs_without_recipes(self, sample_asp_yaml):
        assets = build_asset_definitions(sample_asp_yaml)
        asset_keys = {a.key.path[-1] for a in assets}
        assert "external" not in asset_keys

    def test_asset_dependencies(self, sample_asp_yaml):
        assets = build_asset_definitions(sample_asp_yaml)
        result_asset = next(a for a in assets if a.key.path[-1] == "result")
        dep_keys = {dep.asset_key.path[-1] for dep in result_asset.specs[0].deps}
        assert "cleaned" in dep_keys

    def test_build_definitions_returns_definitions(self, sample_asp_yaml):
        defs = build_definitions(sample_asp_yaml)
        assert isinstance(defs, dg.Definitions)
```

**Step 2: Run tests — expect FAIL**

**Step 3: Create `src/prism/dagster/assets.py`**

```python
"""Asset factory — generates Dagster assets from asp.yaml output recipes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import dagster as dg
except ImportError:
    raise ImportError(
        "Dagster is not installed. Install with: pip install prism[dagster]"
    )

from asp.helpers import load_yaml, get_outputs

from prism.dagster.io_manager import ASPIOManager
from prism.dagster.runner import ASPContainerRunner


def build_asset_definitions(
    project_path: Path,
) -> list[dg.AssetsDefinition]:
    """Read asp.yaml and generate one @asset per output with a recipe."""
    spec = load_yaml(project_path / "asp.yaml")
    outputs = get_outputs(spec)

    assets: list[dg.AssetsDefinition] = []
    for output_def in outputs:
        output_id = output_def.get("id")
        recipe = output_def.get("recipe")
        if not output_id or not recipe:
            continue
        assets.append(_build_single_asset(output_id, recipe))

    return assets


def _build_single_asset(
    output_id: str,
    recipe: dict[str, Any],
) -> dg.AssetsDefinition:
    """Build a single Dagster asset from an output recipe."""
    input_ids = recipe.get("inputs") or []
    command = recipe["command"]
    container = recipe.get("container")
    resources = recipe.get("resources") or {}

    @dg.asset(
        name=output_id,
        deps=[dg.AssetKey(i) for i in input_ids],
        metadata={
            "command": command,
            "container": container or "default",
        },
    )
    def _asset(
        context: dg.AssetExecutionContext,
        asp_runner: ASPContainerRunner,
    ) -> dg.MaterializeResult:
        # TODO: universe_id from partition key when partitions are wired
        universe_id = "baseline"
        result = asp_runner.execute(
            command=command,
            container=container,
            inputs=input_ids,
            output_id=output_id,
            universe_id=universe_id,
            resources=resources,
        )
        return dg.MaterializeResult(
            metadata={
                "exit_code": result.exit_code,
                "output_path": str(result.output_path),
                **result.metadata,
            }
        )

    return _asset


def build_definitions(
    project_path: Path,
    target: str | None = None,
) -> dg.Definitions:
    """Build complete Dagster Definitions from an ASP project.

    This is the main entry point for the Dagster integration.
    """
    from prism.dagster.targets import load_target

    spec = load_yaml(project_path / "asp.yaml")
    default_container = spec.get("container")

    # Build runner from target config
    if target:
        target_config = load_target(target)
        if target_config is None:
            raise ValueError(f"Unknown target: {target}")
        runner = ASPContainerRunner(
            project_root=str(project_path),
            backend=target_config.get("backend", "docker"),
            default_container=default_container,
            target_config=target_config,
        )
    else:
        runner = ASPContainerRunner(
            project_root=str(project_path),
            backend="docker",
            default_container=default_container,
        )

    assets = build_asset_definitions(project_path)

    return dg.Definitions(
        assets=assets,
        resources={
            "asp_runner": runner,
            "io_manager": dg.FilesystemIOManager(),
        },
    )
```

**Step 4: Run tests — expect PASS**

Run: `pytest tests/test_assets.py -v`

**Step 5: Commit**

```bash
git add src/prism/dagster/assets.py tests/test_assets.py
git commit -m "feat: add asset factory — asp.yaml outputs to Dagster @asset definitions"
```

---

### Task 16: Status Queries

**Files:**
- Create: `src/prism/dagster/status.py`
- Create: `tests/test_status.py`

**Step 1: Write failing tests**

```python
# tests/test_status.py
"""Tests for materialization status queries."""
from __future__ import annotations
from pathlib import Path
import pytest
from prism.dagster.status import get_output_status


class TestOutputStatus:
    def test_no_results_dir(self, tmp_path):
        """Status should show 'not run' when no results exist."""
        asp_yaml = tmp_path / "asp.yaml"
        asp_yaml.write_text("""
version: "1.0"
name: test
inputs: []
outputs:
  - id: result
    type: metric
    recipe:
      command: python run.py
""")
        status = get_output_status(tmp_path, "baseline")
        assert status["result"] == "not_run"

    def test_results_exist(self, tmp_path):
        """Status should show 'materialized' when output files exist."""
        asp_yaml = tmp_path / "asp.yaml"
        asp_yaml.write_text("""
version: "1.0"
name: test
inputs: []
outputs:
  - id: result
    type: metric
    recipe:
      command: python run.py
""")
        result_dir = tmp_path / "results" / "baseline" / "result"
        result_dir.mkdir(parents=True)
        (result_dir / "output.json").write_text("{}")
        status = get_output_status(tmp_path, "baseline")
        assert status["result"] == "materialized"
```

**Step 2: Run tests — expect FAIL**

**Step 3: Create `src/prism/dagster/status.py`**

```python
"""Materialization status queries for ASP outputs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from asp.helpers import load_yaml, get_outputs


def get_output_status(
    project_path: Path,
    universe_id: str,
) -> dict[str, str]:
    """Get materialization status for all outputs in a universe.

    Returns dict mapping output_id to status string:
    - "materialized": output directory exists and contains files
    - "not_run": output directory doesn't exist or is empty
    """
    spec = load_yaml(project_path / "asp.yaml")
    outputs = get_outputs(spec)

    status: dict[str, str] = {}
    for out in outputs:
        out_id = out.get("id")
        if not out_id:
            continue
        if not out.get("recipe"):
            continue
        output_path = project_path / "results" / universe_id / out_id
        if output_path.exists() and any(output_path.iterdir()):
            status[out_id] = "materialized"
        else:
            status[out_id] = "not_run"

    return status


def get_all_universe_status(
    project_path: Path,
) -> dict[str, dict[str, str]]:
    """Get status for all universes.

    Returns dict mapping universe_id to output status dict.
    """
    universes_dir = project_path / "universes"
    if not universes_dir.exists():
        return {}

    result: dict[str, dict[str, str]] = {}
    for universe_file in sorted(universes_dir.glob("*.yaml")):
        universe_data = load_yaml(universe_file)
        universe_id = universe_data.get("id", universe_file.stem)
        result[universe_id] = get_output_status(project_path, universe_id)

    return result
```

**Step 4: Run tests — expect PASS**

Run: `pytest tests/test_status.py -v`

**Step 5: Commit**

```bash
git add src/prism/dagster/status.py tests/test_status.py
git commit -m "feat: add materialization status queries"
```

---

### Task 17: Wire Up dagster/__init__.py

**Files:**
- Modify: `src/prism/dagster/__init__.py`

**Step 1: Update the package init to export public API**

```python
"""Dagster execution layer for Prism.

Provides:
- build_definitions(): Generate Dagster Definitions from asp.yaml
- ASPContainerRunner: Execute recipes in Docker/SLURM containers
- ASPIOManager: Map (asset, universe) to filesystem paths
- get_output_status(): Query materialization status
"""
from prism.dagster.assets import build_asset_definitions, build_definitions
from prism.dagster.io_manager import ASPIOManager
from prism.dagster.runner import ASPContainerRunner
from prism.dagster.status import get_all_universe_status, get_output_status
from prism.dagster.targets import list_targets, load_target, save_target

__all__ = [
    "build_asset_definitions",
    "build_definitions",
    "ASPContainerRunner",
    "ASPIOManager",
    "get_output_status",
    "get_all_universe_status",
    "list_targets",
    "load_target",
    "save_target",
]
```

**Step 2: Commit**

```bash
git add src/prism/dagster/__init__.py
git commit -m "feat: wire up prism.dagster public API"
```

---

## Phase 4: CLI Commands

---

### Task 18: Add `prism run` Command

**Files:**
- Modify: `src/prism/cli.py`
- Create: `tests/test_cli_run.py`

**Step 1: Write failing test**

```python
# tests/test_cli_run.py
"""Tests for prism run CLI command."""
from pathlib import Path
import pytest
from click.testing import CliRunner
from prism.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestRunCommand:
    def test_run_without_dagster_shows_error(self, runner, tmp_path, monkeypatch):
        """prism run should error gracefully if dagster not installed."""
        # This test verifies graceful degradation
        # The actual import check is in the command implementation
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        assert "Materialize" in result.output or "run" in result.output

    def test_run_help(self, runner):
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
```

**Step 2: Add `prism run` command to `src/prism/cli.py`**

Add after the init command section:

```python
# =============================================================================
# Dagster execution commands
# =============================================================================


def _require_dagster():
    """Check that dagster is installed, exit with helpful message if not."""
    try:
        import dagster  # noqa: F401
    except ImportError:
        console.print("[red]Error:[/red] Dagster is not installed.")
        console.print("  Install with: [cyan]pip install prism[dagster][/cyan]")
        raise SystemExit(1)


@main.command()
@click.argument("outputs", nargs=-1)
@click.option("--universe", "-u", default=None, help="Universe to materialize for")
@click.option("--target", "-t", default=None, help="Execution target (e.g., perlmutter)")
def run(outputs: tuple[str, ...], universe: str | None, target: str | None) -> None:
    """Materialize ASP outputs via Dagster.

    Runs recipes to produce outputs. Without arguments, materializes all
    outputs for all universes.

    Examples:
        prism run                           # all outputs, all universes
        prism run accuracy                  # specific output
        prism run --universe baseline       # specific universe
        prism run accuracy -u baseline      # specific output + universe
        prism run --target perlmutter       # run on SLURM
    """
    _require_dagster()

    from prism.dagster.assets import build_definitions

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    defs = build_definitions(project_path, target=target)

    console.print(f"[bold]Materializing outputs...[/bold]")

    import dagster as dg

    # Select assets to materialize
    all_assets = defs.get_all_asset_specs()
    if outputs:
        selection = list(outputs)
    else:
        selection = [spec.key.path[-1] for spec in all_assets]

    # Execute
    try:
        result = dg.materialize(
            assets=defs.get_asset_graph().assets,
            resources=defs.get_resource_top_level_defs(),
            selection=selection,
        )
        if result.success:
            console.print(f"[green]✓[/green] Materialization complete")
        else:
            console.print(f"[red]✗[/red] Materialization failed")
            raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Step 3: Run tests — expect PASS**

Run: `pytest tests/test_cli_run.py -v`

**Step 4: Commit**

```bash
git add src/prism/cli.py tests/test_cli_run.py
git commit -m "feat: add prism run command for Dagster materialization"
```

---

### Task 19: Add `prism status` Command

**Files:**
- Modify: `src/prism/cli.py`

**Step 1: Add status command to CLI**

```python
@main.command()
@click.option("--universe", "-u", default=None, help="Show status for specific universe")
def status(universe: str | None) -> None:
    """Show materialization status of all outputs.

    Displays a table of outputs vs universes with materialization state.

    Examples:
        prism status
        prism status --universe baseline
    """
    from prism.dagster.status import get_all_universe_status, get_output_status
    from asp.helpers import load_yaml, get_outputs

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    spec = load_yaml(project_path / "asp.yaml")
    name = spec.get("name", "Unknown")
    outputs = get_outputs(spec)
    recipe_outputs = [o for o in outputs if o.get("recipe")]

    if universe:
        all_status = {universe: get_output_status(project_path, universe)}
    else:
        all_status = get_all_universe_status(project_path)

    if not all_status:
        console.print("[yellow]No universes found.[/yellow]")
        return

    from rich.table import Table

    table = Table(title=f"{name} — Materialization Status")
    table.add_column("Output", style="cyan")
    for uid in all_status:
        table.add_column(uid)

    materialized = 0
    total = 0
    for out in recipe_outputs:
        out_id = out["id"]
        row = [out_id]
        for uid, universe_status in all_status.items():
            s = universe_status.get(out_id, "not_run")
            total += 1
            if s == "materialized":
                materialized += 1
                row.append("[green]ok[/green]")
            else:
                row.append("[dim]not run[/dim]")
        table.add_row(*row)

    console.print(table)
    console.print(f"\n  [green]{materialized}[/green] materialized  "
                  f"[dim]{total - materialized}[/dim] pending")
```

**Step 2: Commit**

```bash
git add src/prism/cli.py
git commit -m "feat: add prism status command"
```

---

### Task 20: Add `prism dev` Command

**Files:**
- Modify: `src/prism/cli.py`

**Step 1: Add dev command**

```python
@main.command()
@click.option("--port", "-p", default=3000, type=int, help="Port for Dagster webserver")
def dev(port: int) -> None:
    """Launch Dagster webserver UI for the current project.

    Opens a web UI showing the asset graph, run history, and
    materialization status.

    Examples:
        prism dev
        prism dev --port 8080
    """
    _require_dagster()

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    console.print(f"[bold]Starting Dagster webserver on port {port}...[/bold]")
    console.print(f"  Open [cyan]http://localhost:{port}[/cyan] in your browser")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        subprocess.run(
            ["dagster-webserver", "-h", "0.0.0.0", "-p", str(port)],
            check=True,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Dagster webserver stopped[/dim]")
    except FileNotFoundError:
        console.print("[red]Error:[/red] dagster-webserver not found.")
        console.print("  Install with: [cyan]pip install prism[dagster][/cyan]")
        raise SystemExit(1)
```

**Step 2: Commit**

```bash
git add src/prism/cli.py
git commit -m "feat: add prism dev command for Dagster webserver"
```

---

### Task 21: Rewrite `prism remote` Command

**Files:**
- Modify: `src/prism/cli.py`

**Step 1: Add new remote command group with Dagster-style target config**

```python
# =============================================================================
# Remote target commands (Dagster executor configuration)
# =============================================================================


@main.group()
def remote() -> None:
    """Manage execution targets (Docker, SLURM)."""
    pass


@remote.command("setup")
@click.argument("name", required=False)
@click.option("--list", "list_targets_flag", is_flag=True, help="List saved targets")
def remote_setup(name: str | None, list_targets_flag: bool) -> None:
    """Configure an execution target.

    Sets up connection details, scheduler config, and resource limits
    for remote execution backends (SLURM, etc.).

    Examples:
        prism remote setup perlmutter
        prism remote setup --list
    """
    from prism.dagster.targets import list_targets, save_target

    if list_targets_flag:
        saved = list_targets()
        if not saved:
            console.print("[dim]No saved targets.[/dim]")
            console.print("Run [cyan]prism remote setup <name>[/cyan] to configure one.")
        else:
            console.print("[bold]Saved targets:[/bold]")
            for t in saved:
                console.print(f"  - {t}")
        return

    if name is None:
        console.print("[red]Error:[/red] Provide a target name.")
        raise SystemExit(1)

    console.print(f"\n[bold]Setting up target: [cyan]{name}[/cyan][/bold]\n")

    backend = click.prompt(
        "  Backend", type=click.Choice(["slurm", "pbs"]), default="slurm"
    )
    hostname = click.prompt("  Hostname")
    username = click.prompt("  Username", default=os.environ.get("USER", ""))
    account = click.prompt("  Account/allocation")
    partition = click.prompt("  Partition", default="regular")
    container_runtime = click.prompt(
        "  Container runtime",
        type=click.Choice(["shifter", "podman-hpc", "singularity"]),
        default="shifter",
    )

    console.print("\n  [bold]Resource limits[/bold]")
    max_nodes = click.prompt("    Max nodes per job", type=int, default=4)
    max_walltime = click.prompt("    Max walltime (minutes)", type=int, default=240)
    max_concurrent = click.prompt("    Max concurrent jobs", type=int, default=8)
    max_node_hours = click.prompt("    Max node-hours per session", type=int, default=32)

    config = {
        "name": name,
        "backend": backend,
        "connection": {"hostname": hostname, "username": username},
        "scheduler": {
            "account": account,
            "partition": partition,
            "container_runtime": container_runtime,
        },
        "resource_limits": {
            "max_nodes": max_nodes,
            "max_walltime_minutes": max_walltime,
            "max_concurrent_jobs": max_concurrent,
            "max_node_hours_per_session": max_node_hours,
        },
    }

    path = save_target(name, config)
    console.print(f"\n[green]✓[/green] Saved to [cyan]{path}[/cyan]")
    console.print(f"Use with: [cyan]prism run --target {name}[/cyan]")


@remote.command("show")
@click.argument("name")
def remote_show(name: str) -> None:
    """Show a saved target configuration."""
    from prism.dagster.targets import load_target

    config = load_target(name)
    if config is None:
        console.print(f"[red]Error:[/red] No saved target '{name}'.")
        raise SystemExit(1)

    console.print(f"[bold]Target: {name}[/bold]\n")
    console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))
```

**Step 2: Add remote help test back to test_cli.py**

**Step 3: Run tests**

Run: `pytest -v`

**Step 4: Commit**

```bash
git add src/prism/cli.py tests/test_cli.py
git commit -m "feat: rewrite prism remote for Dagster executor targets"
```

---

### Task 22: Update `prism init`

**Files:**
- Modify: `src/prism/cli.py`

**Step 1: Update init to generate dagster.yaml and updated .gitignore**

In the init command, after creating the directory structure:

- Add `dagster.yaml` generation:
```python
    # Create dagster.yaml for Dagster instance configuration
    dagster_yaml = {
        "storage": {
            "sqlite": {
                "base_dir": "results/.dagster",
            },
        },
    }
    (directory / "dagster.yaml").write_text(
        yaml.dump(dagster_yaml, default_flow_style=False, sort_keys=False)
    )
```

- Update .gitignore to include `results/.dagster/`
- Update success message to reference `prism run`

**Step 2: Update test for init to check dagster.yaml**

```python
def test_init_creates_dagster_yaml(self, runner, tmp_path):
    project_dir = tmp_path / "dagster-test"
    result = runner.invoke(main, ["init", str(project_dir), "--no-git", "--no-venv"])
    assert result.exit_code == 0
    assert (project_dir / "dagster.yaml").exists()
```

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git add src/prism/cli.py tests/test_cli.py
git commit -m "feat: update prism init to generate dagster.yaml"
```

---

## Phase 5: Skills

---

### Task 23: Create `/prism-run` Skill

**Files:**
- Create: `claude/prism/skills/prism-run/SKILL.md`

Write the skill that teaches Claude how to execute recipes via Dagster. This is a documentation file (SKILL.md), not code.

The skill should cover:
1. Pre-execution validation (`asp validate asp.yaml`)
2. Checking recipe completeness (all target outputs have recipes)
3. Running `prism run [OUTPUT...] --universe <name>`
4. Monitoring with `prism status`
5. Inspecting outputs in `results/<universe_id>/`
6. Failure diagnosis and re-run workflow
7. Target selection for HPC

**Commit:**

```bash
git add claude/prism/skills/prism-run/SKILL.md
git commit -m "feat: add /prism-run skill for execution workflow"
```

---

### Task 24: Create `/prism-status` Skill

**Files:**
- Create: `claude/prism/skills/prism-status/SKILL.md`

Quick-reference skill for pipeline inspection:
- `prism status` for overview table
- `prism dev` for full Dagster UI
- How to interpret materialization states
- Re-materialization commands

**Commit:**

```bash
git add claude/prism/skills/prism-status/SKILL.md
git commit -m "feat: add /prism-status skill for pipeline inspection"
```

---

### Task 25: Update Existing Skills

**Files:**
- Modify: `claude/prism/skills/prism/SKILL.md`
- Modify: `claude/prism/skills/prism-new/SKILL.md`
- Modify: `claude/prism/skills/prism-verify/SKILL.md`
- Modify: `claude/prism/templates/CLAUDE.md`

Update each skill:
- `/prism`: Add execution section covering run/status/dev, new recipe format
- `/prism-new`: Update recipe registration step to use inline recipe on outputs
- `/prism-verify`: Add `prism status` as authoritative materialization source
- Template CLAUDE.md: Update workflow to include execution commands

**Commit:**

```bash
git add claude/prism/skills/ claude/prism/templates/
git commit -m "docs: update existing skills for Dagster execution layer"
```

---

## Phase 6: Integration Testing

---

### Task 26: End-to-End Test

**Files:**
- Create: `tests/test_integration.py`

Write an integration test that:
1. Creates a project with `prism init`
2. Writes an `asp.yaml` with inline recipes
3. Calls `build_definitions()` and verifies asset graph
4. Calls `get_output_status()` and verifies "not_run"
5. Verifies `prism status` CLI output

This does NOT test actual Docker execution (that requires Docker daemon).

```python
# tests/test_integration.py
"""Integration tests for the Dagster execution layer."""
from pathlib import Path
import pytest
from click.testing import CliRunner
from prism.cli import main


@pytest.fixture
def project_dir(tmp_path):
    """Create a project with init, then add inline recipes."""
    runner = CliRunner()
    project = tmp_path / "test-project"
    runner.invoke(main, ["init", str(project), "--no-git", "--no-venv"])

    # Overwrite asp.yaml with recipes
    (project / "asp.yaml").write_text("""
version: "1.0"
name: "Integration Test"
inputs:
  - id: raw_data
    type: data
outputs:
  - id: cleaned
    type: data
    recipe:
      command: python src/clean.py
      container: python:3.11
  - id: result
    type: metric
    recipe:
      command: python src/analyze.py
      inputs: [cleaned]
      container: python:3.11
decisions: {}
""")
    return project


class TestIntegration:
    def test_init_creates_dagster_yaml(self, project_dir):
        assert (project_dir / "dagster.yaml").exists()

    def test_status_shows_not_run(self, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        # Ensure universes exist
        (project_dir / "universes" / "baseline.yaml").write_text(
            "id: baseline\ndecisions: {}\n"
        )
        from prism.dagster.status import get_output_status
        status = get_output_status(project_dir, "baseline")
        assert status["cleaned"] == "not_run"
        assert status["result"] == "not_run"

    @pytest.mark.skipif(
        not pytest.importorskip("dagster", reason="dagster not installed"),
        reason="dagster not installed",
    )
    def test_build_definitions(self, project_dir):
        from prism.dagster.assets import build_definitions
        defs = build_definitions(project_dir)
        import dagster as dg
        assert isinstance(defs, dg.Definitions)
```

**Commit:**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests for Dagster execution layer"
```

---

### Task 27: Run Full Test Suite and Fix Issues

**Step 1:** Run: `pytest -v`
**Step 2:** Run: `ruff check src/ tests/`
**Step 3:** Fix any failures
**Step 4:** Final commit

```bash
git add -u
git commit -m "fix: resolve test and lint issues from Dagster integration"
```

---

## Summary

| Phase | Tasks | What |
|-------|-------|------|
| 1 | 1-8 | ASP schema changes (recipe on output) |
| 2 | 9-11 | Prism cleanup (remove old code) |
| 3 | 12-17 | Dagster core (targets, IO, runner, factory, status) |
| 4 | 18-22 | CLI commands (run, status, dev, remote, init update) |
| 5 | 23-25 | Skills (/prism-run, /prism-status, updates) |
| 6 | 26-27 | Integration tests |
