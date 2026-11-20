When the user invokes this command, consolidate the rules, skills, and commands under the `.cursor` directory into the repository root `AGENTS.md`.

Strictly follow this flow:

1. **Collect sources**:
   - Read `.cursor/rules/*.mdc`
   - Read `.cursor/skills/*/SKILL.md`
   - Read `.cursor/commands/*.md` (including this command file)
2. **Update the target file**:
   - Create or update the root `AGENTS.md`
   - Organize it as "index + key constraints"; do not simply concatenate the source text
   - Include at least the following sections:
     - Format and precedence rules for how Codex automatically reads `AGENTS.md`
     - `.cursor/rules` rule index (scope + key constraints)
     - `.cursor/skills` skill index (purpose + key flow)
     - `.cursor/commands` command index (command name + function)
     - Common test and validation commands
     - Maintenance conventions
3. **Consistency requirements**:
   - Use UTF-8 encoding
   - Wrap paths, commands, and file names in backticks
   - Write the document in English, keeping terminology precise (e.g. `shallowRef`, `Socket`, `DTO`)
4. **Self-check when done**:
   - Check that `AGENTS.md` covers every rule/skill/command under `.cursor`
   - Check that no description conflicts with the original rules
   - Output a change summary and the list of added/changed commands

Notes:

- Do not modify the original contents of `.cursor/rules` or `.cursor/skills`.
- You may improve the organization, but must not alter the semantics of the rules.
