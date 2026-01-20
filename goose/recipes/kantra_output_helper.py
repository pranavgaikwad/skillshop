#!/usr/bin/env python3
"""
Kantra Output Helper
Helps parse and analyze Kantra migration analysis results from output.yaml
"""

import yaml
import sys
import argparse
from pathlib import Path
from collections import defaultdict


def load_kantra_output(output_file):
    """Load and parse the Kantra output.yaml file"""
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {output_file}: {e}")
        sys.exit(1)


def display_issues_summary(output_file):
    """Display summary of all issues with file counts"""
    data = load_kantra_output(output_file)

    print("=" * 80)
    print("KANTRA MIGRATION ISSUES SUMMARY")
    print("=" * 80)

    total_issues = 0
    total_files_affected = set()

    for ruleset in data:
        if 'violations' not in ruleset:
            continue

        ruleset_name = ruleset.get('name', 'Unknown')
        print(f"\n📋 Ruleset: {ruleset_name}")
        print("-" * 60)

        for rule_id, violation in ruleset['violations'].items():
            description = violation.get('description', 'No description')
            category = violation.get('category', 'unknown')
            incidents = violation.get('incidents', [])

            # Count unique files for this issue
            files_with_issue = set()
            for incident in incidents:
                uri = incident.get('uri', '')
                if uri.startswith('file://'):
                    file_path = uri[7:]  # Remove 'file://' prefix
                    files_with_issue.add(file_path)
                    total_files_affected.add(file_path)

            total_issues += 1

            print(f"🔍 Issue: {rule_id}")
            print(f"   Description: {description}")
            print(f"   Category: {category}")
            print(f"   Files affected: {len(files_with_issue)}")

            # Show effort if available
            if 'effort' in violation:
                print(f"   Effort: {violation['effort']}")

            print()

    print("=" * 80)
    print(f"TOTAL: {total_issues} issues found across {len(total_files_affected)} files")
    print("=" * 80)


def display_file_issues(output_file, target_file):
    """Display all issues found in a specific file"""
    data = load_kantra_output(output_file)

    print("=" * 80)
    print(f"ISSUES IN FILE: {target_file}")
    print("=" * 80)

    issues_found = []

    for ruleset in data:
        if 'violations' not in ruleset:
            continue

        ruleset_name = ruleset.get('name', 'Unknown')

        for rule_id, violation in ruleset['violations'].items():
            description = violation.get('description', 'No description')
            category = violation.get('category', 'unknown')
            incidents = violation.get('incidents', [])

            # Find incidents for the target file
            file_incidents = []
            for incident in incidents:
                uri = incident.get('uri', '')
                if uri.startswith('file://'):
                    file_path = uri[7:]  # Remove 'file://' prefix
                    if file_path == target_file or file_path.endswith(target_file):
                        file_incidents.append(incident)

            if file_incidents:
                issues_found.append({
                    'ruleset': ruleset_name,
                    'rule_id': rule_id,
                    'description': description,
                    'category': category,
                    'incidents': file_incidents,
                    'effort': violation.get('effort')
                })

    if not issues_found:
        print(f"❌ No issues found for file: {target_file}")
        print("\n💡 Tip: Try using just the filename (e.g., 'pom.xml') if full path doesn't match")
        return

    for i, issue in enumerate(issues_found, 1):
        print(f"\n📌 Issue {i}: {issue['rule_id']}")
        print(f"   Ruleset: {issue['ruleset']}")
        print(f"   Category: {issue['category']}")
        if issue['effort']:
            print(f"   Effort: {issue['effort']}")
        print(f"   Description: {issue['description']}")
        print()

        for j, incident in enumerate(issue['incidents'], 1):
            print(f"   📍 Occurrence {j}:")
            print(f"      Line: {incident.get('lineNumber', 'N/A')}")
            print(f"      Message: {incident.get('message', 'No message')}")

            # Show code snippet if available (first few lines)
            code_snip = incident.get('codeSnip', '')
            if code_snip:
                lines = code_snip.split('\n')[:5]  # Show first 5 lines
                print(f"      Code Preview:")
                for line in lines:
                    if line.strip():
                        print(f"        {line}")
                if len(code_snip.split('\n')) > 5:
                    print(f"        ... (truncated)")
            print()

    print("=" * 80)
    print(f"TOTAL: {len(issues_found)} issues found in {target_file}")
    print("=" * 80)


def list_affected_files(output_file):
    """List all files that have issues"""
    data = load_kantra_output(output_file)

    files_with_issues = defaultdict(int)

    for ruleset in data:
        if 'violations' not in ruleset:
            continue

        for rule_id, violation in ruleset['violations'].items():
            incidents = violation.get('incidents', [])

            for incident in incidents:
                uri = incident.get('uri', '')
                if uri.startswith('file://'):
                    file_path = uri[7:]  # Remove 'file://' prefix
                    files_with_issues[file_path] += 1

    print("=" * 80)
    print("FILES WITH MIGRATION ISSUES")
    print("=" * 80)

    for file_path, issue_count in sorted(files_with_issues.items()):
        print(f"{issue_count:>3} issues | {file_path}")

    print("=" * 80)
    print(f"TOTAL: {len(files_with_issues)} files have migration issues")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Kantra migration output.yaml file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python kantra_output_helper.py summary /path/to/kantra-output/output.yaml
  python kantra_output_helper.py file /path/to/kantra-output/output.yaml /path/to/pom.xml
  python kantra_output_helper.py file /path/to/kantra-output/output.yaml pom.xml
  python kantra_output_helper.py files /path/to/kantra-output/output.yaml

Note: Kantra creates a directory (e.g., kantra-output/) containing output.yaml file.
      Provide the full path to the output.yaml file within that directory.
        """
    )

    parser.add_argument('command', choices=['summary', 'file', 'files'],
                       help='Command to run: summary (all issues), file (issues in specific file), files (list affected files)')
    parser.add_argument('output_file', help='Path to Kantra output.yaml file')
    parser.add_argument('target_file', nargs='?',
                       help='Target file path (required for "file" command)')

    args = parser.parse_args()

    # Validate arguments
    if args.command == 'file' and not args.target_file:
        parser.error("Target file is required for 'file' command")

    if not Path(args.output_file).exists():
        print(f"Error: Output file '{args.output_file}' not found")
        sys.exit(1)

    # Execute command
    if args.command == 'summary':
        display_issues_summary(args.output_file)
    elif args.command == 'file':
        display_file_issues(args.output_file, args.target_file)
    elif args.command == 'files':
        list_affected_files(args.output_file)


if __name__ == "__main__":
    main()