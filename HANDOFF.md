# HANDOFF - Kariimc/whome-diagnostic-tool

> Continuity doc. Any agent must resume cold from this file with zero briefing.
> Update it in the same commit as any code change.

**Seeded:** 2026-07-15 from verified repo state. Sections marked UNVERIFIED were not
provable from the repo alone - fill them in, do not guess.

## Verified facts

| | |
|---|---|
| Repo | `Kariimc/whome-diagnostic-tool` |
| Namespace | user `Kariimc` |
| Default branch | `main` |
| Visibility | public |
| Language | Python |
| Files | 23 |
| Last commit | 2026-06-25 - Add "Make a 22H2 USB/ISO" action and explicit window move/resize |
| Branches | 1 |
| Open PRs | 0 |

**Top-level dirs:** `assets`, `core`, `ui`

**Root files:** `.gitattributes`, `.gitignore`, `README.md`, `build.bat`, `main.py`, `requirements.txt`, `run.bat`

**Existing docs:** `README.md`

## Current state

**UNVERIFIED.** Percent-complete and working/broken status cannot be derived from
the repo alone. Do not write a number here you have not proven. Read the code, run
the build, then record what you observed and how you observed it.

## Exact next steps

**UNVERIFIED.** Fill in on first real session in this repo.

## Open decisions

**UNVERIFIED.**

## Rules

- Repos span TWO namespaces: user `Kariimc` AND org `shift9-studio`. Enumerate with
  `gh api '/user/repos?affiliation=owner,collaborator,organization_member'`, never
  `gh repo list Kariimc` alone. See `Kariimc/my-skills` `rules/10-repo-topology.md`.
- Never assert an absence, status, or completion without proving your scope was exhaustive.
- Update this file in the same commit as any code change. A global pre-commit hook enforces it.
