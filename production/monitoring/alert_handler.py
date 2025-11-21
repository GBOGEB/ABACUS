#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime

def trigger_alert(rule_name, severity, message):
    alert = {
        'timestamp': datetime.now().isoformat(),
        'rule': rule_name,
        'severity': severity,
        'message': message
    }
    
    # Log to file
    log_file = Path('production/logs/alerts.log')
    with open(log_file, 'a') as f:
        f.write(f'{json.dumps(alert)}\n')
    
    # Save to history
    history_file = Path('production/monitoring/alerts_history.json')
    history = []
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
    
    history.append(alert)
    
    with open(history_file, 'w') as f:
        json.dump(history[-100:], f, indent=2)  # Keep last 100 alerts

if __name__ == '__main__':
    trigger_alert('Test Alert', 'info', 'Alert system initialized')
