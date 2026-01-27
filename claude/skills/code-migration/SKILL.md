---
name: code-migration
description: Migrate applications between technology stacks using Kantra static analysis. Use when migrating Java, Node.js, Python, Go, or .NET applications, upgrading frameworks, or modernizing codebases. Handles iterative analysis, fix application, and validation until migration is complete.
---

# Code Migration with Kantra

Kantra is a static analysis tool that identifies migration issues using declarative YAML rules. It supports providers: java, nodejs, python, go, dotnet.

## Setup and Discovery

1. Explore the project structure and identify the build system (Maven, Gradle, npm, etc.)
2. Extract available build, test, and lint commands from configuration files
3. Create a migration workspace directory to store analysis outputs across rounds
4. Run `kantra --help` to familiarize yourself with available options
5. Check for target-specific instructions at `targets/<target>.md` (e.g., `targets/patternfly.md`). If found, follow that guidance first.

## Migration Loop

Execute this workflow. You MUST continue looping until the exit criteria in step 5 are satisfied.

### 1. Run Analysis

```bash
kantra analyze --input <project_path> --target <target1> --target <target2> --output <work_dir>/kantra-output --provider <provider>
```

Options:
- Add `--rules <path>` for custom rules
- Add `--enable-default-rulesets=false` to disable default rules

### 2. Parse Results

Use the bundled helper script:

```bash
# Summary of all issues
python scripts/kantra_output_helper.py summary <work_dir>/kantra-output/output.yaml

# List affected files
python scripts/kantra_output_helper.py files <work_dir>/kantra-output/output.yaml

# Issues in a specific file
python scripts/kantra_output_helper.py file <work_dir>/kantra-output/output.yaml <file_path>
```

### 3. Plan Fixes

Create a detailed fix plan based on logical grouping:

a) **Group interdependent issues** that should be addressed together

b) **Prioritize in this order**:
   - Build configuration (pom.xml, package.json, go.mod, etc.)
   - Foundation imports and dependencies
   - API/annotation changes: removals, rewrites, additions
   - Implementation details

c) **Identify additional migration issues** beyond Kantra findings:
   - Known breaking changes in the migration path
   - Deprecated APIs, patterns, or libraries
   - Dependency version conflicts
   - Issues documented in target-specific instruction files

d) **Document your fix plan** before starting

### 4. Apply Fixes and Validate

Apply fixes following your plan, then validate:

a) **Re-run Kantra analysis** to verify issue count decreased

b) **Run build** to ensure no compilation errors

c) **Run lint** (if available) to catch code quality issues

d) **Run tests** (if available) to verify no regressions

e) **Compare issue counts** to previous round - if no progress, reassess approach

### 5. Exit Decision

Evaluate exit criteria before starting the next iteration:

**Exit criteria (ALL must be true)**:
- Kantra analysis reports 0 issues
- Build succeeds
- Tests pass (if available)
- No known unfixed migration issues remain

**If criteria NOT met**: Go back to step 1. Do NOT exit until all criteria are satisfied.

**If an issue cannot be fixed**:
- Attempt at least 2 different approaches before marking unfixable
- Document why it cannot be fixed automatically
- Continue fixing other issues - unfixable issues do not allow early exit
- Only exit after ALL fixable issues are resolved AND unfixable ones are documented

## Guidelines

- **Focus on logical grouping**: Identify interdependent issues and fix them in optimal order
- **Be systematic**: Follow your planned fix order rather than addressing issues randomly
- **Be conservative**: Prefer minimal changes that maintain functionality
- **Be thorough**: Verify each fix doesn't break existing features
- **Analyze persistent issues**: If after 3+ rounds you have stubborn issues, reassess the approach and try alternative solutions
