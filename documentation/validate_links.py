#!/usr/bin/env python3
"""
Documentation Link Validator

Validates internal links in markdown documentation files.
Checks:
1. Inter-document links (e.g., [text](requirements#fr-xxx))
2. Anchor links within files (e.g., #section-name)
3. File references (e.g., [text](user_guide/index))

Usage:
    python validate_links.py [--verbose]
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuration
CONTENT_DIR = Path(__file__).parent / "content"
VALID_EXTENSIONS = {".md"}

# Regex patterns
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
ANCHOR_ID_PATTERN = re.compile(r'<a\s+id="([^"]+)"', re.IGNORECASE)
HEADER_PATTERN = re.compile(r"^#+\s+(.+)$", re.MULTILINE)


def slugify(text: str) -> str:
    """Convert header text to anchor slug (GitHub-style)."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Replace arrows with hyphens (common in documentation)
    text = text.replace("→", "-").replace("←", "-").replace("↔", "-")
    # Replace & with empty (GitHub removes it)
    text = text.replace("&", "")
    # Remove special characters except hyphens, spaces, and underscores
    text = re.sub(r"[^\w\s-]", "", text.lower())
    # Replace spaces with hyphens
    text = re.sub(r"\s+", "-", text.strip())
    # Collapse multiple hyphens to double-hyphen max
    text = re.sub(r"-{3,}", "--", text)
    return text


def extract_anchors(content: str) -> set:
    """Extract all anchor IDs from markdown content."""
    anchors = set()

    # Explicit anchor IDs: <a id="xxx">
    for match in ANCHOR_ID_PATTERN.finditer(content):
        anchors.add(match.group(1).lower())

    # Header-based anchors
    for match in HEADER_PATTERN.finditer(content):
        header_text = match.group(1)
        anchors.add(slugify(header_text))

    return anchors


def extract_links(content: str) -> list:
    """Extract all markdown links from content."""
    links = []
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        link_text = match.group(1)
        link_target = match.group(2)
        links.append((link_text, link_target, match.start()))
    return links


def parse_link(link: str) -> tuple:
    """Parse a link into (file_path, anchor) components."""
    # Skip external links
    if link.startswith(("http://", "https://", "mailto:", "tel:")):
        return None, None

    # Skip image references
    if link.startswith(("images/", "../images/")):
        return None, None

    # Parse file and anchor
    if "#" in link:
        file_part, anchor = link.split("#", 1)
        return file_part or None, anchor.lower()
    else:
        return link, None


def resolve_file_path(source_file: Path, target: str) -> Path:
    """Resolve a relative file path to absolute."""
    if not target:
        return source_file

    # Handle relative paths
    if target.startswith("../"):
        base = source_file.parent
        while target.startswith("../"):
            base = base.parent
            target = target[3:]
        return base / f"{target}.md"
    elif target.startswith("./"):
        return source_file.parent / f"{target[2:]}.md"
    else:
        # Assume relative to content root or current directory
        # Try current directory first
        local_path = source_file.parent / f"{target}.md"
        if local_path.exists():
            return local_path
        # Try content root
        return CONTENT_DIR / f"{target}.md"


def validate_documentation(verbose: bool = False) -> tuple:
    """
    Validate all links in documentation.
    Returns (errors, warnings) as lists of strings.
    """
    errors = []
    warnings = []

    # First pass: build anchor index
    file_anchors = {}  # file_path -> set of anchors

    for md_file in CONTENT_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        anchors = extract_anchors(content)
        file_anchors[md_file] = anchors

        if verbose:
            print(f"📄 {md_file.relative_to(CONTENT_DIR)}: {len(anchors)} anchors")

    # Second pass: validate links
    link_count = 0
    broken_count = 0

    for md_file in CONTENT_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        links = extract_links(content)
        relative_path = md_file.relative_to(CONTENT_DIR)

        for link_text, link_target, position in links:
            file_part, anchor = parse_link(link_target)

            # Skip external/image links
            if file_part is None and anchor is None:
                continue

            link_count += 1

            # Resolve target file
            if file_part:
                target_file = resolve_file_path(md_file, file_part)
            else:
                target_file = md_file

            # Check file exists
            if file_part and not target_file.exists():
                errors.append(
                    f"❌ {relative_path}: Broken file link [{link_text}]({link_target})"
                )
                broken_count += 1
                continue

            # Check anchor exists
            if anchor:
                target_anchors = file_anchors.get(target_file, set())
                if anchor not in target_anchors:
                    # Try common variations
                    variations = [
                        anchor.replace("-", "_"),
                        anchor.replace("_", "-"),
                        anchor.lower(),
                    ]
                    if not any(v in target_anchors for v in variations):
                        errors.append(
                            f"❌ {relative_path}: Broken anchor [{link_text}]({link_target}) "
                            f"- anchor '{anchor}' not found in {target_file.name}"
                        )
                        broken_count += 1

    return errors, warnings, link_count, broken_count


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("=" * 60)
    print("📚 VMS Documentation Link Validator")
    print("=" * 60)
    print(f"\nScanning: {CONTENT_DIR}\n")

    if not CONTENT_DIR.exists():
        print(f"❌ Content directory not found: {CONTENT_DIR}")
        sys.exit(1)

    errors, warnings, link_count, broken_count = validate_documentation(verbose)

    print("\n" + "=" * 60)
    print("📊 Results")
    print("=" * 60)
    print(f"Total links checked: {link_count}")
    print(f"Broken links: {broken_count}")

    if errors:
        print(f"\n🔴 {len(errors)} Error(s):\n")
        for error in errors:
            print(f"  {error}")

    if warnings:
        print(f"\n🟡 {len(warnings)} Warning(s):\n")
        for warning in warnings:
            print(f"  {warning}")

    if not errors and not warnings:
        print("\n✅ All links valid!")

    print()

    # Exit with error code if broken links found
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
