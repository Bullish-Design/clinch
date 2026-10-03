# AGENTS.md — project instructions

> **Canonical instructions.** This file belongs to the repository. Every agent
> tool reads it through the `CLAUDE.md` symlink.

## What this project is

_One paragraph: what it does, who uses it, what it is not._

## Working here

```bash
devenv shell                     # enter the pinned environment
repoman-sync                     # verify toolchain + install agent skills
```

_Add the build / test / lint commands, and the gate that must be green before a
PR._

## Where things live

_The two or three directories a newcomer actually needs. Deeper detail belongs in
`docs/`, not here._

## The standing configuration

Read the writing rules in
[`.agents/skills/writing/SKILL.md`](.agents/skills/writing/SKILL.md). For
manager routing, start at the `repoman` skill. Keep this file for what is true
of *this* project only.

```bash
copyroom layer list              # which template layers manage this repo
copyroom agent-files check       # conformance report
```
