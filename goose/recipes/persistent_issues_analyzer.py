#!/usr/bin/env python3
"""
Persistent Issues Analyzer for Migration Workspace
Examines round directories to identify issues that persist across multiple analysis rounds.
Shows issue names, descriptions, and messages for persistent issues without analysis.
"""

import yaml
import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import re
from datetime import datetime


def parse_round_timestamp(round_dir_name):
    """Extract timestamp from round directory name"""
    match = re.search(r'round_(\d{8}_\d{6})', round_dir_name)
    if match:
        timestamp_str = match.group(1)
        try:
            return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        except ValueError:
            return None
    return None


def load_kantra_output(yaml_file):
    """Load and parse a Kantra output.yaml file"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

            if data is None:
                print(f"Warning: {yaml_file} is empty or contains only whitespace")
                return None

            if not isinstance(data, list):
                print(f"Warning: {yaml_file} does not contain expected list format")
                return None

            return data

    except FileNotFoundError:
        print(f"Warning: File '{yaml_file}' not found")
        return None
    except PermissionError:
        print(f"Warning: Permission denied accessing '{yaml_file}'")
        return None
    except yaml.YAMLError as e:
        print(f"Warning: Invalid YAML format in '{yaml_file}': {e}")
        return None
    except UnicodeDecodeError:
        print(f"Warning: File '{yaml_file}' contains invalid UTF-8 characters")
        return None
    except Exception as e:
        print(f"Warning: Unexpected error loading '{yaml_file}': {e}")
        return None


def extract_issues_from_round(round_dir):
    """Extract all issues from a round directory"""
    try:
        kantra_file = round_dir / "kantra_output.yaml"
        if not kantra_file.exists():
            return None, {}

        data = load_kantra_output(kantra_file)
        if not data:
            return None, {}

        issues = {}
        total_incidents = 0

        for i, ruleset in enumerate(data):
            try:
                if not isinstance(ruleset, dict):
                    print(f"Warning: Skipping invalid ruleset at index {i} in {round_dir}")
                    continue

                if 'violations' not in ruleset:
                    continue

                violations = ruleset.get('violations')
                if not isinstance(violations, dict):
                    print(f"Warning: Invalid violations format in ruleset {i} in {round_dir}")
                    continue

                ruleset_name = ruleset.get('name', 'Unknown')

                for rule_id, violation in violations.items():
                    try:
                        if not isinstance(violation, dict):
                            print(f"Warning: Invalid violation '{rule_id}' in {round_dir}")
                            continue

                        incidents = violation.get('incidents', [])
                        if not isinstance(incidents, list):
                            print(f"Warning: Invalid incidents format for '{rule_id}' in {round_dir}")
                            continue

                        files_affected = set()
                        incident_messages = set()

                        for incident in incidents:
                            try:
                                if not isinstance(incident, dict):
                                    continue

                                # Extract file paths
                                uri = incident.get('uri', '')
                                if isinstance(uri, str) and uri.startswith('file://'):
                                    file_path = uri[7:]  # Remove 'file://' prefix
                                    if file_path:  # Only add non-empty paths
                                        files_affected.add(file_path)

                                # Extract incident messages
                                message = incident.get('message', 'No message')
                                if isinstance(message, str) and message:
                                    incident_messages.add(message)

                            except Exception as e:
                                print(f"Warning: Error processing incident in '{rule_id}': {e}")
                                continue

                        issues[rule_id] = {
                            'description': violation.get('description', 'No description'),
                            'category': violation.get('category', 'unknown'),
                            'effort': violation.get('effort', 'unknown'),
                            'ruleset': ruleset_name,
                            'incident_count': len(incidents),
                            'files_affected': list(files_affected),
                            'incident_messages': list(incident_messages)
                        }
                        total_incidents += len(incidents)

                    except Exception as e:
                        print(f"Warning: Error processing rule '{rule_id}' in {round_dir}: {e}")
                        continue

            except Exception as e:
                print(f"Warning: Error processing ruleset {i} in {round_dir}: {e}")
                continue

        return total_incidents, issues

    except Exception as e:
        print(f"Warning: Error extracting issues from {round_dir}: {e}")
        return None, {}


def find_workspace_rounds(workspace_dir):
    """Find all round directories in the workspace"""
    try:
        workspace_path = Path(workspace_dir)
        if not workspace_path.exists():
            print(f"Warning: Workspace directory '{workspace_dir}' does not exist")
            return []

        if not workspace_path.is_dir():
            print(f"Warning: '{workspace_dir}' is not a directory")
            return []

        rounds = []

        try:
            for item in workspace_path.iterdir():
                try:
                    if item.is_dir() and item.name.startswith('round_'):
                        timestamp = parse_round_timestamp(item.name)
                        if timestamp:
                            rounds.append({
                                'path': item,
                                'name': item.name,
                                'timestamp': timestamp
                            })
                        else:
                            print(f"Warning: Could not parse timestamp from directory '{item.name}'")

                except PermissionError:
                    print(f"Warning: Permission denied accessing '{item}'")
                    continue
                except Exception as e:
                    print(f"Warning: Error processing directory '{item}': {e}")
                    continue

        except PermissionError:
            print(f"Error: Permission denied accessing workspace directory '{workspace_dir}'")
            return []
        except Exception as e:
            print(f"Warning: Error listing workspace directory '{workspace_dir}': {e}")
            return []

        # Sort by timestamp
        try:
            rounds.sort(key=lambda x: x['timestamp'])
        except Exception as e:
            print(f"Warning: Error sorting rounds by timestamp: {e}")
            # Return unsorted if sorting fails

        return rounds

    except Exception as e:
        print(f"Error: Failed to find workspace rounds in '{workspace_dir}': {e}")
        return []


def analyze_persistent_issues(workspace_dir, min_persistence=3):
    """Analyze issues that persist across multiple rounds"""
    try:
        rounds = find_workspace_rounds(workspace_dir)

        if len(rounds) < min_persistence:
            print(f"❌ Need at least {min_persistence} rounds to analyze persistence.")
            print(f"Found {len(rounds)} rounds in workspace.")
            return

        print("=" * 80)
        print("PERSISTENT ISSUES ANALYSIS")
        print("=" * 80)
        print(f"Workspace: {workspace_dir}")
        print(f"Rounds analyzed: {len(rounds)}")
        print(f"Persistence threshold: {min_persistence}+ rounds")
        print()

        # Track issues across rounds
        issue_history = defaultdict(list)  # rule_id -> [round_info, ...]
        round_summaries = []

        for round_info in rounds:
            try:
                round_dir = round_info.get('path')
                round_name = round_info.get('name', 'Unknown')
                timestamp = round_info.get('timestamp')

                if not round_dir:
                    print(f"Warning: Invalid round info for {round_name}")
                    continue

                total_incidents, issues = extract_issues_from_round(round_dir)

                if total_incidents is None:
                    print(f"⚠️  Skipping {round_name} - no valid Kantra output found")
                    continue

                round_summary = {
                    'name': round_name,
                    'timestamp': timestamp,
                    'total_incidents': total_incidents,
                    'unique_issues': len(issues) if issues else 0,
                    'issues': issues
                }
                round_summaries.append(round_summary)

                # Track each issue
                if issues:
                    for rule_id, issue_data in issues.items():
                        try:
                            if not isinstance(issue_data, dict):
                                print(f"Warning: Invalid issue data for '{rule_id}' in {round_name}")
                                continue

                            incident_count = issue_data.get('incident_count', 0)
                            files_affected = issue_data.get('files_affected', [])

                            issue_history[rule_id].append({
                                'round': round_name,
                                'timestamp': timestamp,
                                'incident_count': incident_count,
                                'files_affected': files_affected if isinstance(files_affected, list) else [],
                                'issue_data': issue_data
                            })

                        except Exception as e:
                            print(f"Warning: Error processing issue '{rule_id}' in {round_name}: {e}")
                            continue

            except Exception as e:
                print(f"Warning: Error processing round {round_info}: {e}")
                continue

        print("📊 ROUND SUMMARY:")
        print("-" * 40)
        if round_summaries:
            for summary in round_summaries:
                try:
                    name = summary.get('name', 'Unknown')
                    unique_issues = summary.get('unique_issues', 0)
                    total_incidents = summary.get('total_incidents', 0)
                    print(f"{name}: {unique_issues} issues, {total_incidents} incidents")
                except Exception as e:
                    print(f"Warning: Error displaying summary for round: {e}")
                    continue
        else:
            print("No valid round summaries found")
        print()

        # Find persistent issues
        persistent_issues = {}
        if issue_history:
            for rule_id, history in issue_history.items():
                try:
                    if isinstance(history, list) and len(history) >= min_persistence:
                        persistent_issues[rule_id] = history
                except Exception as e:
                    print(f"Warning: Error checking persistence for '{rule_id}': {e}")
                    continue

        if not persistent_issues:
            print("🎉 No persistent issues found!")
            print(f"All issues were resolved within {min_persistence-1} rounds.")
            return

        print("PERSISTENT ISSUES:")
        print("=" * 80)

        for rule_id, history in persistent_issues.items():
            try:
                if not history or not isinstance(history, list):
                    print(f"Warning: Invalid history for issue '{rule_id}'")
                    continue

                latest_entry = history[-1]
                if not isinstance(latest_entry, dict):
                    print(f"Warning: Invalid latest entry for issue '{rule_id}'")
                    continue

                latest_issue = latest_entry.get('issue_data', {})
                if not isinstance(latest_issue, dict):
                    print(f"Warning: Invalid issue data for '{rule_id}'")
                    continue

                description = latest_issue.get('description', 'No description')
                incident_messages = latest_issue.get('incident_messages', [])

                print(f"Issue: {rule_id}")
                print(f"Description: {description}")

                if isinstance(incident_messages, list) and incident_messages:
                    for message in incident_messages:
                        if isinstance(message, str) and message:
                            print(f"Message: {message}")
                else:
                    print("Message: No specific messages available")
                print()

            except Exception as e:
                print(f"Warning: Error displaying issue '{rule_id}': {e}")
                print()
                continue

    except Exception as e:
        print(f"Error: Failed to analyze persistent issues: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze persistent issues across migration rounds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python persistent_issues_analyzer.py .migration-workspace
  python persistent_issues_analyzer.py .migration-workspace --min-rounds 2
  python persistent_issues_analyzer.py /path/to/project/.migration-workspace --min-rounds 4
        """
    )

    parser.add_argument('workspace_dir', nargs='?', default='.migration-workspace',
                       help='Path to migration workspace directory (default: .migration-workspace)')
    parser.add_argument('--min-rounds', type=int, default=3,
                       help='Minimum rounds for an issue to be considered persistent (default: 3)')

    args = parser.parse_args()

    if not Path(args.workspace_dir).exists():
        print(f"❌ Workspace directory '{args.workspace_dir}' not found")
        print("💡 Run this script from the project directory where migration was performed")
        sys.exit(1)

    analyze_persistent_issues(args.workspace_dir, args.min_rounds)


if __name__ == "__main__":
    main()