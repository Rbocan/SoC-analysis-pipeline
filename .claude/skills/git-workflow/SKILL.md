---
name: git-workflow
description: Automated Git Workflow & PR Creation for the SoC Analysis Pipeline. Analyzes code changes across 6 lenses (security, performance, tests, quality, compatibility, breaking changes), generates conventional commit messages, stages commits, produces a full PR description with structured comments, then gates on explicit engineer APPROVE/CHANGES/CANCEL before any git push. Trigger with: "automate my git workflow", "create PR for these changes", "analyze and commit", or /git-workflow.
tools: Bash, Read, Glob, Grep
---

# Automated Git Workflow & PR Creation

Orchestrate the full Git development cycle with an engineer approval gate before any push.

## Project Context

- **Repo**: SoC Analysis Pipeline — FastAPI + Polars/DuckDB backend, Next.js 15 + React 19 frontend
- **Stack signals**: Check `backend/` and `frontend/` structure; use `docker-compose.yml` as deployment reference
- **Branch naming convention**: `feat/<name>`, `fix/<name>`, `refactor/<name>`, `security/<name>`, `chore/<name>`
- **PR target**: `main`

---

## Workflow

### PHASE 1 — ANALYZE CHANGES

Run git diff to collect changed files, then analyze across 6 lenses:

```bash
git status
git diff --stat HEAD
git diff HEAD
```

**Analysis lenses:**

| Lens | What to check |
|------|--------------|
| **Security** | Auth, input validation, SQL injection, exposed secrets, CORS, rate limiting |
| **Performance** | N+1 queries, missing indexes, large payloads, Polars/DuckDB inefficiency |
| **Testing** | New code paths without tests, missing edge cases, coverage gaps |
| **Quality** | Code smells, hardcoded values, duplicate logic, naming |
| **Compatibility** | Breaking API changes, schema migrations, Docker/env changes |
| **Breaking changes** | Anything requiring client update, migration step, or config change |

**Output format:**

```
CHANGE ANALYSIS: [feature/fix name]

Summary: [1-2 sentences]

Security:    [findings] — Risk: Critical/High/Medium/Low/None
Performance: [findings] — Risk: Critical/High/Medium/Low/None
Testing:     [findings] — Risk: Critical/High/Medium/Low/None
Quality:     [findings] — Risk: Critical/High/Medium/Low/None
Compatibility: [findings] — Risk: Critical/High/Medium/Low/None
Breaking:    [YES/NO — describe if yes]

OVERALL RISK: [Critical/High/Medium/Low]

BLOCKERS (must fix before merge):
- [list]

NICE-TO-HAVES (should fix before merge):
- [list]
```

---

### PHASE 2 — COMMIT MESSAGES

Generate atomic commits using conventional commits format:

```
[type]([scope]): [imperative subject, lowercase, no period]

[body — what and why, not how]

[footer — BREAKING CHANGE:, Closes #N]
```

**Types**: `feat` `fix` `refactor` `perf` `style` `test` `docs` `chore` `security`  
**Scopes** (SoC project): `api` `auth` `data` `scheduler` `reports` `frontend` `dashboard` `explorer` `pivot` `admin` `docker` `config` `seed`

Rules:
- One commit per logical change
- Group interdependent changes together
- Breaking changes get `BREAKING CHANGE:` in footer
- Reference issues with `Closes #N`

---

### PHASE 3 — GIT COMMANDS

Show exact copy-paste commands for each commit:

```bash
# Commit N: [description]
git add [specific files — never "git add ."]
git commit -m "$(cat <<'EOF'
[type]([scope]): [subject]

[body]

[footer]
EOF
)"
```

Then show the push command (engineer runs this after APPROVE):

```bash
git push origin [branch-name]
```

---

### PHASE 4 — PR DESCRIPTION & COMMENTS

Generate a complete PR description:

