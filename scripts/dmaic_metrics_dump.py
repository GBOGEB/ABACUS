import os
import csv

def dump_dmaic_metrics(metrics, output_dir):
    """
    Dumps DMAIC metrics to a CSV file.

    Args:
        metrics (list
        of dict): A list of dictionaries containing DMAIC metrics.
        output_dir (str): The directory where the CSV file will be saved.

        Returns:
        None
        """

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Define the output file path
        output_file = os.path.join(output_dir, "dmaic_metrics.csv")

        # Write metrics to the CSV file
        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = metrics[0].keys() if metrics else []
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(metrics)