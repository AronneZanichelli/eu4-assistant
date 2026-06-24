# Coding Conventions

**Analysis Date:** 2026-06-23

This codebase is pure Python 3.11+ (no linter/formatter config committed). Conventions below are derived from the consistent style across `eu4_assistant_bot/*.py`. Follow them when adding code so new modules match the existing pipeline.

## Module Layout (canonical order)

Every module in `eu4_assistant_bot/` follows the same top-to-bottom structure. Replicate this order:

1. Module docstring (triple-quoted, summary + behaviour notes; references classes with `:class:` Sphinx-style roles)
2. `from __future__ import annotations` (present in **every** module — required for `X | None` / `dict[str, Any]` syntax on 3.11)
3. Stdlib imports, then third-party (`watchdog`, `PyQt6`), then local relative imports (`.config`, `..models`)
4. Module-level `logger = logging.getLogger(__name__)` (when the module logs)
5. Module-level constants (UPPER_SNAKE, often with `_` prefix when private — see below)
6. Enums
7. Dataclasses
8. Classes / functions

Reference: `eu4_assistant_bot/decision_engine.py`, `eu4_assistant_bot/watcher.py`, `eu4_assistant_bot/extractor.py`.

## Naming Patterns

**Files:**
- `snake_case.py`, one cohesive responsibility per file (`save_unzipper.py`, `pause_controller.py`, `state_reader.py`)
- Test files mirror the module name: `eu4_assistant_bot/parser.py` → `tests/test_parser.py`

**Classes:**
- `PascalCase`. Service/engine classes are nouns: `DecisionEngine`, `StateExtractor`, `FileWatcher`, `SaveSnapshotAdapter`, `ModBuilder`.
- Internal/private classes get a leading underscore: `_SaveFileHandler` (`watcher.py:40`), `_LegacyClausewitzParser` (`parser.py:205`), `_RecommendationCard` (`ui/advisor_panel.py:17`).

**Functions / methods:**
- `snake_case`. Public methods are verbs: `evaluate_risks`, `extract`, `read_json_snapshot`, `extract_gamestate`.
- Private helpers get a leading underscore: `_monthly_balance`, `_extract_economy`, `_pause_game`, `_coerce`, `_tokenize`.

**Variables:** `snake_case`. Short locals (`c` for country block, `n` for length, `tok` for token) are used in tight parser loops only.

**Constants:**
- Module-level public constants: `UPPER_SNAKE` (`MODE_PRESETS`, `RISK_PROFILE_PRESETS` in `config.py:70,109`).
- Module-level *private* tuning constants: `_UPPER_SNAKE`, often visually aligned in a block. Example from `decision_engine.py:17`:
  ```python
  _PRIO_COALITION          = 0.95
  _PRIO_DEBT               = 0.92
  _PRIO_MANPOWER           = 0.90
  _MERCHANT_NODE_MIN_VALUE: float = 3.0   # minimum node value to flag missing merchant
  ```
  Magic numbers (priorities, thresholds, scale factors) are **always** lifted to a named module constant with an inline `#` comment, never inlined. Mirror this when adding new heuristics.

**Numeric literals:** use underscores for thousands: `10_000`, `20_000`, `5_000` (`config.py:41`, `decision_engine.py`).

## Type Hints

**Mandatory and pervasive.** Every function signature, dataclass field, and most locals that hold collections are annotated.

- Built-in generics (PEP 585): `dict[str, Any]`, `list[RiskReason]`, `tuple[dict, int]` — never `typing.Dict`/`List`.
- Optionals use `X | None` (PEP 604), enabled by `from __future__ import annotations`.
- `typing.Any` is used for untyped Clausewitz parse trees (`dict[str, Any]`) and JSON payloads.
- `typing.Callable` for injected callbacks: `Callable[[Path], None]`, `Callable[[PauseEvent], Any]` (`pause_controller.py:55`).
- Return types are always annotated, including `-> None` and `-> int` (CLI `run()` returns `int` exit code: `main.py:28`).
- Locals that start empty get an explicit annotation so the type is clear: `reasons: list[RiskReason] = []`, `comp: dict[str, int] = {}`.

## Dataclasses

Dataclasses are the **primary modelling tool**. Conventions:

- **`@dataclass(slots=True)` is the default** for all data models (`config.py`, `models.py`, `decision_engine.py`, `executor.py`, `pause_controller.py`, `extractor` outputs). Use `slots=True` unless you have a reason not to.
  - **Exception:** `watcher.py:32` (`SaveEvent`) and `mod_builder.py:25` (`ModInstallResult`) use plain `@dataclass` (no slots). Slots is the norm; these two are the outliers.