```markdown
## Summary
[What changed and why — 2-3 sentences]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Performance improvement
- [ ] Security hardening
- [ ] Documentation
- [ ] Breaking change

## Related Issues
Closes #[N]

## Changes Made
[Detailed bullet list]

## Why This Approach
[Architecture decisions, trade-offs considered]

## Testing
[What was tested, what reviewers should verify]

## Deployment Notes
[Migration steps, env var changes, docker-compose changes, seed script needs]

## Checklist
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] No hardcoded secrets or credentials
- [ ] docker-compose.yml updated if needed
- [ ] BREAKING CHANGE documented with migration path

## Risks & Mitigations
| Risk | Severity | Mitigation |
|------|----------|-----------|
| ...  | ...      | ...       |

## Rollback
[How to revert if something breaks in production]

## Reviewer Focus
[Specific areas requiring careful review]
```

Then generate 3-4 PR comments as separate blocks:

- **Comment 1 — Security Review** (if security findings exist)
- **Comment 2 — Performance Notes** (if perf impact)
- **Comment 3 — Testing Strategy** (always include)
- **Comment 4 — Deployment & Rollback** (if deployment steps needed)

---

### PHASE 5 — ENGINEER APPROVAL GATE

Present a summary panel, then ask for explicit approval:

```
═══════════════════════════════════════════════════
  GIT WORKFLOW — APPROVAL REQUIRED
═══════════════════════════════════════════════════

ANALYSIS:     [risk level + key findings]
COMMITS:      [N commits queued]
FILES:        [list of staged files]
PR:           [title]
RISK:         [Critical/High/Medium/Low]

BLOCKERS:
  [list or "None"]

NICE-TO-HAVES:
  [list or "None"]

═══════════════════════════════════════════════════

Review the above. Do you approve?

  APPROVE  — Proceed with commits and prepare for push + PR
  CHANGES  — Modify something (describe what)
  CANCEL   — Stop (describe why)

Awaiting your response...
```

**Pre-approval checklist (internal — verify before showing gate):**
- [ ] Analysis complete and accurate
- [ ] Commit messages clear and conventional
- [ ] No sensitive data in staged files (check for `.env`, secrets, tokens)
- [ ] Files staged specifically (no `git add .` shortcuts shown)
- [ ] PR description is comprehensive
- [ ] Risk level clearly stated
- [ ] Blockers vs nice-to-haves distinguished

---

### PHASE 6 — NEXT STEPS (after APPROVE)

```
✅ APPROVED

STEP 1 — RUN COMMITS
[Exact git add + git commit commands from Phase 3]

STEP 2 — PUSH
git push origin [branch-name]

STEP 3 — CREATE PR ON GITHUB
1. Go to: github.com/[repo]/compare/main...[branch]
2. Title: [PR title]
3. Paste the PR description from Phase 4
4. Assign reviewers
5. Click "Create Pull Request"

STEP 4 — ADD PR COMMENTS
Paste the 3-4 comment blocks from Phase 4 as individual comments.

PR is ready for team review.
```

If engineer types **CHANGES**: ask what to modify (commits, description, analysis), update, re-present Phase 5.  
If engineer types **CANCEL**: acknowledge, summarize what needs to be fixed before retrying.

---

## Safety Rules

1. Never commit without engineer seeing analysis first
2. Never show `git push` until engineer types APPROVE
3. Never use `git add .` or `git add -A` — always list specific files
4. Always flag breaking changes prominently
5. Always include rollback strategy for Medium+ risk
6. Never commit files likely containing secrets (`.env`, `*.key`, `credentials.*`)

## Usage Patterns

**After building a feature:**
```
I finished [feature]. Analyze my changes and create a PR workflow.
Branch: feat/[name]
Key changes: [brief description]
```

**Prepare existing branch for merge:**
```
Automate the PR workflow for branch [name].
Analyze all changes vs main and prepare commits + PR.
```

**Batch (multiple logical changes):**
```
I have [N] changes ready. Create the full workflow for each,
ask approval for each separately.
```
