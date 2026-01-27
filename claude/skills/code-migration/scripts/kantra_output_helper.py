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
            data = yaml.safe_load(f)

            if data is None:
                print(f"Error: {output_file} is empty or contains only whitespace")
                sys.exit(1)

            if not isinstance(data, list):
                print(f"Error: {output_file} does not contain expected list format")
                sys.exit(1)

            return data

    except FileNotFoundError:
        print(f"Error: File '{output_file}' not found")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied accessing '{output_file}'")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML format in '{output_file}': {e}")
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"Error: File '{output_file}' contains invalid UTF-8 characters")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected error loading '{output_file}': {e}")
        sys.exit(1)


def display_issues_summary(output_file):
    """Display summary of all issues with file counts"""
    try:
        data = load_kantra_output(output_file)

        print("=" * 80)
        print("KANTRA MIGRATION ISSUES SUMMARY")
        print("=" * 80)
        print(f"{'Rule ID':<40} {'Files':<8} Description")
        print("-" * 80)

        total_issues = 0
        total_files_affected = set()

        for ruleset in data:
            if not isinstance(ruleset, dict) or 'violations' not in ruleset:
                continue

            violations = ruleset.get('violations')
            if not isinstance(violations, dict) or not violations:
                continue

            for rule_id, violation in violations.items():
                if not isinstance(violation, dict):
                    continue

                description = violation.get('description', 'No description')
                incidents = violation.get('incidents', [])

                if not isinstance(incidents, list):
                    continue

                files_with_issue = set()
                for incident in incidents:
                    if not isinstance(incident, dict):
                        continue
                    uri = incident.get('uri', '')
                    if isinstance(uri, str) and uri.startswith('file://'):
                        file_path = uri[7:]
                        if file_path:
                            files_with_issue.add(file_path)
                            total_files_affected.add(file_path)

                total_issues += 1
                print(f"{rule_id:<40} {len(files_with_issue):<8} {description}")

        print("=" * 80)
        print(f"TOTAL: {total_issues} issues across {len(total_files_affected)} files")
        print("=" * 80)

        if total_issues == 0:
            print("No migration issues found in the analysis results.")

    except Exception as e:
        print(f"Error: Failed to display issues summary: {e}")
        sys.exit(1)


