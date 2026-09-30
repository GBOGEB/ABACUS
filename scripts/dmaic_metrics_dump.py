"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Auto-generated version header
"""

import os
import csv

def dump_dmaic_metrics(metrics, output_dir):
    """
    Dumps DMAIC metrics to a CSV file.

    Args:
        metrics (list of dict): A list of dictionaries containing DMAIC metrics.
        output_dir (str): The directory where the CSV file will be saved.

    Returns:
        None
    """
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "dmaic_metrics.csv")

    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = metrics[0].keys() if metrics else []
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metrics)
