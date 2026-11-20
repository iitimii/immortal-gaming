# World Secret System Design Notes

This document describes the phase-one design of the "world secret" system. A world secret is a hidden main storyline of a run that is independent of the map preset: one secret is chosen at the start of the run, the system splits it into several fragments and randomly binds trigger sources for the current run; different avatars discover fragments independently, and if an avatar collects all fragments, it learns the complete secret and decides in a one-time choice whether to reveal it.

The current design goal is to make the core experience solid first: only one world secret is enabled per run; fragments are discovered through passive events; avatar knowledge is independent; the player views the full picture through the TopBar from the default god's-eye view; avatar AI only knows the information it actually holds.

## 1. Goals

The world secret system aims to convey a sense of a long-term main storyline:

1. There is a preset truth behind the world.
2. The truth is not published directly through a quest, but gradually reconstructed from several fragments seen from different angles.
3. Fragments are not bound to a specific map preset; the static content is independent of the map.
4. At the start of each run, the system randomly places fragments into locations, cities or low-probability insight triggers on the current map.
5. Each avatar maintains its own secret knowledge, which is not shared.
6. An avatar obtains the complete secret after collecting all fragments.
7. The collector immediately decides through a finite choice whether to reveal it; non-roleplayed avatars decide via the LLM, and the roleplayed avatar hands the choice to the player.
8. Once revealed, the complete secret becomes common knowledge under heaven; all current and later newly awakened / newly born cultivators know the complete secret by default.

## 2. Boundaries with Existing Systems

### 2.1 Difference from world_lore

`world_lore` is the start-of-run world-setting shaping input, mainly used to rewrite static objects such as the map, sects and items. It is a "start-of-run shaping" system.

The world secret is a runtime main-storyline clue progress system that stores avatars' personal knowledge, fragment discoveries, complete-secret awareness and reveal state. It is a "current run progress" system.

Therefore the world secret should not be stuffed into `src/classes/world_lore.py` or `world_lore_snapshot`. The two can coexist in the same run, but are independent of each other in phase one.

### 2.2 Difference from random_minor_event

Random minor events are one-off everyday narratives with no long-term main-storyline progress after the event happens.

The world secret has long-term state:

- the active secret of the current run;
- fragment trigger bindings;
- the fragments known to each avatar;
- whether each avatar knows the complete secret;
- whether it has been revealed to all under heaven.

Therefore events only record the fact of discovery and are not the source of truth; the source of truth must be stored in `World` and `Avatar` state.

### 2.3 Difference from opportunity

An opportunity is a time-limited sensing for a single avatar, settled after the avatar moves close to the target.

The world secret is not a quest, opportunity or action target:

- No new active inquiry action is added.
- City inquiry is a passive event.
- Location awareness is a passive event.
- Mysterious insight is a low-probability passive event.
- Whether an avatar changes its behavior because of known fragments is left to AI decision-making.

## 3. Non-Goals

Phase one explicitly does not do the following:

1. No enabling of multiple world secrets at the same time.
2. No new active inquiry, investigation or secret-pursuing actions.
3. No point-to-point active telling of others.
4. No revealing of the specific location or city a fragment is bound to the frontend player.
5. No numeric or world-rule consequences from the world secret.
6. No injecting of the complete secret into every avatar's AI context.
7. No multi-language content; only English (`en-US`) content is maintained.
8. No including the world secret as part of `world_lore` for map or sect rewriting.

## 4. Start-of-Run Selection

The start-of-run configuration adds `world_secret_id`, which belongs to `RunConfig` / `NewGameDefaults`.

Allowed values:

- `none`: no world secret.
- `random`: randomly choose one from the non-`none` presets by weight.
- A specific secret ID: enable the corresponding world secret.

The start-of-run frontend dropdown displays the concrete titles; the options include:

- None
- Random
- All preset secret titles

`none` should exist as a real configuration entry, not rely only on special-case logic. This way the frontend and backend selection lists, save files and queries can all handle it uniformly.

