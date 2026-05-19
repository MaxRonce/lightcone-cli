# Codex Support

Codex support is experimental. The Codex bundle is intentionally smaller
than the Claude Code bundle today: it provides project instructions and a
small set of reference skills for ASTRA and lightcone-cli workflows, but it is
not a complete one-to-one port of every Claude skill.

## Create a Codex project

```bash
lc init --agent codex my-analysis
cd my-analysis
codex
```

The Codex scaffold is separate from the Claude Code scaffold:

```text
my-analysis/
├── astra.yaml
├── AGENTS.md              # Codex project instructions
├── .agents/
│   └── skills/            # Codex-readable skill guidance
├── .codex/
│   └── prompts/           # /lc-new and /lc-from-code aliases
├── .lightcone/
├── Containerfile
├── requirements.txt
├── universes/
├── src/
└── results/
```

With `--agent codex`, the project does not install `.claude/` and does not
write `CLAUDE.md`. Use `lc init` or `lc init --agent claude` for the Claude
Code bundle.

## Working With Codex

Start Codex from inside the project directory:

```bash
cd my-analysis
codex
```

Tell Codex what you are trying to do in plain language. For example:

- scope a new analysis from a research question;
- wrap an existing codebase in ASTRA;
- update `astra.yaml` and the implementation together;
- debug a failing `lc run`.

You can also invoke the bundled skills explicitly as `$lc-new` or
`$lc-from-code`, or use Codex's `/skills` picker. The scaffold includes
`/lc-new` and `/lc-from-code` prompt aliases for Codex CLI versions that load
project-local prompts from `.codex/prompts/`.

The key invariant is the same as with Claude: `astra.yaml` is the source of
truth. Code, recipes, decisions, inputs, and outputs should stay synchronized
with the spec. Do not hand-edit files in `results/` to make a run look
successful; final outputs should be produced by `lc run` and backed by
Lightcone manifests.

After relevant changes, ask Codex to run the checks that apply:

```bash
astra validate astra.yaml
lc run
lc status
lc verify
```

If `astra validate` is not available in the environment, Codex should say so
explicitly and continue with `lc status` / `lc verify` where possible. Failed
commands should be fixed or surfaced; do not mask execution failures.
