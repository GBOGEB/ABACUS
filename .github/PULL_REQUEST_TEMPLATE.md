## Description

<!-- Briefly describe the changes in this PR -->

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature causing existing functionality to change)
- [ ] 📝 Documentation update
- [ ] 🏗️ Infrastructure / CI change
- [ ] 🎨 Theme / styling update
- [ ] 📊 New asset in Input_Master/

## Governance Checklist

### Rendering Rules (RENDER_RULES.md)
- [ ] No text overflow in any rendered output
- [ ] WCAG AA contrast ratios met (4.5:1 minimum for text)
- [ ] Heading hierarchy is strictly sequential (H1 → H2 → H3)
- [ ] No orphan bullets (single-item lists)
- [ ] All figures have fig-id, caption, and alt text

### Lineage Tracking
- [ ] All slides have valid `slide_id` format: `{deck}-{section}-{sequence}`
- [ ] Lineage manifest is up to date (`_data/lineage_manifest.json`)
- [ ] `.mock` sidecar files committed for any new Input_Master/ assets
- [ ] No manual edits to generated outputs

### Semantic Cards & Notes
- [ ] All presentation slides have speaker notes (≥50 chars)
- [ ] Semantic cards include: `slide_id`, `purpose`, `audience`
- [ ] Stakeholder routing tags applied: `[KEB]`, `[DOW]`, or `[ALL]`

### Code Quality
- [ ] All engines pass `RENDER_LINTER.py` with zero errors
- [ ] `WCAG_CONTRAST_CHECKER.py` passes with zero AA violations
- [ ] `SLIDE_ID_ENFORCER.py` passes with zero missing IDs
- [ ] Unit tests pass (`python -m pytest tests/ -v`)

## Stakeholder Routing

<!-- Which teams/outputs does this affect? -->
- [ ] `[KEB]` — Executive summaries / high-level views
- [ ] `[DOW]` — Technical specifications / implementation
- [ ] `[ALL]` — Both teams

## Testing

<!-- Describe how you tested these changes -->

```bash
# Commands run
python engines/RENDER_LINTER.py docs/
python engines/WCAG_CONTRAST_CHECKER.py --theme engines/SEMANTIC_THEME.yaml
python engines/SLIDE_ID_ENFORCER.py docs/
python -m pytest tests/ -v
```

## Related Issues

<!-- Link any related issues: Closes #123, Relates to #456 -->

## Screenshots

<!-- If applicable, add screenshots of rendered output -->
