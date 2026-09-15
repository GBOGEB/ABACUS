#!/usr/bin/env python3
"""Independent DOW challenge of MissionControl temporal H2 surveillance.

Consumes an exported MissionControl policy receipt. It does not import the origin
implementation and grants no CONTROL or engineering authority.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def recompute(receipt, task_class):
    frontier = receipt['scheduled_control_frontier']
    event = frontier['eligibility_event']
    path = frontier['eligibility_workflow_path']
    windows = [
        w for w in receipt['windows']
        if w.get('event') == event
        and w.get('workflow_path') == path
        and w.get('source_kind') != 'SYNTHETIC_TEST'
    ]
    windows.sort(key=lambda w: (w['created_at'], int(w['window_id'])))
    rows = [w['task_classes'][task_class] for w in windows]
    directional = [r['direction'] for r in rows if r['direction'] != 'INDETERMINATE']
    flips = sum(a != b for a, b in zip(directional, directional[1:]))
    pairs = sum(int(r['observed_pairs']) for r in rows)
    single = sum(float(r['single_normalized_strength']) * int(r['observed_pairs']) for r in rows) / pairs if pairs else 0.5
    counts = Counter(directional)
    dominant = counts.most_common(1)[0][0] if counts else 'INDETERMINATE'
    return {
        'task_class': task_class,
        'genuine_scheduled_windows': len(windows),
        'directional_windows': len(directional),
        'direction_flip_count': flips,
        'indeterminate_window_fraction': ((len(rows) - len(directional)) / len(rows)) if rows else None,
        'pooled_winner_strength': max(single, 1.0 - single),
        'dominant_direction': dominant,
        'synthetic_windows_counted': 0,
        'competency_promotions': 0,
        'authority_transfer': False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    receipt = json.loads(Path(args.receipt).read_text())
    origin = receipt.get('temporal_surveillance', {})
    result = {'schema': 'abacus.dow.temporal_h2_challenge.v1', 'origin_schema': origin.get('schema'), 'classes': {}}
    for task_class in receipt.get('policies', {}):
        result['classes'][task_class] = recompute(receipt, task_class)
    result['disposition'] = 'CHALLENGE_RECOMPUTED'
    result['engineering_credit_delta'] = 0
    result['control_authority'] = False
    result['authority_transfer'] = False
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
