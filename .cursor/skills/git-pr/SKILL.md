---
name: git-pr
description: Create a Pull Request with correct remote handling
---

## Preflight Check

```bash
git remote -v
# If the origin URL is outdated, fix it:
# git remote set-url origin https://github.com/AI-Cultivation/cultivation-world-simulator.git
```

## Commands

```bash
git checkout main && git pull origin main
git checkout -b <github-username>/<branch-name>
git add <files>
git commit -m "<type>: <description>"
git push -u origin <github-username>/<branch-name>
gh pr create --head <github-username>/<branch-name> --base main --title "<type>: <description>" --body "<body>"
```

## Notes

- Always branch off `main`, not the current branch
- Follow the PR template in `.github/PULL_REQUEST_TEMPLATE.md`
- `<github-username>`: e.g. `xzhseh`
- `<type>`: `feat` | `fix` | `refactor` | `test` | `docs`
