# PatternFly Migration

## PatternFly 5 to 6

When migrating from PatternFly 5 to PatternFly 6, use the official `pf-codemods` tool.

### Run pf-codemods FIRST

**Critical**: Run this BEFORE making any manual code changes.

```bash
npx @patternfly/pf-codemods@latest <project_path> --v6 --fix
```

Options:
- `--v6`: Run PatternFly 5 to 6 codemods (required)
- `--fix`: Apply autofixes automatically
- `--only <rules>`: Run specific rules only
- `--exclude <rules>`: Exclude specific rules

The tool uses eslint-based autofixers for `@patternfly/react-core@5.x.x` to `6.x.x`. Some issues will still require manual fixes.

After running pf-codemods, proceed with the normal Kantra analysis loop.

### Fix Strategy

**Always prefer long-term fixes over temporary workarounds.**

When addressing PatternFly migration issues:
- Use the new recommended APIs and components, not deprecated alternatives
- Refactor to align with PatternFly 6 patterns rather than shimming old behavior
- Remove compatibility layers and legacy code paths
- Update component usage to match current PatternFly 6 documentation

Avoid:
- Suppressing warnings or lint errors without fixing underlying issues
- Using deprecated props with `// @ts-ignore` or similar
- Creating wrapper components that preserve old API signatures
- Pinning to intermediate versions to defer migration work
