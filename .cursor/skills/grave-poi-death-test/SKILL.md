---
name: grave-poi-death-test
description: "Verify avatar death, grave POI creation, map rendering, and click-through to details via a real game simulation. Use for tasks that need to test lifespan death or other in-game death flows and grave POIs, without calling handle_death directly."
---

# Grave Death Verification

Start the test run with an isolated data directory; never pollute the user's current saves or settings. Death must come from the normal settlement path of `Simulator.step()`. Do not call `handle_death()` directly, register graves by hand, or fabricate death events for the sake of the test.

## Flow

1. Read `docs/specs/external-control-api.md`, and create or configure test avatars through `/api/v1/command/*`; do not modify `game_instance` directly.
2. Give the test avatar a death condition that will be reached naturally. Lifespan death is the most reliable: create an elderly avatar, then run full monthly simulation steps until death settlement completes.
3. If the full simulation depends on an LLM, use a local OpenAI-compatible stub dedicated to this test; its data directory, listening port, and process name must be isolated from the normal development services.
4. Verify the full causal chain through the API:
   - The avatar detail has `is_dead` set to true and includes `death_info`.
   - The `pois` of `world/map` contain `kind: "grave"`, at the same position where the deceased died.
   - The grave summary contains `deceased_avatar_id`, used by the frontend to link into the avatar detail.
5. On the actual frontend map, confirm the icon has loaded, is close to avatar portrait size, and is clickable. Clicking the grave should select the `avatar` and open the deceased's existing avatar detail, not a separate grave detail panel.

## Minimal Verification

```powershell
pytest tests/test_death.py
cd web
npm run type-check
npm run test -- src/__tests__/composables/useTextures.test.ts
```

For UI verification, prefer any available browser control tool; only fall back to local Playwright opening the isolated frontend service when none is available. Do not substitute end-to-end verification with direct calls to the death handling function.

## Cleanup

After the test, pause the test run first, then stop the frontend, backend, and LLM stub processes started for this run. Delete the dedicated data directory, stub, logs, and screenshots for this run; keep only the real implementation and regression tests in the repository. Before cleaning up, verify that every target lives under the repository's `tmp/` or `web/tmp/`; never touch the user's regular data directory or services that are in use.
