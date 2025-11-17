#!/bin/bash


<file> ```bash # filepath: /scripts/auto_cleanup.sh #!/bin/bash echo "Removing yellow marker comments from Markdown, YAML, and JSON files..." find . \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" \) -type f | while read file; do # Create a temporary file tmp_file=$(mktemp)
grep -v "YELLOW: Check for unmatched or missing brackets" "$file" | grep -v "YELLOW: End of YAML file, check for unmatched or missing brackets above" > "$tmp_file"
mv "$tmp_file" "$file"

echo "Cleaned: $file" done echo "Cleanup complete."

# Define the directory to clean up and the retention period
TARGET_DIR="/var/log/myapp"
RETENTION_DAYS=7

# Ensure the target directory exists
if [ -d "$TARGET_DIR" ]; then
  # Find and delete files older than the retention period
  find "$TARGET_DIR" -type f -mtime +$RETENTION_DAYS -exec rm -f {} \;

  # Log the cleanup activity
  echo "$(date): Cleanup completed for $TARGET_DIR. Files older than $RETENTION_DAYS days were removed." >> /var/log/cleanup.log
else
  echo "$(date): ERROR - Target directory $TARGET_DIR does not exist." >> /var/log/cleanup.log
fi