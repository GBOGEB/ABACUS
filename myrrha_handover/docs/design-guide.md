# MYRRHA Handover — HTML Slide Design Guide

## 1. Slide structure
Every slide is one `<section class="slide">` with:
- `<h1>` title (project blue `#0b3d91`)
- optional `.sub` subtitle (muted)
- `.content` body — markdown-rendered
- optional `.caption` (italic, muted)
- optional `.notes` (dashed top border, accent-highlighted TODO/REVIEW/ACTION)

## 2. Color scheme (from `master/config.yaml`)
| Token   | Hex       | Use                       |
|---------|-----------|---------------------------|
| primary | `#0b3d91` | titles, labels, links     |
| accent  | `#ff8a00` | review markers, CTAs      |
| bg      | `#f7f8fa` | page background           |
| fg      | `#1b1f24` | body text                 |
| rule    | `#d8dde3` | borders, dividers         |

## 3. Typography
- **Body / headings:** Aptos (fallbacks: Segoe UI, system-ui)
- **Code / ASCII / mono:** Consolas (fallbacks: JetBrains Mono, Courier New)
- ASCII trees, code blocks, table IDs, and operating-point values are **always** in mono.

## 4. Layout templates
| Layout         | Grid                                | When to use                       |
|----------------|-------------------------------------|-----------------------------------|
| `text-only`    | `1fr`                               | hierarchy, exec summary, roadmap  |
| `text-table`   | `1.618fr 1fr` (golden)              | argument + supporting table       |
| `text-graph`   | `1.618fr 1fr`                       | argument + chart                  |
| `4-quadrants`  | `1fr 1fr / 1fr 1fr`                 | comparative analysis              |

## 5. Smart labeling system
| Prefix | Domain               | Examples                  |
|--------|----------------------|---------------------------|
| `B`    | Design arguments     | B1 baseline, B2 ALaT, B3 LKT |
| `G`    | Graphs               | G1, G2, G3                |
| `T`    | Tables               | T1, T2                    |
| `E`    | Equations            | E1, E2                    |
| `F`    | Figures (incl. ASCII) | F1                       |

Cross-reference syntax in markdown: ``See **G1** in graphs.html``.
The renderer auto-numbers within each artifact page; IDs declared in `master/slides.md`
front-matter (`caption: F1 — …`) are preserved verbatim.

## 6. Outline numbering
Slides are ordered by `slides_order` in `master/config.yaml`. Each slide carries
a sequential pill `n/N` plus its layout name. Argument labels (B1..B5) link
directly back to `truth.html`.
