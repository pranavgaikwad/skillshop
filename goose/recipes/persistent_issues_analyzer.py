#!/usr/bin/env python3
"""
Persistent Issues Analyzer for Migration Workspace
Examines round directories to identify issues that persist across multiple analysis rounds.
Helps identify problematic issues that the agent is struggling to fix.
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
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not load {yaml_file}: {e}")
        return None


def extract_issues_from_round(round_dir):
    """Extract all issues from a round directory"""
    kantra_file = round_dir / "kantra_output.yaml"
    if not kantra_file.exists():
        return None, {}

    data = load_kantra_output(kantra_file)
    if not data:
        return None, {}

    issues = {}
    total_incidents = 0

    for ruleset in data:
        if 'violations' not in ruleset:
            continue

        ruleset_name = ruleset.get('name', 'Unknown')

        for rule_id, violation in ruleset['violations'].items():
            incidents = violation.get('incidents', [])
            files_affected = set()

            for incident in incidents:
                uri = incident.get('uri', '')
                if uri.startswith('file://'):
                    file_path = uri[7:]  # Remove 'file://' prefix
                    files_affected.add(file_path)

            issues[rule_id] = {
                'description': violation.get('description', 'No description'),
                'category': violation.get('category', 'unknown'),
                'effort': violation.get('effort', 'unknown'),
                'ruleset': ruleset_name,
                'incident_count': len(incidents),
                'files_affected': list(files_affected)
            }
            total_incidents += len(incidents)

    return total_incidents, issues


def find_workspace_rounds(workspace_dir):
    """Find all round directories in the workspace"""
    workspace_path = Path(workspace_dir)
    if not workspace_path.exists():
        return []

    rounds = []
    for item in workspace_path.iterdir():
        if item.is_dir() and item.name.startswith('round_'):
            timestamp = parse_round_timestamp(item.name)
            if timestamp:
                rounds.append({
                    'path': item,
                    'name': item.name,
                    'timestamp': timestamp
                })

    # Sort by timestamp
    rounds.sort(key=lambda x: x['timestamp'])
    return rounds


def analyze_persistent_issues(workspace_dir, min_persistence=3):
    """Analyze issues that persist across multiple rounds"""
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
        round_dir = round_info['path']
        round_name = round_info['name']
        timestamp = round_info['timestamp']

        total_incidents, issues = extract_issues_from_round(round_dir)

        if total_incidents is None:
            print(f"⚠️  Skipping {round_name} - no valid Kantra output found")
            continue

        round_summary = {
            'name': round_name,
            'timestamp': timestamp,
            'total_incidents': total_incidents,
            'unique_issues': len(issues),
            'issues': issues
        }
        round_summaries.append(round_summary)

        # Track each issue
        for rule_id, issue_data in issues.items():
            issue_history[rule_id].append({
                'round': round_name,
                'timestamp': timestamp,
                'incident_count': issue_data['incident_count'],
                'files_affected': issue_data['files_affected'],
                'issue_data': issue_data
            })

    print("📊 ROUND SUMMARY:")
    print("-" * 40)
    for summary in round_summaries:
        print(f"{summary['name']}: {summary['unique_issues']} issues, {summary['total_incidents']} incidents")
    print()

    # Find persistent issues
    persistent_issues = {}
    for rule_id, history in issue_history.items():
        if len(history) >= min_persistence:
            persistent_issues[rule_id] = history

    if not persistent_issues:
        print("🎉 No persistent issues found!")
        print(f"All issues were resolved within {min_persistence-1} rounds.")
        return

    print("🔴 PERSISTENT ISSUES DETECTED:")
    print("=" * 80)
    print(f"Found {len(persistent_issues)} issues persisting {min_persistence}+ rounds")
    print()

    # Analyze each persistent issue
    for rule_id, history in persistent_issues.items():
        latest_issue = history[-1]['issue_data']

        print(f"📌 Issue: {rule_id}")
        print(f"   Description: {latest_issue['description']}")
        print(f"   Category: {latest_issue['category']}")
        print(f"   Effort Level: {latest_issue['effort']}")
        print(f"   Ruleset: {latest_issue['ruleset']}")
        print(f"   Persistence: {len(history)} rounds")

        print(f"   📈 History:")
        for entry in history:
            files_count = len(entry['files_affected'])
            print(f"      {entry['round']}: {entry['incident_count']} incidents, {files_count} files")

        print(f"   📁 Current Files Affected:")
        current_files = history[-1]['files_affected']
        for file_path in sorted(current_files):
            print(f"      - {file_path}")

        # Check if issue is getting worse, better, or staying the same
        incident_counts = [entry['incident_count'] for entry in history]
        if incident_counts[-1] > incident_counts[0]:
            trend = "🔺 WORSENING"
        elif incident_counts[-1] < incident_counts[0]:
            trend = "🔻 IMPROVING"
        else:
            trend = "➖ STABLE"

        print(f"   📊 Trend: {trend} ({incident_counts[0]} → {incident_counts[-1]} incidents)")
        print()

    # Provide recommendations
    print("💡 RECOMMENDATIONS:")
    print("=" * 50)

    # Group by category and effort
    by_category = defaultdict(list)
    by_effort = defaultdict(list)
    high_impact_issues = []

    for rule_id, history in persistent_issues.items():
        latest = history[-1]['issue_data']
        by_category[latest['category']].append(rule_id)
        by_effort[latest['effort']].append(rule_id)

        # High impact: many incidents or many files
        if latest['incident_count'] >= 5 or len(history[-1]['files_affected']) >= 3:
            high_impact_issues.append(rule_id)

    print(f"1. High Impact Issues ({len(high_impact_issues)} found):")
    for rule_id in high_impact_issues:
        latest = persistent_issues[rule_id][-1]['issue_data']
        print(f"   - {rule_id}: {latest['incident_count']} incidents, {len(persistent_issues[rule_id][-1]['files_affected'])} files")

    print(f"\n2. By Category:")
    for category, rule_ids in by_category.items():
        print(f"   - {category}: {len(rule_ids)} issues")

    print(f"\n3. By Effort Level:")
    for effort, rule_ids in by_effort.items():
        print(f"   - Level {effort}: {len(rule_ids)} issues")

    print(f"\n4. Suggested Actions:")
    print(f"   - Review fix strategies for high-effort issues (may need manual intervention)")
    print(f"   - Focus on mandatory category issues first")
    print(f"   - Consider if high-impact issues need different migration approaches")
    print(f"   - Check if persistent files have complex dependencies")


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