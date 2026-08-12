# Agent Guidelines & Rules

## 1. Logging Rules

1. **No Verbose Strategy Text in Logs**:
   - Do not include explanatory text or descriptive narratives detailing the internal strategy for each game version in console logs, CLI help descriptions, or diagnostic outputs.
   - Keep log messages concise, clean, and focused strictly on runtime events and status updates.

## 2. Architecture & Design Pattern Rules

1. **Configuration Management**:
   - Avoid mutating global configuration variables directly in `config.py` at runtime.
   - Encapsulate settings inside `BotConfig` dataclass instances and pass configuration via dependency injection.

2. **Single Responsibility Principle (SRP)**:
   - Keep functions and methods focused and modular.
   - Avoid monolithic functions; break down complex workflows (> 50 lines) into dedicated sub-methods (e.g., hero scanning, home strategy, modal navigation).

3. **Component Decoupling**:
   - Maintain clear boundaries between modules:
     - `VisionEngine`: Image pattern matching and screen identification.
     - `ActionEngine`: Mouse movement, click execution, and drag dispatches.
     - `BrowserManager`: OS process table queries and browser lifecycle.
     - `BombCryptoBot`: Main decision FSM and cycle loop execution.

## 3. DRY Principles & Code Cleanliness

1. **Vision Matching Helpers**:
   - Use `VisionEngine.find_unique_matches()` instead of duplicating `find_all_templates()` followed by `filter_overlapping_matches()`.

2. **No Magic Numbers**:
   - Extract raw pixel offsets, crop boundaries, coordinate bounds, and sleep intervals into named constants or configuration attributes (e.g., `STAMINA_CROP_XMIN_OFFSET`).

3. **Platform Abstraction**:
   - Avoid scattering raw `sys.platform` conditionals across business logic. Use or extend centralized platform helpers.

## 4. Error Handling & Failure Resilience

1. **No Silent Exception Swallowing**:
   - Never use `except Exception: pass` without logging or catching specific expected exceptions.
   - Log debug info (`logger.debug("...", exc_info=True)`) so failures can be traced during debugging.

2. **Subprocess Timeout Safeguards**:
   - Always pass explicit `timeout` parameters to `subprocess.run()` or `subprocess.check_output()` calls to prevent hanging background tasks.

3. **Thread Pool Safety**:
   - Ensure long-lived worker threads or `ThreadPoolExecutor` instances register cleanup handlers (e.g., `atexit.register(...)`).

## 5. Coding Standards & Verification

1. **Type Annotations**:
   - Include `from __future__ import annotations` at the top of all Python files for type hint compatibility.

2. **Mandatory Verification**:
   - Before completing any task, run `./venv/bin/pytest` and `./venv/bin/ruff check .` to verify that all unit tests pass and no linting errors are present.