- **Mutable defaults use `field(default_factory=...)`** — never bare mutable defaults:
  ```python
  armies: list[ArmyState] = field(default_factory=list)        # models.py:60
  composition: dict[str, int] = field(default_factory=dict)    # models.py:33
  ```
- **`Path` defaults that depend on `Path.home()` use `default_factory`** so they resolve at instantiation, not import — this keeps config testable (documented at `config.py:3`):
  ```python
  data_dir: Path = field(default_factory=lambda: Path.home() / ".eu4-assistant")  # config.py:99
  ```
- **Validation in `__post_init__`** with raised `ValueError` and an f-string showing the bad value. Pattern from `config.py:43`:
  ```python
  def __post_init__(self) -> None:
      if not (0.0 <= self.coalition_risk_threshold <= 1.0):
          raise ValueError(
              f"coalition_risk_threshold must be in [0, 1], got {self.coalition_risk_threshold}"
          )
  ```
- **Defaults are "safe empty" values** so missing save-file fields never crash downstream (`models.py:5`): numerics default to `0`/`0.0`, strings to `""`, collections to empty. `GameSnapshot` exposes a `GameSnapshot.empty(country="UNK")` classmethod factory (`models.py:132`).
- **Copy presets with `dataclasses.replace`** rather than mutating shared instances (`config.py:120`): `safety=replace(MODE_PRESETS[mode])`.

## Enums

- Modes, risk profiles, status codes, and event types are modelled as **`str`-mixin enums** (`class Foo(str, Enum)`) so members serialize directly as their string value and compare to strings:
  ```python
  class BotMode(str, Enum):       # config.py:14
      ASSIST = "assist"
      SEMI_BOT = "semi-bot"
      FULL_BOT = "full-bot"

  class RiskProfile(str, Enum):   # config.py:20
      SAFE = "safe"; BALANCED = "balanced"; AGGRESSIVE = "aggressive"
  ```
- Other `str, Enum` examples: `RiskCode` (dotted codes like `"coalition.high"`, `decision_engine.py:55`), `SaveEventType` (`watcher.py:27`), `PauseReason` (`pause_controller.py:23`), `ModInstallStatus` (`mod_builder.py:19`), `LogLevel` (`ui/log_panel.py`).
- **Modes/risk-profiles are wired via preset dicts** keyed by the enum (`config.py`):
  - `MODE_PRESETS: dict[BotMode, SafetyLimits]` — per-mode safety caps.
  - `RISK_PROFILE_PRESETS: dict[RiskProfile, DecisionThresholds]` — per-profile decision thresholds.
  - `build_config(mode, risk_profile)` (`config.py:116`) is the single entry point that composes an `AppConfig` from these presets. Add new modes/profiles by extending the enum **and** its preset dict.
- CLI choices are generated from the enum, never hardcoded: `choices=[m.value for m in BotMode]` (`main.py:250`).

## Error Handling

- **Custom exception per module subsystem**, subclassing `Exception` with a docstring: `SaveFormatError` (`save_unzipper.py:14`), `SnapshotReadError` (`state_reader.py:28`), `SaveAdapterError` (`save_adapter.py:15`). Some store `self.message` and override `__str__`.
- **Wrap-and-reraise with `from exc`** to preserve the cause:
  ```python
  except OSError as exc:
      raise SaveFormatError(f"Cannot read save file: {path}") from exc   # save_unzipper.py:45
  ```
- **Catch narrow exceptions** at the boundary (`OSError`, `json.JSONDecodeError`, `zipfile.BadZipFile`, `(TypeError, ValueError)`), not bare `except`.
- **Broad `except Exception` is allowed only at thread/process boundaries** and is explicitly tagged with a `# noqa: BLE001` or `# pragma: no cover` comment, then logged as a warning instead of crashing:
  ```python
  except Exception as exc:  # noqa: BLE001
      logger.warning("PauseController: pynput failed: %s", exc)   # pause_controller.py:130
  ```
- **Graceful degradation over hard failure:** parsers/extractors return safe defaults (`{}`, empty `GameSnapshot`) on bad input rather than raising — see `parser.py:191`, `extractor.py` defensive `_str/_int/_float` helpers (`extractor.py:299-321`). The CLI catches adapter errors and falls back to `GameSnapshot.empty()` (`main.py:48-67`).

## Optional-Dependency Pattern (graceful import)

