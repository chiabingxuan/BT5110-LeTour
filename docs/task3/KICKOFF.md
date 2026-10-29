# Kickoff prompt for Claude Code

Run in this folder: `claude`, then paste:

---
Read CLAUDE.md, then everything in docs/task3/ (ui_spec.md, olap_narratives.md, the screenshots in docs/task3/screenshots/, and docs/task3/design_source/).

Then:
1. Create a local branch `feat/task3-dashboard` from main.
2. Inspect the repo and load the data per the README (data/ and .env are already in place locally). Report row counts per table and the sanity checks listed in CLAUDE.md.
3. Give me a plan: the SQL views you'll create, the app structure, how each requirement a–e and each narrative E1–E15 (including the [fix] items) maps to a page/visual, and your proposal for the Points/KOM method plus the other open questions in CLAUDE.md.

Don't write app code until I approve the plan. Never push, open a PR or commit to main without asking me first.
---

## For later sessions
- "Continue from the Suggested build order in CLAUDE.md; tell me which milestone you're on and check in after it."
- Before pushing: "Show me `git log main..HEAD --oneline` and a summary of changes; I'll tell you when to push."
