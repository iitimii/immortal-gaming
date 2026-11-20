# Contributing Guide

Thank you for your interest in **Cultivation World Simulator**! Contributions of every kind are welcome, including reporting bugs, fixing bugs, improving documentation, and building new features.

> **Important**: Before submitting any new feature, especially gameplay/business features, please discuss it in an issue first and wait for a maintainer to confirm it.
> Major gameplay changes and changes or refactors of core code design patterns are currently **not accepted**.

Please read the guidelines below before contributing; they keep the codebase healthy and consistent in style.

## 🛠️ Development Setup

See [README.md](./README.md) for installation and startup steps.

**Project layout:**
- **Backend (Python)**: lives in `src/`.
- **Frontend (Vue 3)**: lives in `web/`.

Agent-facing engineering rules are aggregated in [AGENTS.md](./AGENTS.md) (sources in `.cursor/rules/`), and topic docs live in `docs/`.

## ✅ Testing Requirements (Mandatory)

Make sure all tests pass before opening a Pull Request. This is key to keeping code quality high.

**Backend tests:**

CI runs Python 3.11.

1. Install the test dependencies (included in `requirements.txt`):
   ```bash
   pip install -r requirements.txt
   ```

2. Run the tests with coverage (60% coverage is required):
   ```bash
   pytest -v --cov=src --cov-report=term --cov-fail-under=60
   ```

**Frontend tests (Vue/Vitest):**

Frontend tests live in `web/`.

1. Enter the frontend directory and install dependencies:
   ```bash
   cd web
   npm install
   ```

2. Run the unit tests:
   ```bash
   npm run test:run
   ```

3. Run the tests with coverage:
   ```bash
   npm run test:coverage
   ```

Make sure every test case passes. If you add a new feature, please add matching tests as well.

## 📝 Code Style

We aim for code that is **concise, elegant, clear, and easy to read**.

### Python backend
- Follow the PEP 8 style guide.
- Add pytest tests for new functionality.

### Vue frontend
- Write logic in **TypeScript**.
- Follow Vue 3 Composition API best practices.
- Name components clearly and keep each one focused on a single responsibility.

### Language
- All code, comments, docs, commit messages, and user-facing strings are written in English. User-facing strings go through the i18n system (`en-US` is the single locale; see [docs/i18n-guide.md](./docs/i18n-guide.md)).

## 🚀 Submitting a Pull Request (PR)

1. **Fork** this repository to your GitHub account.
2. **Clone** your fork locally.
3. Create a new branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-being-fixed
   ```
4. Commit your changes with clear commit messages.
5. Push to your remote branch.
6. Open a **Pull Request** on GitHub and fill in the PR template.

Thanks for contributing! Let's build a more fun and interesting AI cultivation world together.
