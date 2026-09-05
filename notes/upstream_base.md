# Upstream Base Branch & Fork Comparison Note

## Upstream Base Reference
The repository maintains a protected `upstream-base` branch permanently pinned to the upstream fork base commit:
- **Upstream Repository**: `https://github.com/docekalgjkt/ChessWithQuests`
- **Upstream Base Commit**: `a98e36d` (`docekalgjkt/ChessWithQuests:main`)
- **Local / Remote Branch**: `origin/upstream-base`

## Purpose & Diff Comparison
The `upstream-base` branch serves as a perpetual, immutable reference point to view the full diff and evolution of this repository from the original fork base without needing to clone or query an external remote.

To inspect changes between the fork base and the current `main` branch:
- **Web Diff URL**: `https://github.com/marius-patrik/ChessWithQuests/compare/upstream-base...main`
- **CLI Diff**: `git diff origin/upstream-base...main`

## Protection Policy
The `upstream-base` branch is protected by GitHub branch protection rules:
- **Force pushes**: Disabled (`allow_force_pushes: false`)
- **Branch deletions**: Disabled (`allow_deletions: false`)
- **Branch lock**: Locked against new pushes (`lock_branch: true`)
- **Enforce admins**: Enabled (`enforce_admins: true`)
