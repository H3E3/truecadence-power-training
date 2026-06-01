# TrueCadence AI Coding Discipline

This document captures coding-agent discipline for TrueCadence production and local development. It complements, but does not replace, the production stability rules in `deploy_ubuntu.md` and `docs/production_json_safety.md`.

## Production stability first

- Do not trade stability for speed.
- Do not deploy production changes without explicit user approval.
- For production website/server/data changes, always run the smallest safe checklist before claiming completion:
  - backup relevant files/data;
  - compile/import check;
  - service user and file permission check for data writes;
  - service status;
  - local HTTP smoke test;
  - public URL smoke test when applicable;
  - recent warning/error logs.
- For `/opt/truecadence/data/*.json`, avoid writing final files as root. Mutate as service user `www-data` where possible, or immediately restore owner/mode and verify `www-data` can read/write.

## Karpathy-style coding discipline

Inspired by Andrej Karpathy-style LLM coding failure modes: wrong assumptions, hidden confusion, over-engineering, unrelated edits, and lack of verification.

### 1. Think before coding

- State assumptions before non-trivial implementation.
- If multiple interpretations exist, surface them instead of silently choosing.
- Ask when one missing decision blocks safe progress.
- Push back when the requested approach is riskier than a simpler alternative.

### 2. Simplicity first

- Use the minimum code that solves the requested problem.
- Do not add speculative features, abstractions, configurability, or broad rewrites.
- Prefer small reversible changes, especially in auth, user data, payments, uploads, and deployment code.

### 3. Surgical changes

- Touch only files and code paths directly required by the task.
- Do not refactor adjacent code, reformat unrelated blocks, or delete pre-existing dead code unless explicitly requested.
- Match existing style unless changing style is itself the task.
- Every changed line should trace back to the user request or a necessary verification/safety fix.

### 4. Goal-driven execution

For non-trivial tasks, define success criteria before or during implementation.

Examples:

- Bug fix: reproduce or reason about the failure path, then verify the fixed path.
- Login/session work: verify refresh, browser close/reopen, logout revocation, expired/invalid tokens, and multi-user isolation.
- Data write work: verify JSON syntax, owner/mode, service-user read/write, and no permission regression.
- UI work: verify page loads and the affected page/element is visible or testable.

### 5. Local-first for risky features

- Auth/session, user data, billing, upload parsing, deployment, and server config changes must be developed and tested locally first unless the user explicitly authorizes a production hotfix.
- Local verification is not deployment approval. Ask separately before production deploy.

## Minimal completion evidence

Before saying “done”, provide evidence such as one or more of:

- `py_compile` / import check;
- unit/function-level test;
- local Streamlit HTTP 200;
- public URL HTTP 200 after approved deploy;
- service status;
- permission/read-write check;
- recent log inspection;
- relevant diff summary.