Heavy/optional deps (`PyQt6`, `pyautogui`, `pynput`) are imported **lazily inside the function that needs them**, tagged `# noqa: PLC0415`, and fail soft:
```python
try:
    import pyautogui  # type: ignore[import]  # noqa: PLC0415
except ImportError:
    logger.warning("pyautogui not installed — install eu4-assistant-bot[bot] ...")
    return False                                          # executor.py:132
```
`run_with_ui()` (`main.py:165`) defers all PyQt6/UI imports to call time so the core `run()` path works without the `[ui]`/`[bot]` extras installed. Follow this pattern for any new optional integration.

## Logging / Telemetry

- **One logger per module:** `logger = logging.getLogger(__name__)` at module top. The CLI uses a named logger `logging.getLogger("eu4-assistant")` (`main.py:40`).
- **`%`-style lazy formatting**, never f-strings, in log calls: `logger.info("Starting EU4 Assistant in mode: %s", mode.value)` (`main.py:41`). f-strings are used only for exception messages and user-facing UI strings.
- **Log-level intent:** `debug` for high-frequency internal events (queue puts, keypresses), `info` for lifecycle milestones, `warning` for recoverable/degraded paths, `error` for crashes caught at boundaries.
- **Central logging setup:** `telemetry.setup_logging(log_dir, level)` (`telemetry.py:24`) configures a `RotatingFileHandler` (5 MB × 3 backups) + `StreamHandler`, with `force=True`. Format: `"%(asctime)s [%(levelname)s] %(name)s: %(message)s"`.
- **Structured session events** go through `telemetry.emit_event(event_path, event_name, payload)` (`telemetry.py:41`), which appends one JSON object per line to `events.jsonl`. Enums serialize via a custom `_json_default` that emits `obj.value` (`telemetry.py:17`). The startup event payload (`main.py:79`) is the canonical example of the event schema.
- **UI logging is separate** from Python logging: the UI pushes user-facing entries via `window.push_log(LogLevel.X, message)` into the `LogPanel`. User-facing strings are in **Italian** (e.g. `"Nessun piano disponibile — attendi il prossimo salvataggio."`, `main_window.py:163`); internal Python log messages and code are in **English**.

## Docstring Style

- **Module docstrings** are mandatory: a one-line summary, a blank line, then prose describing behaviour. They reference key classes/functions with Sphinx roles: `:class:`~eu4_assistant_bot.models.GameSnapshot``, `:func:`setup_logging`` (see `models.py:1`, `telemetry.py:1`, `decision_engine.py:1`).
- **Class docstrings** describe responsibility; complex ones include a `Parameters`/`Signals`/`Usage::` section in light reStructuredText (`pause_controller.py:36`, `ui/main_window.py:59`, `watcher.py:80`).
- **Public-method docstrings** use Google-style `Args:` / `Returns:` / `Raises:` blocks (`save_unzipper.py:29`, `mod_builder.py:78`).
- **Milestone tags** (`M1`–`M9`) appear throughout docstrings/comments to mark when a feature was introduced and what is deferred (e.g. `"M8 real path"`, `"full menu navigation is deferred to M9"`). Preserve/extend these tags when adding milestone work.
- **Private helpers** get a short one-line docstring describing intent (`_coerce`, `_set_key`, `_tokenize` in `parser.py`).

## Function & Module Design

- **Static helpers** are marked `@staticmethod` when they don't touch instance state (`_monthly_balance`, `_pause_game`, the `_str/_int/_float/_dig` coercers in `extractor.py`). Pure module-level helper functions (`_coerce`, `_tokenize`, `_parse_block`) live at module scope, prefixed `_`.
- **Dependency injection for testability:** side-effecting callables are constructor parameters with sensible defaults so tests can pass fakes. Canonical example — `PauseController(send_key=keys.append)` (`pause_controller.py:52`, tests inject a list's `.append`).
- **Pipelines return typed objects, not dicts:** `evaluate_risks → RiskAlerts`, `recommend → list[Recommendation]`, `build_action_plans → list[ActionPlan]`, `simulate/execute → list[ExecutionResult]`. Serialization to dict/JSON happens only at the edges (`telemetry`, `models.to_json`).
- **Imports use explicit relative paths** within the package (`from .models import ...`, `from ..config import BotMode`). No `import *`.
- **Backward-compat shims are kept and deprecated, not deleted:** `ClausewitzParser` is a deprecated factory that emits `DeprecationWarning` and returns `_LegacyClausewitzParser` (`parser.py:235`). New code must use `ClausewitzTextParser`.

---

*Convention analysis: 2026-06-23*
