# acem-cost-estimation

Use when the user wants to estimate what it would have cost (time/dollars)
for an AI coding agent to build an existing codebase, or wants a
token+HITL cost forecast for a planned agentic software project — applies
the ACEM (Agentic Cost Estimation Model) methodology.

> [!WARNING]
> ACEM has not been validated against real project data. This skill is
> exploratory and testing tooling — no cost figure it produces should be
> treated as an accurate or guaranteed estimate. See
> `references/opportunities.md`.

## Installation

### Claude Code

```bash
cp -r /path/to/acem-cost-estimation/ ~/.claude/skills/acem-cost-estimation/
```

Or symlink:
```bash
ln -s /path/to/acem-cost-estimation/ ~/.claude/skills/acem-cost-estimation
```

Then invoke with: `/acem-cost-estimation`

### Codex

Place the plugin directory where Codex can find it, then add an entry to your marketplace:

**`~/.agents/plugins/marketplace.json`** (create if absent):
```json
{
  "name": "personal",
  "interface": { "displayName": "Personal Plugins" },
  "plugins": [
    {
      "name": "acem-cost-estimation",
      "source": { "source": "local", "path": "/path/to/acem-cost-estimation/" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

### Antigravity

**Global install** (all workspaces):
```bash
cp -r /path/to/acem-cost-estimation/ ~/.gemini/antigravity/skills/acem-cost-estimation/
```

**Workspace install** (current project only):
```bash
cp -r /path/to/acem-cost-estimation/ .agents/skills/acem-cost-estimation/
```

The root `SKILL.md` has no Claude Code-specific metadata, so it's used as-is —
no separate Antigravity variant needed.

Skills are auto-discovered. You can also mention the skill by name to force activation.

### Gemini CLI

Gemini CLI installs extensions directly from GitHub:

```bash
gemini extensions install https://github.com/keithmackay/estimator
```

To update:
```bash
gemini extensions update acem-cost-estimation
```

The skill is auto-discovered from `GEMINI.md` after installation. Note: this
extension lives inside the larger `estimator` repo rather than its own
repo — if `gemini extensions install` requires the extension at the repo
root, clone the repo and point Gemini CLI at the
`skill/acem-cost-estimation/` subdirectory instead, or copy that
subdirectory into its own repo.

## Compatibility

| Feature | Claude Code | Codex | Antigravity | Gemini CLI |
|---------|:-----------:|:-----:|:-----------:|:----------:|
| Core skill (inventory → cost calculation workflow) | ✅ | ✅ | ✅ | ✅ |
| Bundled calculator (`acem_calculate.py`) | ✅ | ✅ | ✅ | ✅ |
| Sub-documents (`references/`) | ✅ | ✅ | ✅ | ✅ |

This skill uses no Claude Code-specific frontmatter (`metadata`,
`retrieval`, `tags`), no subagent/`Task`-tool dispatch, and no hooks — so
there are no platform gaps to document. All four platforms run the same
workflow and the same calculator.

## References

- **Claude Code Skills:** https://code.claude.com/docs/en/skills
- **Codex Plugins:** https://developers.openai.com/codex/plugins/build
- **Antigravity Skills:** https://antigravity.google/docs/skills
- **Gemini CLI Extensions:** https://github.com/google-gemini/gemini-cli/blob/main/docs/extension.md
- **Agent Skills open standard:** https://agentskills.io/home
- **ACEM paper:** https://arxiv.org/abs/2608.02582
