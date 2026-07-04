# UI templates (AUTO-01 / AUTO-02)

PNG templates consumed by `eu4_assistant_bot.navigation.Navigator.find` for
real in-game action navigation.

## Capture rules (design §6.5)

- **English base UI only.** Capture against EU4 with the interface language set
  to English — *not* the Italian translation mod. Matching the base UI is what
  keeps the translation mod from breaking recognition (see
  `.planning/REQUIREMENTS.md` → "Italian-UI template matching" is out of scope).
- **Tight crops.** Crop each asset to the smallest distinctive region of the
  widget (no surrounding chrome) to keep `cv2.matchTemplate` robust.
- **Document the resolution.** Template matching is resolution / UI-scale
  sensitive. Record the screen resolution and EU4 UI scale each asset was
  captured at, next to the file. Re-capture if the target resolution differs.
- **Windows DPI scale 100%, primary monitor.** Capture and click must share the
  same coordinate space: run EU4 on the primary monitor with Windows display
  scaling at 100% (pyautogui screenshots the primary monitor in physical
  pixels; a scaled desktop makes click coordinates miss the matched target).

## Expected assets (colonize slice)

| File | What to capture |
|------|-----------------|
| `colonizable_marker.png` | The colonist/expansion marker shown over an in-range colonizable province while a free colonist is available. |
| `colonize_button.png` | The "Colonize" action button in the province panel. Used for pre-check (present → go) and post-check (consumed → started). |
| `colonizing_progress.png` *(optional)* | The colonization progress indicator that appears in the province panel after a colonist is sent (stronger post-check). |

Assets are committed once captured during manual integration on Windows + live EU4.