Only one active world secret is allowed per run. If multiple secrets are to be supported later, a new version of the design should be started.

## 5. Static Configuration

It is recommended to add two CSVs:

```text
static/game_configs/world_secret.csv
static/game_configs/world_secret_fragment.csv
```

### 5.1 `world_secret.csv`

Recommended fields:

```csv
id,title,secret,weight
ID,Title,Complete secret,Random weight
none,None,,0
fake_sky,This World's Sky Is False,"The sky is not a natural firmament, but a vast masking barrier; the sun, moon, and stars are projections, and the true world is sealed inside some vessel or prison.",10
```

Notes:

- `id` uses English snake_case as a stable ID.
- `title` is displayed to the player in the god's-eye view.
- `secret` is the complete secret body text.
- `weight` is used for `random` start-of-run selection.
- For `none`, `secret` is empty, the fragment count is 0 and the weight is 0.

### 5.2 `world_secret_fragment.csv`

Recommended fields:

```csv
id,secret_id,order,angle,text,trigger_kind
ID,Secret ID,Order,Fragment angle,Fragment text,Trigger type
fake_sky_1,fake_sky,1,Celestial Anomaly,"The sky sometimes flickers for the briefest instant, and the positions of the stars slip into arrangements that violate celestial patterns.",region
fake_sky_2,fake_sky,2,Ascension Boundary,"When high-realm cultivators attempt ascension, it is not that they cannot reach beyond the sky; at a certain height, they strike an unseen wall.",insight
```

Notes:

- The number of fragments is not fixed.
- Most current presets can keep 6 fragments, but the system does not hard-code 6.
- `angle` ensures that fragments organize the truth from different angles, rather than degenerating into random ghost stories.
- In phase one, `trigger_kind` only allows:
  - `region`
  - `city`
  - `insight`

## 6. Preset Content

Phase one directly uses the batch of presets given in the requirements. Titles are kept essentially as in the original, and IDs use English snake_case.

Suggested IDs:

- `upper_world_feeds_on_ascenders`: Upper-Realm Powers Feed on Ascended Cultivators
- `fake_sky`: This World's Sky Is False
- `mad_heavenly_dao`: The Will of Heaven Has Gone Mad
- `simulated_world_code`: The World Is Simulated Code
- `spiritual_qi_is_dead_memories`: Spiritual Qi Is the Memory of the Dead
- `sects_on_colossal_corpses`: All Sects Are Built on Colossal Corpses
- `reincarnation_is_copying`: Reincarnation Does Not Exist; Rebirth Is Copying
- `yao_are_previous_humans`: The Yao Were Humans from the Previous Era
- `realms_are_artificial_shackles`: Cultivation Realms Are Artificial Shackles
- `moon_is_an_eye`: The Moon Is an Eye Watching This World
- `secret_realms_are_tumors`: Secret Realms Are Tumors Grown by the World
- `dead_gods_answer_prayers`: The Gods and Buddhas Are Dead; Their Corpses Answer Prayers

The copy may be lightly restructured for the configuration tables, but its core meaning must not change.

## 7. Runtime Model

Suggested additions:

```text
src/classes/world_secret.py
src/systems/world_secret.py
```

### 7.1 Static definition model

Suggested domain model:

```python
@dataclass
class WorldSecretFragment:
    id: str
    secret_id: str
    order: int
    angle: str
    text: str
    trigger_kind: str


@dataclass
class WorldSecretDefinition:
    id: str
    title: str
    secret: str
    weight: float
    fragments: list[WorldSecretFragment]
```

These objects are produced by the CSV loader and are not saved directly into the save file.

### 7.2 World runtime state

Suggested to hang on `World`:

```python
world_secret: WorldSecretRuntime = field(default_factory=WorldSecretRuntime)
```

Suggested model:

