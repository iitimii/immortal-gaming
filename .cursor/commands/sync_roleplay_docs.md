When the user invokes this command, sync and tidy up the rules, skills, specs, and test follow-ups related to the "avatar roleplay mode (personal roleplay mode)".

Strictly follow this flow:

1. **Read the anchor files**:
   - `docs/specs/avatar-roleplay-mode.md`
   - `docs/specs/single-choice-unified-framework.md`
   - `.cursor/rules/roleplay-mode.mdc`
   - `.cursor/skills/roleplay-mode-implementation/SKILL.md`
   - `AGENTS.md`

2. **Check whether anything needs to be synced**:
   - If this change affects long-term constraints of roleplay mode, update `.cursor/rules/roleplay-mode.mdc`
   - If this change affects the recommended implementation flow for future agents, update `.cursor/skills/roleplay-mode-implementation/SKILL.md`
   - If this change affects the overall design, phase boundaries, or key state machines, update `docs/specs/avatar-roleplay-mode.md`
   - If this change affects the Phase 2 unified finite-decision framework, update `docs/specs/single-choice-unified-framework.md`
   - If any rule / skill under `.cursor` changed, update the root `AGENTS.md`

3. **Check that implementation semantics are still consistent**:
   - The default is still the god view, not a standalone "personal mode"
   - At most one avatar can be roleplayed at a time
   - Pause only at decision boundaries; never interrupt an action chain
   - Roleplay state, pending request, conversation session, and continuation are not saved
   - Phase 2 goes through the unified choice resolver / continuation first
   - Phase 3 conversations still hang off the `Conversation` action, and raw chat logs do not enter the long-term event stream

4. **Complete the test checklist and run regressions**:
   - Backend, check at least:
     - `tests/test_public_api_v1.py`
     - `tests/test_single_choice.py`
     - `tests/test_action_social.py`
     - `tests/test_mutual_actions.py`
   - Frontend, check at least:
     - `web/src/__tests__/components/game/RoleplayDock.test.ts`
     - `web/src/__tests__/components/game/roleplay/RoleplayViews.test.ts`
     - `web/src/__tests__/components/game/panels/info/components/RoleplayPanel.test.ts`
   - Run:
     - `pytest tests/test_public_api_v1.py tests/test_single_choice.py tests/test_action_social.py tests/test_mutual_actions.py -q`
     - `cd web && npm run type-check`
     - `cd web && npm run test`

5. **Output a summary when done**:
   - Whether the rule / skill / spec / AGENTS were updated this time
   - Whether this change affects Phase 1, Phase 2, or Phase 3
   - Which tests were run and which were not

Notes:

- Do not modify unrelated specs just because you are syncing docs.
- If the change is only an implementation detail and does not alter long-term constraints, do not force edits to `.cursor/rules/roleplay-mode.mdc`.
- If you changed `.cursor/rules`, `.cursor/skills`, or `.cursor/commands`, update `AGENTS.md` accordingly.
