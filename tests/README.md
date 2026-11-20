# Unit Testing Guide

This document explains how to write and maintain unit tests for the Cultivation World Simulator.

## Directory Layout

*   `tests/`: all unit test files live in this directory.
*   `tests/conftest.py`: globally shared fixtures and helper functions.
*   `tests/test_*.py`: tests for specific modules. Names should mirror the modules under `src`, e.g. `src/classes/action/buy.py` maps to `tests/test_buy_action.py`.

## Running Tests

From the project root:

```bash
pytest
```

Or run a specific file:

```bash
pytest tests/test_buy_action.py
```

## Writing New Tests

We use the `pytest` framework. To keep the code clean (DRY), follow these guidelines:

### 1. Use Shared Fixtures

Do not recreate test avatars, maps, or items in every test file. Use the fixtures provided by `tests/conftest.py`:

*   `base_world`: a basic game world environment.
*   `dummy_avatar`: a standard test avatar (at (0,0), Qi Refinement, male).
*   `avatar_in_city`: based on `dummy_avatar`, but placed in a city with 1000 spirit stones and an empty inventory.
*   `mock_item_data`: a standard set of mock items (elixirs, material, weapon, auxiliary) plus matching mock dict structures, convenient for patching the `resolution` module.
*   `mock_llm_managers`: automatically mocks every LLM call so tests never hit a real model.

**Example:**

```python
def test_my_feature(avatar_in_city, mock_item_data):
    # Use the prepared avatar directly
    assert avatar_in_city.magic_stone == 1000

    # Get a standard test item
    test_sword = mock_item_data["obj_weapon"]

    # ...
```

### 2. Mock External Dependencies

Action tests usually need to mock the lookup dicts in `src.utils.resolution`. Combine `mock_item_data` with `unittest.mock.patch`.

**Example:**

```python
from unittest.mock import patch

def test_action_logic(avatar_in_city, mock_item_data):
    materials_mock = mock_item_data["materials"]

    with patch("src.utils.resolution.materials_by_name", materials_mock):
        # Only the materials defined in mock_item_data are visible now
        action = MyAction(avatar_in_city, avatar_in_city.world)
        action.execute("Iron Ore")
```

### 3. Action Test Template

For a new Action under `src.classes.action`, test these three aspects:

1.  **`can_start` (precondition checks)**:
    *   Test the success case.
    *   Test the failure cases (wrong location, insufficient resources, missing target, ...) and assert the returned `reason`.
2.  **`start` (event generation)**:
    *   Verify the returned `Event` contains the correct description text.
3.  **`_execute` (execution logic)**:
    *   Verify changes to Avatar state (spending money, gaining items, losing HP, gaining proficiency, ...).
    *   Verify changes to World state.

### 4. Helper Functions

When you need specific test objects, check the helpers in `conftest.py` first:
*   `create_test_material(...)`
*   `create_test_weapon(...)`
*   `create_test_elixir(...)`
*   `create_test_auxiliary(...)`

If you find a new common need, add it to `conftest.py` instead of copy-pasting it across test files.

## FAQ

*   **`ModuleNotFoundError`**: make sure your IDE or terminal adds the project root to `PYTHONPATH`. `pytest` usually handles this automatically.
*   **The LLM was called**: make sure your test (if it runs the sim loop) uses the `mock_llm_managers` fixture, or patch the relevant modules manually.