```python
@dataclass
class WorldSecretTriggerBinding:
    fragment_id: str
    trigger_kind: str
    region_id: int | None = None
    city_region_id: int | None = None


@dataclass
class WorldSecretRuntime:
    selected_secret_id: str = "none"
    trigger_bindings: dict[str, WorldSecretTriggerBinding] = field(default_factory=dict)
    resolved_by_avatar_ids: set[str] = field(default_factory=set)
    disclosure_decisions: dict[str, str] = field(default_factory=dict)
    public_revealed: bool = False
    public_revealed_month: int | None = None
    public_revealed_by_avatar_id: str | None = None
```

Notes:

- `selected_secret_id = "none"` means there is no secret.
- `trigger_bindings` is the random binding result of the current run and must be saved.
- `resolved_by_avatar_ids` records the avatars that have ever collected the secret.
- `disclosure_decisions` records each collector's one-time reveal/silence choice.
- Once `public_revealed` is true, all avatars know the complete secret by default.

### 7.3 Avatar personal knowledge

Suggested to hang on `Avatar`:

```python
world_secret_knowledge: dict[str, AvatarWorldSecretKnowledge]
```

Suggested model:

```python
@dataclass
class AvatarWorldSecretKnowledge:
    secret_id: str
    known_fragment_ids: set[str] = field(default_factory=set)
    knows_full_secret: bool = False
    full_secret_month: int | None = None
```

Even if phase one only enables one secret, it is still recommended to store it as a mapping keyed by `secret_id`, to avoid rework when extending later.

## 8. Current Run Initialization

Start-of-run initialization timing: after the map is loaded and `World` is created, either before or after NPC initialization; if the initial avatars should be immediately affected by the reveal state, it is recommended to call a knowledge sync once uniformly after avatar creation.

Recommended flow:

1. Read `run_config.world_secret_id`.
2. If it is `none`:
   - `world.world_secret.selected_secret_id = "none"`;
   - `trigger_bindings = {}`;
   - Do not trigger any subsequent logic.
3. If it is `random`:
   - Randomly choose from the non-`none` secrets by `weight`.
4. If it is a specific ID:
   - Enable the corresponding secret.
5. Create a trigger binding for each fragment:
   - `region`: randomly bind a non-wilderness, non-city region.
   - `city`: randomly bind a city region.
   - `insight`: no location binding.
6. The binding results go into `world.world_secret.trigger_bindings`.

`region` may bind to ordinary regions, cave dwellings/ruins, sect headquarters and other non-city regions. Sect headquarters may make certain clues easier for sect members to come across, which is an allowed narrative effect.

## 9. Passive Triggers

World secret discovery is a passive event; no active action is added.

Suggested new phase:

```python
phase_world_secret_discovery(world, living_avatars)
```

It is suggested to hook it in after action execution, near the ordinary world event / opportunity checks, so that an avatar can trigger it in the same month it moves into the target region.

### 9.1 Location awareness

Conditions:

1. The active secret of the current run is not `none`.
2. The fragment's `trigger_kind == "region"`.
3. The avatar's current `avatar.tile.region.id == binding.region_id`.
4. The avatar does not yet know the fragment.
5. The probability roll hits.

Event:

- Generate an ordinary event.
- The event text may include the fragment text.
- `related_avatars=[avatar.id]`.
- `is_major=False`.
- `is_story=False`.

### 9.2 City inquiry

City inquiry is a passive event; there is no active inquiry action.

Conditions:

1. The fragment's `trigger_kind == "city"`.
2. The avatar is currently inside the bound city, i.e. `avatar.tile.region.id == binding.city_region_id`.
3. The avatar does not yet know the fragment.
4. The probability roll hits.

The event can read:

```text
So-and-so heard a hidden clue in the market rumors of a certain city: ...
```

### 9.3 Mysterious insight

Conditions:

1. The fragment's `trigger_kind == "insight"`.
2. The avatar can trigger world events.
3. The avatar does not yet know the fragment.
4. A low-probability roll hits.

The event can read:

```text
So-and-so glimpsed a corner of the truth through a mysterious insight: ...
```

### 9.4 Probability pacing

The requirement target is "medium pace". Specific probabilities are decided at implementation time; suggested magnitudes:

