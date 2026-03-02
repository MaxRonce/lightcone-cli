# CLAUDE.md

## Project Overview

Prism is Lightcone Research's ASP-compliant agentic layer. It provides the full agent experience on top of the ASP (Agentic Science Protocol) core specification.

**ASP** = pure specification: schema, validation, insights, verification, helpers, minimal CLI
**Prism** = agentic layer: Claude Code skills/plugin, project scaffolding, remote/HPC config, execution framework

Prism depends on ASP. `pip install prism` gives the full agent experience with ASP as a dependency.

## Repository Structure

```
Prism/
├── extern/ASP              # Symlink to ASP repo
├── src/prism/
│   ├── __init__.py
│   ├── cli.py              # Prism CLI (init, remote, canvas, navigator)
│   └── remote.py           # HPC/remote target config
├── claude/prism/            # Claude Code plugin
│   ├── skills/             # Skills for Claude Code
│   ├── templates/          # Project templates (CLAUDE.md)
│   └── scripts/            # Hook scripts
├── tests/
├── pyproject.toml
└── CLAUDE.md               # This file
```

## Development Commands

```bash
# Install for development
pip install -e ".[dev]"

# Also install ASP in dev mode
cd extern/ASP && pip install -e ".[dev]"

# Run tests
pytest

# Lint and type check
ruff check src/ tests/
mypy src/
```

## Key Conventions

- Prism depends on ASP for all spec operations (validation, schemas, helpers)
- The `prism` CLI handles agent/execution operations (init with scaffolding, remote, canvas)
- The `asp` CLI handles spec operations (validate, info, universe, viz, schema, paper)
- Skills are branded as `/prism-new`, `/prism-build`, `/prism-verify`
- Target configs are stored in `~/.prism/targets/`