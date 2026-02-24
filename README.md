# Prism

Part of [Lightcone Research](https://github.com/LightconeResearch/lightcone.dev) — install all tools with:
```bash
curl -fsSL https://lightconeresearch.github.io/lightcone.dev/install.sh | bash
```

---

## What is Prism?

Prism is the agentic layer for ASP (Agentic Science Protocol). While ASP provides the core specification format — schemas, validation, insights, and evidence verification — Prism adds the full agent experience:

- **Project scaffolding** with Claude Code integration (`prism init`)
- **Claude Code skills** for analysis creation, insight extraction, and verification
- **HPC/remote target management** for running on compute clusters
- **Visual editors** (Canvas, Navigator)

## Quick Start

```bash
# Create a new analysis project
prism init my-analysis
cd my-analysis

# Open in Claude Code
claude

# Scope your research question
/prism-new
```

## CLI Commands

```bash
# Project setup (full scaffolding with Claude Code config)
prism init my-analysis
prism init my-analysis --no-git
prism init my-analysis --target perlmutter

# HPC/remote targets
prism remote setup perlmutter
prism remote setup --list
prism remote show perlmutter

# Visual editors
prism canvas
prism navigator

# Spec operations (via ASP CLI):
asp validate asp.yaml
asp info
asp universe generate -n baseline
asp viz
asp paper add <doi>
```

## Claude Code Skills

| Skill | Purpose |
|-------|---------|
| `/prism` | Reference guide for working with ASP analyses |
| `/prism-new` | Scope a research question and structure the analysis |
| `/prism-verify` | Verify implementation matches specification |

## Architecture

```
ASP (core)          →  Schema, validation, insights, verification, minimal CLI
Prism (agent layer) →  Skills, scaffolding, remote config, visual editors
Spectrum (future)   →  UI layer
```

Prism depends on ASP. All spec operations (`asp validate`, `asp info`, etc.) are provided by ASP.

## License

Apache 2.0