- Location awareness: about `0.04` per avatar per month.
- City inquiry: about `0.05` per avatar per month.
- Mysterious insight: about `0.003` per avatar per month.

These values can start as static balance configuration and be tuned later based on experience.

The same avatar may obtain multiple fragments in the same month. If multiple triggers hit at the same time, all hits are recorded and produce events.

## 10. Collection and the Complete Secret

When the fragments known to an avatar cover all fragments of the active secret:

1. Set the avatar's `knows_full_secret=True`.
2. Set `full_secret_month=int(world.month_stamp)`.
3. Record `world.world_secret.resolved_by_avatar_ids.add(avatar.id)`.
4. Generate a major event indicating that the avatar has learned a world secret.
5. Immediately trigger the reveal/silence choice.

The collection event does not include the complete secret body text, to avoid conflicting with the "whether to reveal" semantics.

Recommended event:

```text
So-and-so connected scattered clues and finally learned a world secret capable of shaking this realm's foundations.
```

Note: the event contains neither the title nor the complete secret. The TopBar god's-eye view can display the full information, but the world event feed still preserves suspense from the avatar's perspective.

## 11. Reveal/Silence Choice

Each collector has only one choice:

- `share_all`
- `keep_secret`

### 11.1 Decision source

By default, the avatar decides via the LLM.

If the collector is exactly the avatar currently controlled in roleplay mode, it goes through the existing `single_choice` / roleplay choice and the player chooses.

If the player is roleplaying A but B collects the secret, B still decides automatically via the LLM.

### 11.2 LLM failure fallback

If the LLM decision fails or returns an invalid option, the fallback defaults to `keep_secret`.

Rationale:

- Avoids accidentally revealing the secret to the world because of a model failure;
- Silence is the default choice with fewer side effects.

### 11.3 Reveal

If `share_all` is chosen:

1. `world.world_secret.public_revealed=True`.
2. Record the reveal time and the revealer.
3. All currently living avatars know the complete secret by default.
4. Later newly born / newly awakened cultivators know the complete secret by default.
5. There is no need to fill in all fragments for every avatar.

The event after a reveal may include the complete secret title, but whether to include the full body text should still be handled with care. The recommended event only includes the title and the fact of the reveal, not the long body text:

```text
So-and-so revealed a world secret to all: 'This World's Sky Is False'. From now on, cultivators under heaven know this realm's truth.
```

The complete secret body text is still mainly displayed through the TopBar world secret panel.

### 11.4 Silence

If `keep_secret` is chosen:

1. Only record `disclosure_decisions[avatar.id] = "keep_secret"`.
2. Do not propagate it to other avatars.
3. Either an ordinary or a major event is acceptable; an ordinary event is recommended.

Recommended event:

```text
So-and-so chose silence after learning the truth, pressing this secret deep into the heart.
```

## 12. Information Boundaries

This system must strictly distinguish three kinds of perspective.

### 12.1 Player TopBar god's-eye view

The player sees everything by default from the god's-eye view.

From the start of the run, the TopBar world secret panel can display:

- the current secret title;
- the complete secret;
- all fragments;
- which avatars know each fragment;
- the number of fragments known to each avatar;
- which avatars know the complete secret;
- whether it has been revealed;
- the revealer and the reveal time.

But the TopBar does not reveal the specific location or city a fragment is bound to.

### 12.2 Event feed

Fragment text may appear in the event feed.

The event feed should not write the complete secret body text before an avatar has collected everything. The collection event also does not include the complete secret.

If revealed to the world, the event may include the title and the fact of the reveal; the full body text still need not be written into ordinary events, to keep the event panel from getting too long.

### 12.3 Avatar AI / decision context

This is the most critical boundary.

Avatar AI can only see the information it actually knows:

- the text of known fragments;
- the complete secret, if it knows the complete secret itself;
- the complete secret, if the world has had it revealed;
- not the title, when it does not know the complete secret;
- not the secret, when it does not know the complete secret;
- not undiscovered fragments, when it does not know the complete secret;
- never the locations or cities fragments are bound to.

