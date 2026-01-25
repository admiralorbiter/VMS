import json
import os
import re

DOCS_DIR = os.path.abspath(os.path.join(os.getcwd(), "documentation/content"))
NAV_JS_PATH = os.path.abspath(os.path.join(os.getcwd(), "documentation/js/nav.js"))


def parse_nav_manifest(nav_js_path):
    """Extracts the PAGE_MANIFEST from nav.js."""
    try:
        with open(nav_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex to find the PAGE_MANIFEST object
        match = re.search(r"const PAGE_MANIFEST = ({[\s\S]*?});", content)
        if not match:
            print("Error: Could not find PAGE_MANIFEST in nav.js")
            return {}

        manifest_str = match.group(1)
        # Convert JS object syntax to valid JSON (add quotes to keys)
        # This is a bit hacky but avoids needing a full JS parser
        manifest_str = re.sub(
            r"^\s*'([\w-]+)':", r'"\1":', manifest_str, flags=re.MULTILINE
        )
        manifest_str = manifest_str.replace("'", '"')

        # Remove comments if any (simple approach)
        manifest_str = re.sub(r"//.*", "", manifest_str)

        try:
            return json.loads(manifest_str)
        except json.JSONDecodeError as e:
            print(f"Error parsing manifest JSON: {e}")
            # Fallback manual parsing
            manifest = {}
            for line in manifest_str.split("\n"):
                line = line.strip()
                match = re.match(r'"([\w-]+)":\s*"([\w/]+)"', line)
                if match:
                    manifest[match.group(1)] = match.group(2)
            return manifest

    except Exception as e:
        print(f"Error reading nav.js: {e}")
        return {}


def find_markdown_files(root_dir):
    md_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
    return md_files


def extract_links(md_file):
    """Finds all [text](link) and [text][ref] links in a markdown file."""
    links = []
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Inline links: [text](link)
    inline_matches = re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for m in inline_matches:
        links.append(
            {
                "text": m.group(1),
                "target": m.group(2),
                "line": content[: m.start()].count("\n") + 1,
            }
        )

    return links


def validate_links(links, manifest, current_file_path):
    issues = []
    valid_pages = set(manifest.values())
    valid_keys = set(manifest.keys())

    current_dir = os.path.dirname(current_file_path)

    for link in links:
        target = link["target"]

        # Skip external links, anchors only, and mailto
        if (
            target.startswith("http")
            or target.startswith("mailto:")
            or target.startswith("#")
        ):
            continue

        # Remove anchor part for validation
        target_path = target.split("#")[0]
        anchor = target.split("#")[1] if "#" in target else None

        if not target_path:
            # Just an anchor (handled above, but double check logic)
            continue

        # Check against manifest keys (the primary way links work in this system)
        # e.g. [Link](user_stories) -> maps to 'user_stories' key?
        # Actually nav.js handles:
        # 1. Page keys (from manifest)
        # 2. Relative paths (if not a key)

        # Is it a manifest key directly?
        # e.g., 'getting-started'
        if target_path in valid_keys:
            continue

        # Is it a relative file path that acts as a key?
        # Links often look like 'user_stories' or 'user_stories.md' or './user_stories'

        # Normalized target (remove extensions and ./ )
        clean_target = target_path.replace(".md", "").replace("./", "")

        # Check if it matches a manifest VALUE (file path)
        if clean_target in valid_pages:
            # It matches a file path directly (e.g. 'user_guide/in_person_events')
            continue

        # Check if it matches a manifest KEY (e.g. 'user_stories' -> 'user-stories' via regex magic in nav.js?)
        # nav.js logic: pageHash = pageName.replace(/_/g, '-')
        # So 'user_stories' becomes 'user-stories'
        derived_key = clean_target.replace("_", "-")
        if derived_key in valid_keys:
            continue

        # If we got here, it might be a broken link
        # Check if file exists on disk relative to current file
        rel_path = os.path.join(current_dir, target_path)
        if not target_path.endswith(".md") and not os.path.isdir(rel_path):
            rel_path += ".md"

        if os.path.exists(rel_path):
            # File exists, but is it in the manifest?
            # If not in manifest, it won't load in this SPA system
            # Calculate the path relative to content root
            try:
                rel_to_root = os.path.relpath(rel_path, DOCS_DIR).replace("\\", "/")
                rel_to_root_no_ext = rel_to_root.replace(".md", "")

                if rel_to_root_no_ext not in valid_pages:
                    issues.append(
                        f"Line {link['line']}: Link '{target}' points to file '{rel_to_root}' which is NOT in the navigation manifest. It may not load correctly."
                    )
                elif target_path.endswith(".md"):
                    issues.append(
                        f"Line {link['line']}: Link '{target}' uses .md extension. Consider removing it for consistency."
                    )
            except ValueError:
                pass  # path calculation error
        else:
            issues.append(
                f"Line {link['line']}: Broken link '{target}'. File not found."
            )

    return issues


def main():
    print(" Analyzing Documentation Links...")
    manifest = parse_nav_manifest(NAV_JS_PATH)
    print(f" Loaded {len(manifest)} pages from navigation manifest.")

    md_files = find_markdown_files(DOCS_DIR)
    print(f" Found {len(md_files)} markdown files.")

    total_issues = 0

    for md_file in md_files:
        links = extract_links(md_file)
        issues = validate_links(links, manifest, md_file)

        if issues:
            rel_path = os.path.relpath(md_file, DOCS_DIR)
            print(f"\nIssues in {rel_path}:")
            for issue in issues:
                print(f"  - {issue}")
                total_issues += 1

    if total_issues == 0:
        print("\n No link issues found! Good job.")
    else:
        print(f"\n Found {total_issues} potential link issues.")


if __name__ == "__main__":
    main()
