# Testing Guide

This document describes the project's test architecture, the test environment, and how to add new test cases.

## 1. Test File Layout

Tests live under `tests/`:

*   `tests/conftest.py`: global pytest configuration with all global fixtures, hooks, and settings. This is the key file for understanding how the test environment is built.
*   `tests/test_*.py`: unit and integration tests for individual modules.
    *   `test_action_*.py`: tests for avatar actions (cultivation, combat, movement, etc.).
    *   `test_*.py`: tests for core systems (lifespan, breakthroughs, economy, etc.).
*   `tests/tools/`: tests for tool scripts (e.g. i18n build checks).

## 2. Test Environment Design

To keep tests stable, fast, and isolated from the development environment, `tests/conftest.py` provides the following mechanisms.

### 2.1 Environment Isolation

*   **Log isolation (`configure_test_logging`)**:
    *   Logs written during tests are redirected to a temporary directory so they don't pollute the project's `logs/` folder.
    *   Logs are also sent to `stderr` so pytest can capture and show them (on failure).
*   **Save isolation (`isolate_save_path`)**:
    *   All save files produced during tests are redirected to a temporary directory.
    *   `CONFIG.paths.saves` is monkeypatched dynamically so tests don't interfere with each other or with your real local saves.

### 2.2 Determinism and Stability

*   **Fixed random seed (`fixed_random_seed`)**:
    *   Automatically seeds the `random` module with `42` so random behavior is identical on every run.
*   **Language reset (`force_chinese_language`, legacy name)**:
    *   Resets the game language to the registry's default locale (`en-US`) and reloads game configs around each test, so asserted strings (item names, messages, etc.) are stable and global i18n state does not leak between tests.

### 2.3 Core Mocks and Fixtures

To avoid depending on external services (such as LLM APIs) and to simplify test writing, the following core fixtures are provided:

*   **`mock_llm_managers` (autouse)**:
    *   **Key point**: automatically mocks every core component that calls an LLM, including `llm_ai`, `StoryTeller`, `HistoryManager`, etc.
    *   Prevents tests from consuming tokens.
    *   Prevents failures caused by network issues or non-deterministic LLM output.
    *   **Usage**: to customize LLM return values, accept `mock_llm_managers` as a test argument and set `return_value` on its mock objects.

*   **Base world construction**:
    *   `base_map`: creates a 10x10 all-plains map.
    *   `base_world`: a game world instance built on `base_map`.

*   **Test avatar (`dummy_avatar`)**:
    *   Creates a standard test avatar:
        *   Realm: Qi Refinement
        *   Spiritual root: Metal (`Root.GOLD`)
        *   Alignment: Righteous
        *   Position: (0, 0)
    *   **Note**: traits (`personas`) and techniques are cleared so randomly generated attributes don't affect results.

*   **City avatar (`avatar_in_city`)**:
    *   Based on `dummy_avatar`, but located in a city with starting funds and an empty inventory. Suited for testing purchases, auctions, and other in-city actions.

*   **Test items (`mock_item_data`)**:
    *   Provides a standard set of test items (elixirs, materials, weapons, treasures) that can be handed to avatars directly.

## 3. Adding Tests

### 3.1 Create a Test File

Create a new `test_<module_name>.py` file under `tests/`.

### 3.2 Write Test Cases

Import `pytest` and the modules you need. Usually requesting `dummy_avatar` or `avatar_in_city` is enough to get started.

#### Example: testing a new action

```python
import pytest
from src.classes.action import ActionStatus

# Use pytest.mark.asyncio for async functions
@pytest.mark.asyncio
async def test_my_new_action(dummy_avatar):
    # 1. Arrange
    # e.g. give the avatar specific resources
    dummy_avatar.magic_stone = 100

    # 2. Act
    # assume an action function named do_something
    # result = await do_something(dummy_avatar)

    # 3. Assert
    # assert result.status == ActionStatus.SUCCESS
    # assert dummy_avatar.magic_stone == 0
```

### 3.3 Handling LLM Calls

`mock_llm_managers` intercepts LLM calls automatically, but sometimes you need to simulate a specific LLM reply.

```python
@pytest.mark.asyncio
async def test_action_with_llm(dummy_avatar, mock_llm_managers):
    # Get the mock object
    mock_ai = mock_llm_managers["ai"]

    # Set the expected return value
    mock_ai.decide.return_value = {"decision": "attack"}

    # Run code that depends on the LLM...

    # Verify the LLM was called
    mock_ai.decide.assert_called_once()
```

### 3.4 Tips

1.  **Parametrized tests**: `@pytest.mark.parametrize` runs the same test logic with different inputs; ideal for numeric boundaries or combinations of states.
2.  **Mocking time**: if a test involves the passage of time, modify `dummy_avatar.world.month_stamp` or related time attributes directly.
3.  **Checking logs**: if a test fails for unclear reasons, look at the console log output (redirected to stderr).

## 4. Running Tests

*   Run all tests:
    ```bash
    pytest
    ```
*   Run tests in a specific file:
    ```bash
    pytest tests/test_my_feature.py
    ```
*   Run tests matching a keyword:
    ```bash
    pytest -k "cultivate"
    ```
