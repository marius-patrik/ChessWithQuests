# Repository Development Guidelines & Agent Rules

## Rules for AI Agents & Contributors
1. **Unit Tests with Every Commit**: Every commit that adds or modifies functionality, classes, or methods must be accompanied by corresponding unit tests in the `tests/` directory. All tests must pass locally via `pytest` before committing or pushing.
2. **Language Consistency**: All code, class names, method names, variables, comments, docstrings, and documentation must be written in English.
3. **Commit Granularity**: Keep commits focused and modular — specifically maintain one commit per class/component when implementing diagram specifications.
4. **CI Readiness**: Ensure `.github/workflows/ci.yml` passes cleanly on all supported Python versions without warnings or test failures.
