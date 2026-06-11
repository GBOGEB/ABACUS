#!/usr/bin/env python3
import json
import time
from pathlib import Path
from datetime import datetime

def check_metrics():
    metrics_file = Path('production/monitoring/current_metrics.json')
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
        return metrics
    return {}

def log_status(message):
    log_file = Path('production/logs/monitoring.log')
    with open(log_file, 'a') as f:
        f.write(f'{datetime.now().isoformat()} - {message}\n')

while True:
    metrics = check_metrics()
    log_status(f'Monitoring check: {json.dumps(metrics)}')
    time.sleep(300)  # Check every 5 minutes
