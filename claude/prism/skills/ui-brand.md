# Prism UI Brand

Visual patterns for user-facing Prism output. Skills reference this file for consistent formatting.

## Stage Banners

Use for major phase transitions.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► {STAGE NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Stage names (uppercase):**
- `RESEARCH QUESTION`
- `ANALYSIS STRUCTURE`
- `DEEP DIVE — [CHUNK NAME]`
- `FINALIZING`
- `SPECIFICATION COMPLETE ✓`

---

## Status Symbols

```
✓  Complete / Reviewed / Passed
○  Pending / Unreviewed
◆  In Progress
✗  Failed / Error
⚠  Warning
```

---

## Action Prompts

When user input or action is needed:

```
───────────────────────────────────────────────────────────────
→ ACTION DESCRIPTION
───────────────────────────────────────────────────────────────
```

---

## Next Up Block

At end of major completions:

```
───────────────────────────────────────────────────────────────

▶ Next Up

**{Description}** — {one-line detail}

`{copy-paste command}`

<sub>`/clear` first → fresh context window</sub>

───────────────────────────────────────────────────────────────

Also available:
- `/prism-insights` — description
- Other options

───────────────────────────────────────────────────────────────
```

---

## Tables

```
| Chunk | Decisions | Reviewed | Artefacts |
|-------|-----------|----------|-----------|
| main  | 3         | 2/3      | 2         |
```

---

## Anti-Patterns

- Varying banner widths
- Mixing banner styles (`===`, `---`, `***`)
- Skipping `PRISM ►` prefix in banners
- Random emoji
- Missing Next Up block after completions
