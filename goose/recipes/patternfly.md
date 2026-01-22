# PatternFly Migration Instructions

## PatternFly 5 to 6 Migration

When migrating from PatternFly 5 to PatternFly 6, use the official `pf-codemods` tool to automate breaking changes.

### Run pf-codemods FIRST

**Critical**: Run pf-codemods BEFORE making any manual code changes to minimize manual intervention.

Execute in the Setup and Discovery phase, immediately after identifying the project structure:

```bash
npx @patternfly/pf-codemods@latest {{ input_path }} --v6 --fix
```

### Command Options

- `--v6`: Run PatternFly 5 to 6 codemods (required)
- `--fix`: Apply autofixes automatically (recommended)
- `--only <rules>`: Run specific comma-separated rules only
- `--exclude <rules>`: Exclude specific rules from the recommended set

### What pf-codemods Does

The tool uses eslint-based rules and autofixers to update `@patternfly/react-core@5.x.x` code to `6.x.x`. It automatically handles many breaking changes, though some issues will still require manual fixes.

### Integration with Migration Loop

1. Run pf-codemods during Setup phase
2. Proceed with normal Kantra analysis loop to address remaining issues
3. The tool's changes will be reflected in subsequent Kantra scans