Reason: the title itself is often the answer, e.g. "This World's Sky Is False". Putting the title into avatar info while the avatar only knows fragments would amount to giving away the answer directly, breaking the fragment-deduction semantics.

Therefore the field in avatar info should not be called `active_secret_title`. Recommended structure:

```json
"world_secret_knowledge": {
  "known_fragments": [
    {
      "angle": "Celestial Anomaly",
      "text": "The sky sometimes flickers for the briefest instant, and the positions of the stars slip into arrangements that violate celestial patterns."
    }
  ],
  "knows_full_secret": false,
  "full_secret": ""
}
```

If the avatar knows the complete secret or the world has had it revealed:

```json
"world_secret_knowledge": {
  "known_fragments": [
    {
      "angle": "Celestial Anomaly",
      "text": "The sky sometimes flickers for the briefest instant, and the positions of the stars slip into arrangements that violate celestial patterns."
    }
  ],
  "knows_full_secret": true,
  "secret_title": "This World's Sky Is False",
  "full_secret": "The sky is not a natural firmament, but a vast masking barrier; the sun, moon, and stars are projections, and the true world is sealed inside some vessel or prison."
}
```

After a reveal there is no need to fill in all fragments for the avatar; the AI context only needs the complete secret and the fragments it has actually discovered.

## 13. AI Decision Integration

An avatar's known fragments should go into avatar info and be visible during decision-making.

It is recommended to add them only to the detailed info, for example:

- `avatar.get_expanded_info(detailed=True)`
- or the AI decision context assembly layer

It is not recommended to stuff large amounts of fragment text into the lightweight `get_info()`, to keep the size of lists, details and prompts under control.

When it does not know the complete secret, the AI can only associate and decide on its own based on the fragments; the system does not hard-code specific behavior.

After it knows the complete secret, the AI may react on its own in thinking, goals and action choices. In phase one the system provides no numeric consequences.

## 14. Query API

Suggested new read-only endpoints:

```text
GET /api/v1/query/meta/world-secrets
GET /api/v1/query/world-secrets/overview
```

### 14.1 `meta/world-secrets`

Used for the start-of-run dropdown.

Example response:

```json
{
  "secrets": [
    {"id": "none", "title": "None"},
    {"id": "random", "title": "Random"},
    {"id": "fake_sky", "title": "This World's Sky Is False"}
  ]
}
```

### 14.2 `world-secrets/overview`

Used for the TopBar panel; everything is visible from the god's-eye view, but trigger locations are not revealed.

Example response:

```json
{
  "active_secret": {
    "id": "fake_sky",
    "title": "This World's Sky Is False",
    "secret": "The sky is not a natural firmament, but a vast masking barrier; the sun, moon, and stars are projections, and the true world is sealed inside some vessel or prison.",
    "fragment_count": 6
  },
  "public_revealed": false,
  "public_revealed_by": null,
  "fragments": [
    {
      "id": "fake_sky_1",
      "order": 1,
      "angle": "Celestial Anomaly",
      "text": "The sky sometimes flickers for the briefest instant, and the positions of the stars slip into arrangements that violate celestial patterns.",
      "known_by": [
        {"id": "avatar_1", "name": "Li Qing", "is_dead": false}
      ]
    }
  ],
  "avatars": [
    {
      "id": "avatar_1",
      "name": "Li Qing",
      "known_fragment_count": 1,
      "fragment_count": 6,
      "knows_full_secret": false,
      "decision": null,
      "is_dead": false
    }
  ]
}
```

The `none` response can be:

```json
{
  "active_secret": {
    "id": "none",
    "title": "None",
    "secret": "",
    "fragment_count": 0
  },
  "public_revealed": false,
  "fragments": [],
  "avatars": []
}
```

## 15. Frontend

The TopBar always displays the world secret slot.

If the current value is `none`, the label can show "World Secret: None", or the panel can show "No world secret is enabled in this run" after clicking.

Suggested additions:

```text
web/src/stores/worldSecret.ts
web/src/components/game/panels/WorldSecretModal.vue
web/src/composables/useWorldSecretModal.ts
```

Integration points:

- `web/src/components/layout/StatusBar.vue`
- `web/src/components/layout/StatusBarPanels.vue`
- `web/src/api/modules/world.ts`
- `web/src/api/mappers/worldSecret.ts` or merged into the existing world mapper
- `web/src/types/api.ts`

Suggested modal layout:

1. Summary section: current secret title, complete secret, reveal status.
2. Fragment section: display `angle` and `text` in `order`, listing the avatars who know each one.
3. Avatar section: each avatar's known progress, whether it knows the complete secret, and whether it has made the reveal/silence choice.

Do not display the region/city a fragment is bound to in the panel.

## 16. Save Structure

World-level state goes into `world_data`:

```json
"world_secret": {
  "selected_secret_id": "fake_sky",
  "trigger_bindings": {
    "fake_sky_1": {
      "fragment_id": "fake_sky_1",
      "trigger_kind": "region",
      "region_id": 101,
      "city_region_id": null
    }
  },
  "resolved_by_avatar_ids": ["avatar_1"],
  "disclosure_decisions": {
    "avatar_1": "keep_secret"
  },
  "public_revealed": false,
  "public_revealed_month": null,
  "public_revealed_by_avatar_id": null
}
```

Avatar-level knowledge goes into the avatar save dict:

```json
"world_secret_knowledge": {
  "fake_sky": {
    "known_fragment_ids": ["fake_sky_1"],
    "knows_full_secret": false,
    "full_secret_month": null
  }
}
```

During the development phase there is no requirement to pay complex compatibility costs for old save files; a zero-cost `.get` fallback on load is enough.

## 17. New Avatar Sync

When `world.world_secret.public_revealed=True`:

1. All currently living avatars know the complete secret by default.
2. Later newly born / newly awakened cultivators also know the complete secret by default after creation.
3. There is no need to fill in fragments.

Suggested unified helper:

```python
sync_avatar_public_world_secret_knowledge(world, avatar)
```

Call it on new avatar creation, on rebuild after loading, and in batch after a reveal to the world.

## 18. Event Semantics

### 18.1 Fragment discovery event

- `is_major=False`
- `is_story=False`
- `related_avatars=[avatar.id]`
- May include the fragment text

### 18.2 Collection event

- `is_major=True`
- `is_story=False`
- `related_avatars=[avatar.id]`
- Does not include the title
- Does not include the complete secret

### 18.3 Reveal event

- `is_major=True`
- `is_story=False`
- `related_avatars=[avatar.id]`
- May include the title
- Recommended not to include the complete secret body text

### 18.4 Silence event

- May be `is_major=False`
- `is_story=False`
- `related_avatars=[avatar.id]`
- Does not include the complete secret

## 19. i18n

The game is English-only; `en-US` is the sole and source locale.

The world secret body text and fragments are large amounts of narrative content; the first version can place them directly in the CSVs, with frontend copy added to `en-US`.

Rules to follow:

1. The language list is defined by `static/locales/registry.json`.
2. Configuration text may migrate to `game_configs_modules` or the localized CSV under `static/locales/en-US/game_configs/`.
3. `msgid` in `.po` files uses English source text or stable keys.
4. The split source files under `modules/` and `game_configs_modules/` are the source of truth; do not edit the merged `LC_MESSAGES/*.po` artifacts directly.
5. Run `python tools/i18n/build_mo.py` after editing source files.

## 20. Recommended Implementation Locations

When implementing later, it is recommended to add independent modules, to avoid piling logic into `main.py`, `world_lore` or the random event system.

Possible locations:

- `src/classes/world_secret.py`
- `src/systems/world_secret.py`
- `src/systems/world_secret_loader.py`
- `src/systems/world_secret_service.py`

Integration points:

- `src/config/settings_schema.py`: add `world_secret_id`
- `src/server/init_flow.py`: initialize the current run's secret and bindings
- `src/classes/core/world.py`: mount the runtime
- `src/classes/core/avatar/core.py`: mount personal knowledge
- `src/sim/save/save_game.py`: save the world secret
- `src/sim/load/load_game.py`: restore the world secret
- `src/sim/save/avatar_save_mixin.py`: save avatar secret knowledge
- `src/sim/load/avatar_load_mixin.py`: restore avatar secret knowledge
- `src/sim/simulator_engine/phases/world.py`: add the passive discovery phase
- `src/sim/simulator_engine/simulator.py`: hook in the phase
- `src/server/services/game_query_service.py`: add query assembly
- `src/server/api/public_v1/query.py`: add the v1 query routes

## 21. Testing Suggestions

Cover at least:

1. The CSV loader can load `none` and all presets.
2. Every non-`none` secret has at least one fragment.
3. Every fragment's `secret_id` exists.
4. Fragment `order` is not duplicated within the same secret.
5. `trigger_kind` only allows `region/city/insight`.
6. `random` never selects `none`.
7. `none` initialization does not generate trigger bindings.
8. After initializing a specific secret, every non-insight fragment has a valid binding.
9. `region` bindings do not choose cities or wilderness.
10. `city` bindings only choose cities.
11. An avatar obtains a fragment when inside the bound region and the probability roll hits.
12. An avatar obtains a fragment when inside the bound city and the probability roll hits.
13. A fragment is obtained when the insight probability roll hits.
14. Known fragments are not obtained again.
15. The same avatar can obtain multiple hit fragments in the same month.
16. `knows_full_secret=True` after collecting all fragments.
17. The collection event contains neither the title nor the complete secret.
18. After the LLM chooses `share_all`, the world is publicly revealed and all currently living avatars know the complete secret.
19. LLM failure falls back to `keep_secret`.
20. When the roleplayed avatar collects everything, it goes through the roleplay choice; non-roleplayed avatars still go through the LLM.
21. After a reveal, newly awakened avatars know the complete secret by default.
22. After a reveal, filling in all fragments is not forced.
23. When the avatar AI context does not know the complete secret, it only contains known fragments, without title/secret/undiscovered fragments/bound locations.
24. When the avatar AI context knows the complete secret, it may contain the title and the full secret.
25. The TopBar overview fully reveals title/secret/fragments, but not bound locations.
26. The world secret and avatar knowledge can be saved and restored on load.
27. `/api/v1/query/meta/world-secrets` returns `none/random/specific secrets`.
28. `/api/v1/query/world-secrets/overview` returns a stable empty state for `none`.
29. The frontend lazy modal requests data when initially mounted with `show=true`, and the watcher uses `{ immediate: true }`.

## 22. Current Decisions

Final conclusions after this round of requirement confirmation:

1. The player TopBar is the default god's-eye view and fully reveals the complete secret and fragments.
2. The start-of-run dropdown displays concrete titles.
3. `none` is a real configuration entry.
4. Only one world secret is allowed per run.
5. The number of fragments is not fixed.
6. Each fragment configures a `trigger_kind`.
7. `region` binds to non-city regions; sect headquarters are allowed.
8. City inquiry requires being inside the corresponding city, and is a passive event.
9. The trigger pace is medium; specific probabilities are tuned at implementation.
10. The same avatar can obtain multiple fragments in the same month.
11. Fragments go into avatar decision info, but the title is not provided while the complete secret is unknown, to avoid giving away the answer.
12. Fragment text may appear in the event feed.
13. Immediately after collecting everything, the reveal/silence choice is made.
14. Non-roleplayed avatars choose via the LLM; the choice goes to the player only when the collector is being roleplayed by the player.
15. A reveal only grants the complete secret and does not fill in fragments.
16. After a reveal, later newly awakened / newly born cultivators know the complete secret by default.
17. The world secret has no numeric consequences.
18. Phase one is English-only (`en-US`).
19. The world secret is independent of `world_lore`.
20. Preset content uses the original batch given in the requirements, with titles kept essentially as in the original.