def display_file_issues(output_file, target_file):
    """Display all issues found in a specific file"""
    try:
        data = load_kantra_output(output_file)

        print("=" * 80)
        print(f"ISSUES IN FILE: {target_file}")
        print("=" * 80)

        if not target_file or not target_file.strip():
            print("Error: Target file name cannot be empty")
            return

        issues_found = []

        for i, ruleset in enumerate(data):
            if not isinstance(ruleset, dict):
                continue

            if 'violations' not in ruleset:
                continue

            ruleset_name = ruleset.get('name', 'Unknown')
            violations = ruleset.get('violations')

            if not isinstance(violations, dict):
                continue

            for rule_id, violation in violations.items():
                try:
                    if not isinstance(violation, dict):
                        continue

                    description = violation.get('description', 'No description')
                    category = violation.get('category', 'unknown')
                    incidents = violation.get('incidents', [])

                    if not isinstance(incidents, list):
                        continue

                    # Find incidents for the target file
                    file_incidents = []
                    for incident in incidents:
                        try:
                            if not isinstance(incident, dict):
                                continue

                            uri = incident.get('uri', '')
                            if isinstance(uri, str) and uri.startswith('file://'):
                                file_path = uri[7:]  # Remove 'file://' prefix
                                if file_path == target_file or file_path.endswith(target_file):
                                    file_incidents.append(incident)

                        except Exception as e:
                            print(f"Warning: Error processing incident in '{rule_id}': {e}")
                            continue

                    if file_incidents:
                        issues_found.append({
                            'ruleset': ruleset_name,
                            'rule_id': rule_id,
                            'description': description,
                            'category': category,
                            'incidents': file_incidents,
                            'effort': violation.get('effort')
                        })

                except Exception as e:
                    print(f"Warning: Error processing rule '{rule_id}': {e}")
                    continue

        if not issues_found:
            print(f"❌ No issues found for file: {target_file}")
            print("\n💡 Tip: Try using just the filename (e.g., 'pom.xml') if full path doesn't match")
            return

        for i, issue in enumerate(issues_found, 1):
            try:
                print(f"\n📌 Issue {i}: {issue['rule_id']}")
                print(f"   Ruleset: {issue['ruleset']}")
                print(f"   Category: {issue['category']}")
                if issue.get('effort') is not None:
                    print(f"   Effort: {issue['effort']}")
                print(f"   Description: {issue['description']}")
                print()

                incidents = issue.get('incidents', [])
                for j, incident in enumerate(incidents, 1):
                    try:
                        if not isinstance(incident, dict):
                            print(f"   📍 Occurrence {j}: Invalid incident data")
                            continue

                        print(f"   📍 Occurrence {j}:")
                        line_number = incident.get('lineNumber', 'N/A')
                        print(f"      Line: {line_number}")

                        message = incident.get('message', 'No message')
                        print(f"      Message: {message}")

                        # Show code snippet if available (first few lines)
                        code_snip = incident.get('codeSnip', '')
                        if isinstance(code_snip, str) and code_snip.strip():
                            try:
                                lines = code_snip.split('\n')[:5]  # Show first 5 lines
                                print(f"      Code Preview:")
                                for line in lines:
                                    if line.strip():
                                        print(f"        {line}")
                                if len(code_snip.split('\n')) > 5:
                                    print(f"        ... (truncated)")
                            except Exception as e:
                                print(f"      Code Preview: Error displaying code snippet: {e}")
                        print()

                    except Exception as e:
                        print(f"   📍 Occurrence {j}: Error displaying incident: {e}")
                        print()

            except Exception as e:
                print(f"Error displaying issue {i}: {e}")
                continue

        print("=" * 80)
        print(f"TOTAL: {len(issues_found)} issues found in {target_file}")
        print("=" * 80)

    except Exception as e:
        print(f"Error: Failed to display file issues: {e}")
        sys.exit(1)


def list_affected_files(output_file):
    """List all files that have issues"""
    try:
        data = load_kantra_output(output_file)

        files_with_issues = defaultdict(int)

        for i, ruleset in enumerate(data):
            if not isinstance(ruleset, dict):
                continue

            if 'violations' not in ruleset:
                continue

            violations = ruleset.get('violations')
            if not isinstance(violations, dict):
                continue

            for rule_id, violation in violations.items():
                try:
                    if not isinstance(violation, dict):
                        continue

                    incidents = violation.get('incidents', [])
                    if not isinstance(incidents, list):
                        continue

                    for incident in incidents:
                        try:
                            if not isinstance(incident, dict):
                                continue

                            uri = incident.get('uri', '')
                            if isinstance(uri, str) and uri.startswith('file://'):
                                file_path = uri[7:]  # Remove 'file://' prefix
                                if file_path:  # Only count non-empty paths
                                    files_with_issues[file_path] += 1

                        except Exception as e:
                            print(f"Warning: Error processing incident in '{rule_id}': {e}")
                            continue

                except Exception as e:
                    print(f"Warning: Error processing rule '{rule_id}': {e}")
                    continue

        print("=" * 80)
        print("FILES WITH MIGRATION ISSUES")
        print("=" * 80)

        if not files_with_issues:
            print("No files with migration issues found.")
        else:
            try:
                for file_path, issue_count in sorted(files_with_issues.items()):
                    print(f"{issue_count:>3} issues | {file_path}")
            except Exception as e:
                print(f"Warning: Error sorting files: {e}")
                # Fallback: display unsorted
                for file_path, issue_count in files_with_issues.items():
                    print(f"{issue_count:>3} issues | {file_path}")

        print("=" * 80)
        print(f"TOTAL: {len(files_with_issues)} files have migration issues")
        print("=" * 80)

    except Exception as e:
        print(f"Error: Failed to list affected files: {e}")
        sys.exit(1)


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
