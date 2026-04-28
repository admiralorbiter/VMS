import os
import re

directory = "routes/salesforce"

# Regex to match the last_sync_watermark assignment
pattern = re.compile(
    r"last_sync_watermark=\(\s*datetime\.now\([^)]+\)\s*if sync_status\s*in\s*\([^)]+\)\s*else None\s*\),?",
    re.MULTILINE,
)

# Replace with:
replacement = """# TD-055: Always advance watermark; set wide buffer on failure for next delta
            last_sync_watermark=datetime.now(timezone.utc),
            recovery_buffer_hours=48 if sync_status == SyncStatus.FAILED.value else 1,"""

for filename in os.listdir(directory):
    if filename.endswith(".py"):
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        new_content, count = pattern.subn(replacement, content)
        if count > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {count} sites in {filename}")
