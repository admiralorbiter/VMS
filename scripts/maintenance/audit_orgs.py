import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from models.organization import Organization


def run_audit():
    app = create_app()
    with app.app_context():
        # Using pure SQL to find duplicate names based on leading substrings
        # (e.g. "Turner Construction" and "Turner Construction Company")
        # Load all organizations
        orgs = Organization.query.all()

        # Build a dictionary to map stripped names to clusters
        clusters = {}
        for org in orgs:
            if not org.name:
                continue

            # Normalize: lower, strip whitespace, remove common suffixes
            name = org.name.lower().strip()
            import re

            name = re.sub(r"[,.]", "", name)  # remove punctuation
            name = re.sub(
                r"\b(inc|llc|company|corp|co|ltd|incorporated|corporation)\b", "", name
            )
            key = name.strip()

            if not key:
                continue

            if key not in clusters:
                clusters[key] = []
            clusters[key].append(org)

        duplicates = {k: v for k, v in clusters.items() if len(v) > 1}

        with open("audit_utf8.txt", "w", encoding="utf-8") as f:
            f.write(f"⚠️ Found {len(duplicates)} exact true-duplicate clusters:\n\n")
            for key, group in duplicates.items():
                f.write(f"Cluster: '{key}'\n")
                for org in group:
                    f.write(f"  ID: {org.id:<4} | Name: {org.name}\n")
                f.write("-" * 50 + "\n")


if __name__ == "__main__":
    run_audit()
