# Repository Instructions

Before starting work in this repository:

1. Read `PROJECT_STATUS.md`.
2. Check the current Git status and recent commit before assuming the repository
   is clean or synchronized.
3. Inspect the narrowest relevant implementation and validation surface.

When completing meaningful work, update `PROJECT_STATUS.md` with the new stage,
behavior, validation result, and next task when applicable. Keep the file free
of credentials, tokens, private database contents, and unnecessary personal
data.

Project constraints:

- Never commit or push unless the user explicitly requests it.
- Never expose `client_secrets.json`, `token.pickle`, `.env`, or `data/`.
- Preserve stable upload behavior unless the requested change requires it.
- Prefer the existing Python modules and command-line workflow over new
  abstractions.

Before reporting completion, run the narrowest relevant validation. For a
general Python change, use:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py src
git diff --check
git status --short --branch
```