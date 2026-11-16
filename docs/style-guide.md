# AutoFin Style Guide

AutoFin uses a brutalist, finance-terminal visual system: dense information, hard rules, minimal ornament, and teal only where action or positive signal needs emphasis.

## Logo

Primary logo asset:

- `assets/autofin-logo.png`

Use the logo on off-white, white, or near-black backgrounds. Keep clear space around the full logo equal to at least the height of the capital `A` in the wordmark. Do not add shadows, gradients, outlines, glow effects, or extra slogans.

## Palette

### Brand

| Token | Hex | Use |
| --- | --- | --- |
| Teal 500 | `#1D9E75` | Primary brand accent, positive values, active dark-theme controls |
| Teal 700 | `#0F6E56` | Light-theme accent, brand wordmark, hover/action emphasis |
| Teal 900 | `#085041` | Deep accent, secondary brand mark details |
| Ink 900 | `#0A0A0A` | Light-theme primary text, dark surface base |
| Ink 800 | `#2C2C2A` | Logo text, neutral strong copy |
| Stone 500 | `#888780` | Secondary labels and muted copy |
| Stone 200 | `#D3D1C7` | Dividers in brand assets |
| Red 500 | `#E85454` | Negative values and destructive/error states only |

### Dark Theme

| CSS token | Value |
| --- | --- |
| `--paper` | `#0A0A0A` |
| `--paper-2` | `#0F0F0F` |
| `--ink` | `#FFFFFF` |
| `--ink-2` | `#AAAAAA` |
| `--ink-3` | `#666666` |
| `--rule` | `#1F1F1F` |
| `--rule-2` | `#333333` |
| `--rule-3` | `#4D4D4D` |
| `--hover` | `#151515` |
| `--select` | `#1A1A1A` |
| `--accent` | `#1D9E75` |
| `--accent-2` | `#0F6E56` |
| `--accent-tint` | `rgba(29, 158, 117, 0.12)` |

### Light Theme

| CSS token | Value |
| --- | --- |
| `--paper` | `#FFFFFF` |
| `--paper-2` | `#FAFAF7` |
| `--ink` | `#0A0A0A` |
| `--ink-2` | `#4D4D4D` |
| `--ink-3` | `#AAAAAA` |
| `--rule` | `#E5E5E5` |
| `--rule-2` | `#CCCCCC` |
| `--rule-3` | `#999999` |
| `--hover` | `#F5F5F5` |
| `--select` | `#EFEFEF` |
| `--accent` | `#0F6E56` |
| `--accent-2` | `#085041` |
| `--accent-tint` | `rgba(15, 110, 86, 0.10)` |

## Typography

- UI text: `Inter`, falling back to system sans.
- Numbers, table values, navigation, labels, and compact controls: `JetBrains Mono`.
- Default app text size is `13px`.
- Compact labels use uppercase, `10px`, `0.12em` letter spacing.
- Avoid oversized display type inside app surfaces. AutoFin should feel operational, not like a marketing page.

## Layout

- Use hard `1px` rules for separation.
- Keep radii at `0` unless an existing repeated component already requires rounding.
- Avoid shadows, floating cards, glass effects, gradients, and decorative blobs.
- Prefer dense grids, tables, strips, and inline controls over large empty cards.
- Use the tight spacing scale from `frontend/src/index.css`: `4, 8, 12, 16, 24, 32, 48, 64px`.

## Interaction

- Teal is for active states, primary actions, focus, and positive financial signal.
- Red is only for negative numbers, destructive actions, and errors.
- Links are underlined by default and invert to teal background on hover.
- Buttons are flat, bordered, and compact; primary buttons use solid teal.

## Copy

- Product name: `AutoFin`.
- Positioning: automated AI finance for Canadians.
- Tone: direct, private, local-first, finance-literate.
- Avoid mascot language and visual references from the old ClawFin identity.
