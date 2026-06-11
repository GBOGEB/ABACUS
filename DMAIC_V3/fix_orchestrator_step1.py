import sys

# Read the clean file
with open('full_pipeline_orchestrator_clean.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 1 and 2 (swap them)
if lines[0].startswith('from typing'):
    lines[0], lines[1] = lines[1], lines[0]

# Add background detector import after planning_matrix_tracker
for i, line in enumerate(lines):
    if 'from DMAIC_V3.core.planning_matrix_tracker import' in line:
        lines.insert(i+1, 'from DMAIC_V3.convergence.background_change_detector import BackgroundChangeDetector\n')
        break

# Add feature to docstring
for i, line in enumerate(lines):
    if '- Everything tracked even if incomplete' in line:
        lines.insert(i+1, '- Background change detection (non-blocking)\n')
        break

# Write the fixed file
with open('full_pipeline_orchestrator.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Step 1: Fixed header and added import')
