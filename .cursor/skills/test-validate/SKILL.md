---
name: test-validate
description: Run project tests (covering the Python backend, the Vue frontend, and locale validation)
---

## 🚀 Common Test Commands

### Backend (Python)
Recommended to run with the virtual environment activated:

```bash
# Run all backend tests
pytest

# Run a specific test file
pytest tests/test_<name>.py -v
pytest tests/test_frontend_locales.py  # Check frontend locale (en-US) key coverage and structure
pytest tests/test_backend_locales.py   # Check backend .po modules and templates (en-US)

# Run with a coverage report
pytest --cov=src

# Run the server (dev mode)
python src/server/main.py --dev
```

### Frontend (Vue/Node)
Must be run from the `web` directory:

```bash
# Run all frontend unit tests
cd web && npm run test

# Run with a frontend coverage report
cd web && npm run test:coverage

# Run the TypeScript type check
cd web && npm run type-check
```

## 📊 Test Coverage and Guidelines

After making code changes, consider whether tests are needed:

| Change type | Test recommendation |
|-------------|---------------------|
| Bug fix | Add a regression test to prevent recurrence; make sure the test **fails before the fix** and **passes after the fix** |
| New feature | Unit tests + integration tests if multiple modules are affected |
| Refactor | Existing tests should pass; add tests if behavior changes |
| Config/docs | Usually no tests needed |
| New locale strings | **Must** run `test_frontend_locales.py` / `test_backend_locales.py` to make sure the en-US keys, `.po` modules, and templates are complete and well-formed |

> **Tip:** When writing backend tests, refer to `.cursor/rules/testing.mdc` and prefer the existing project fixtures such as `dummy_avatar` and `mock_llm_managers`, to avoid duplicate mocks or spending real tokens.
