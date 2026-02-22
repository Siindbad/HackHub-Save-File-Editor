# R5 Toolbar Adaptation Playbook

This file records the repeatable pipeline used to adapt preview concept `R5: Bracket Frame` into the live toolbar without the long tweak loop.

## Current Baseline (Final)

- Toolbar style is finalized to `B` for both themes.
- Footer `BTN : A/B` controls were removed from runtime UI.
- SIINDBAD and KAMUE both use the R5-style toolbar path.
- KAMUE keeps its own font control behavior:
  - dropdown combo (no `- / +` stepper)
  - KAMUE color harmonization over R5 sprites

## Source of Truth

- Preview ideas: `assets/previews/siindbad-buttonbar-ideas.html`
- Runtime integration: `sins_editor.py`
- Sprite generator: `tools/generate_r5_b_sprites.py`
- Sprite folder: `assets/buttons/variants/B/r5_sprites/`
- Manifest: `assets/buttons/variants/B/r5_sprites/manifest.json`

## Fast Repeat Workflow

1. Finalize concept visuals in preview HTML first.
2. Regenerate sprites/manifest:
   - `python tools/generate_r5_b_sprites.py`
   - optional: `--frames 72 --frame-ms 40`
3. Confirm generated files:
   - `{key}_base.png`, `{key}_hover_###.png` for each toolbar action
   - `search_base.png`
   - `font_base.png`, `font_hover.png`
   - `manifest.json`
4. Run app and verify both themes immediately:
   - SIINDBAD: visual fidelity to preview
   - KAMUE: same geometry behavior, KAMUE palette, dropdown font control intact
5. Run checks:
   - `python -m py_compile sins_editor.py`
   - `pytest -q`

## Runtime Rules That Avoid Rework

- Keep manifest-driven geometry as the authority:
  - button width/height
  - search box width/height/input box
  - font sprite hitboxes (SIINDBAD stepper path only)
- Keep B rendering on label+frame hosts (`tk.Label` in fixed `tk.Frame`) to avoid native button clipping inconsistencies.
- For search slot layout, always use actual allocated host width/height when placing sprite + entry.
- Only draw right-edge helper lines when host is truly squeezed.
- Keep scan animation time-based and lightweight; do not animate the search input frame or KAMUE font dropdown frame.

## Theme Isolation Guardrails

- Do not couple SIINDBAD and KAMUE through shared mutable UI state.
- KAMUE-specific tinting/harmonization must be applied as a KAMUE-only post-pass.
- KAMUE font control remains dropdown regardless of toolbar style internals.
- Any future preview adaptation must be validated in both themes before accepting.

## Regression Checklist

- Frames intact on all toolbar controls at default window size.
- Search input frame has no clipped right edge and no random corner artifact.
- Scan hover:
  - runs only on action buttons
  - starts on hover, stops on leave
  - does not keep running after unrelated actions (like opening a file)
- KAMUE font control:
  - dropdown centered and aligned
  - no stepper symbols visible
- SIINDBAD appearance remains unaffected by KAMUE tuning.
