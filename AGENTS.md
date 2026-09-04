# Repository Development Guidelines & Agent Rules

### 1. Unit Tests with Every Commit
Every commit that adds or modifies code, classes, or methods must be accompanied by corresponding unit tests in the `tests/` directory. All tests must pass locally via `pytest` before committing or pushing.

### 2. Documentation with Every Commit
The repository maintains a `docs/` directory that mirrors the project structure with a corresponding `.md` documentation file for each Python source file. Every commit that creates or updates code must also create or update the respective documentation in `docs/`. Furthermore, the documentation index (`DOCS.md` and its symlink `docs/INDEX.md`) must be updated with every docs change whenever documentation files are added, removed, or modified.

### 3. Object Model Conformance
The object model must strictly adhere to the reference architecture diagram:
`https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D`
Any architectural or structural deviation from the diagram must be explicitly approved by the user and recorded in `.agents/notes/object_model.md`.

### 4. Language Consistency
All code, class names, method names, variables, comments, docstrings, commit messages, and documentation must be written in English.

### 5. Commit Granularity
Keep commits modular, focused, and descriptive. When implementing components from specifications, maintain one commit per class or component.

### 6. CI Readiness & Verification
Every push must maintain green status on GitHub Actions CI across all matrix Python versions (`3.10`, `3.11`, `3.12`, `3.13`).

### 7. Branch & Pull Request Workflow
All changes, features, refactors, and bug fixes must be developed on dedicated topic/feature branches and submitted through GitHub Pull Requests. Direct commits and pushes to the `main` branch are strictly prohibited. Every pull request requires all GitHub Actions CI checks (`CI` matrix and `Verify Docs Layout`) to pass green before merging. The `main` branch must remain protected at all times with required status checks and pull request enforcement.
