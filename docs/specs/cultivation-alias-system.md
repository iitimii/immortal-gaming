# Cultivation Rank Alias System Design

This document describes the design for "different orthodoxies / races using different names for cultivation ranks". The goal is to give the Martial, Confucian, Buddhist, Yao, and other systems their own cultivation terminology without breaking the existing realm logic, save files, action parameters, or the stability of the external API.

One-line principle:

> `Realm` is the underlying order of the world; a rank alias is the display language of the system an avatar belongs to.

## 1. Background and Goals

The game's underlying cultivation system is currently derived from `CultivationProgress.level`:

- `QI_REFINEMENT`: Qi Refinement
- `FOUNDATION_ESTABLISHMENT`: Foundation Establishment
- `CORE_FORMATION`: Core Formation
- `NASCENT_SOUL`: Nascent Soul

Each major realm is divided into:

- `EARLY_STAGE`: Early Stage
- `MIDDLE_STAGE`: Middle Stage
- `LATE_STAGE`: Late Stage

This system suits the underlying numbers, breakthroughs, lifespan, rankings, item grades, and action restrictions, but it has a problem in terms of world-building expression:

- A martial avatar should not necessarily call themselves "Qi Refinement / Foundation Establishment".
- A Confucian avatar should not necessarily call themselves "Core Formation / Nascent Soul".
- Buddhists and yao should also have their own cultivation vocabulary.
- The titles players see, and that appear in LLM narrative, should reflect the system an avatar belongs to, rather than everyone sharing the standard xianxia names.

Goals of this feature:

1. Keep the existing `Realm` / `Stage` / `level` as the single logical source of truth.
2. Add display aliases derived from the avatar's system.
3. Allow avatar details, event text, LLM context, and world info to use stylized titles.
4. Forbid aliases from entering save files, action parameters, item configs, and ordering checks.
5. Reserve a stable i18n structure so alias text is never hard-coded into the frontend or Python logic.

## 2. Non-Goals

This design explicitly does not do the following:

1. Do not change `Realm` enum values into display text or aliases.
2. Do not make `Realm.__str__()` return different results depending on the avatar.
3. Do not make action parameters accept all natural-language aliases as the main path.
4. Do not create a separate progression curve for each orthodoxy.
5. Do not change underlying rules such as breakthroughs, lifespan, combat power, movement speed, ranking groups, or item grades.
6. Do not require migrating display names out of old saves, because display names can be re-derived from the current config.

## 3. Design Principles

### 3.1 Separate IDs from display names

All cross-module contracts prefer stable IDs:

- `realm_id`: `QI_REFINEMENT`
- `stage_id`: `EARLY_STAGE`
- `level`: `1`
- `profile_id`: `dao` / `sanxiu` / `wu` / `confucianism` / `buddhism` / `yao`

Display names are only returned as derived fields:

- `canonical_realm_name`: `Qi Refinement`
- `canonical_stage_name`: `Early Stage`
- `display_realm_name`: `Body Tempering`
- `display_stage_name`: `Initial Attainment`
- `display_full_name`: `Body Tempering, Initial Attainment`

### 3.2 Aliases depend on the avatar context

The same `Realm.Foundation_Establishment + Stage.Middle_Stage` can be displayed as different text on different avatars:

- Daoist / rogue cultivator: Foundation Establishment Middle Stage
- Martial Path: Tendon-Tempering, Mid Attainment
- Confucian Path: Principle Illumination, Middle Realm
- Buddhist Path: Monk, Middle Realm
- Yao: Form Transformation Middle Stage

Therefore the alias resolution function must receive the avatar or an explicit profile; it must not be decided by the `Realm` alone.

### 3.3 The logic layer does not read display names

The following systems may only read IDs or enums, never aliases:

- Save / load
- Action parameter parsing
- `can_start` / `can_possibly_start`
- Item, elixir, material, hidden domain, and sect mission configs
- Ranking groups
- Breakthrough success rate
- Lifespan effects
- Combat power calculation
- Movement distance
- Command requests of the external control API

### 3.4 The display layer may use aliases freely

Aliases are suitable in the following places:

- Avatar details
- Avatar cards / hover / map markers
- The other party's cultivation in relation lists
- Event text
- Story event prompts
- AI decision context
- Roleplay mode context
- World Info descriptions
- Wiki / help panels

But these places should still keep the standard ID or canonical name alongside, so that the system, players, and external agents can understand the "equivalence".

## 4. Core Domain Model

### 4.1 The standard realm remains the single logical source of truth

The existing structure stays unchanged:

```python
class Realm(Enum):
    Qi_Refinement = "QI_REFINEMENT"
    Foundation_Establishment = "FOUNDATION_ESTABLISHMENT"
    Core_Formation = "CORE_FORMATION"
    Nascent_Soul = "NASCENT_SOUL"
```

`CultivationProgress.level` continues to derive the current realm and stage via `REALM_ORDER` / `STAGE_ORDER`.

### 4.2 New display profile

Add a "rank display system" concept, suggested name `CultivationAliasProfile` or a lightweight string `profile_id`.

Initial profiles:

| profile_id | Source | Description |
|---|---|---|
| `dao` | Daoist sects | Standard xianxia titles |
| `sanxiu` | Rogue cultivators | Uses the standard xianxia titles by default |
| `wu` | Martial Path | Body tempering, martial arts, grandmaster style |
| `confucianism` | Confucian Path | Study, nurturing qi, illuminating principle, establishing one's mandate style |
| `buddhism` | Buddhist Path | Novice monk, monk, arhat, bodhisattva style |
| `yao` | Yao | Spirit awakening, form transformation, demon core, demon king style |

### 4.3 Profile selection rules

Suggested centralized resolver:

```python
def resolve_cultivation_alias_profile(avatar: Avatar) -> str:
    ...
```

Initial recommended rules:

1. If the avatar is yao, prefer `yao`.
2. Otherwise, if the avatar has `orthodoxy.id`, use the corresponding orthodoxy ID.
3. Otherwise fall back to `sanxiu`.
4. If the profile config is missing, fall back to `dao`.

There is a world-building choice here:

- Option A: yao always use yao rank names, even after joining a human sect.
- Option B: after joining a specific human sect, yao are displayed using the sect orthodoxy's titles.

This design recommends adopting Option A first. The reason is that "yao" is a stronger identity in players' minds than sect orthodoxy, and the AGENTS rules already treat race as a frontend/backend i18n contract. If mixed expression is needed later, it can be extended to:

```text
Yao title: Form Transformation Middle Stage
Sect equivalent: Foundation Establishment Middle Stage
```

## 5. Suggested Alias Tables

The following are naming suggestions. They can be fine-tuned through config and i18n during implementation.

### 5.1 Daoist / rogue cultivator

Daoists and rogue cultivators keep the existing standard names by default, lowering the cost of understanding for players.

| realm_id | Realm alias | Stage alias |
|---|---|---|
| `QI_REFINEMENT` | Qi Refinement | Early Stage / Middle Stage / Late Stage |
| `FOUNDATION_ESTABLISHMENT` | Foundation Establishment | Early Stage / Middle Stage / Late Stage |
| `CORE_FORMATION` | Core Formation | Early Stage / Middle Stage / Late Stage |
| `NASCENT_SOUL` | Nascent Soul | Early Stage / Middle Stage / Late Stage |

### 5.2 Martial Path

The Martial Path should convey the physical body, sinews and bones, inner force, and a grandmaster feel; it should not directly use xianxia organ terms such as "Qi Sea / Golden Core".

| realm_id | Realm alias | Recommended full stages |
|---|---|---|
| `QI_REFINEMENT` | Body Tempering | Body Tempering, Initial Attainment / Body Tempering, Mid Attainment / Body Tempering, Great Attainment |
| `FOUNDATION_ESTABLISHMENT` | Tendon-Tempering | Tendon-Tempering, Initial Attainment / Tendon-Tempering, Mid Attainment / Tendon-Tempering, Great Attainment |
| `CORE_FORMATION` | Martial Master | Martial Master, Early Realm / Martial Master, Middle Realm / Martial Master, Completion |
| `NASCENT_SOUL` | Martial Saint | Martial Saint, Early Realm / Martial Saint, Middle Realm / Martial Saint, Completion |

Alternatives:

- `QI_REFINEMENT`: Body Refining
- `FOUNDATION_ESTABLISHMENT`: Blood Exchange
- `CORE_FORMATION`: Grandmaster
- `NASCENT_SOUL`: Saint of the Martial Path

The current recommendation is "Body Tempering / Tendon-Tempering / Martial Master / Martial Saint": concise, highly recognizable, and well suited to UI display.

### 5.3 Confucian Path

The Confucian Path should convey study, nurturing the noble spirit, illuminating principle, establishing one's mandate, and the order of sages. Do not copy imperial examination or official ranks directly, or it will be easily confused with the dynasty's official post system.

| realm_id | Realm alias | Recommended full stages |
|---|---|---|
| `QI_REFINEMENT` | Vital Qi Cultivation | Vital Qi Cultivation, Early Realm / Vital Qi Cultivation, Middle Realm / Vital Qi Cultivation, Completion |
| `FOUNDATION_ESTABLISHMENT` | Principle Illumination | Principle Illumination, Early Realm / Principle Illumination, Middle Realm / Principle Illumination, Completion |
| `CORE_FORMATION` | Mandate Establishment | Mandate Establishment, Early Realm / Mandate Establishment, Middle Realm / Mandate Establishment, Completion |
| `NASCENT_SOUL` | Great Scholar | Great Scholar, Early Realm / Great Scholar, Middle Realm / Great Scholar, Completion |

Alternatives:

- `QI_REFINEMENT`: Initiation into Learning
- `FOUNDATION_ESTABLISHMENT`: Self-Cultivation
- `CORE_FORMATION`: Rectifying the Heart
- `NASCENT_SOUL`: Sage

The current recommendation is "Vital Qi Cultivation / Principle Illumination / Mandate Establishment / Great Scholar", because these read more like cultivation tiers and do not overlap directly with mortal imperial examinations or official posts.

### 5.4 Buddhist Path

The Buddhist Path should convey keeping precepts, meditative absorption, attainment levels, compassion, and the golden body. Take care not to make the early titles too powerful.

| realm_id | Realm alias | Recommended full stages |
|---|---|---|
| `QI_REFINEMENT` | Novice Monk | Novice Monk, Early Realm / Novice Monk, Middle Realm / Novice Monk, Completion |
| `FOUNDATION_ESTABLISHMENT` | Monk | Monk, Early Realm / Monk, Middle Realm / Monk, Completion |
| `CORE_FORMATION` | Arhat | Arhat, Early Realm / Arhat, Middle Realm / Arhat, Completion |
| `NASCENT_SOUL` | Bodhisattva | Bodhisattva, Early Realm / Bodhisattva, Middle Realm / Bodhisattva, Completion |

Alternatives:

- `QI_REFINEMENT`: Precept Keeping
- `FOUNDATION_ESTABLISHMENT`: Entering Samadhi
- `CORE_FORMATION`: Golden Body
- `NASCENT_SOUL`: Bodhi

The current recommendation is "Novice Monk / Monk / Arhat / Bodhisattva", which is highly recognizable, but care is needed to keep the religious terminology consistent in translation.

### 5.5 Yao

Yao should convey the path of awakening intelligence, transforming form, the demon core, and becoming a demon king. It is not an orthodoxy but racial cultivation terminology.

| realm_id | Realm alias | Recommended full stages |
|---|---|---|
| `QI_REFINEMENT` | Spirit Awakening | Spirit Awakening Early Stage / Spirit Awakening Middle Stage / Spirit Awakening Late Stage |
| `FOUNDATION_ESTABLISHMENT` | Form Transformation | Form Transformation Early Stage / Form Transformation Middle Stage / Form Transformation Late Stage |
| `CORE_FORMATION` | Demon Core | Demon Core Early Stage / Demon Core Middle Stage / Demon Core Late Stage |
| `NASCENT_SOUL` | Demon King | Demon King Early Stage / Demon King Middle Stage / Demon King Late Stage |

Alternatives:

- `QI_REFINEMENT`: Spirit Kindling
- `FOUNDATION_ESTABLISHMENT`: Form Refining
- `CORE_FORMATION`: Core Condensing
- `NASCENT_SOUL`: Great Yao

The current recommendation is "Spirit Awakening / Form Transformation / Demon Core / Demon King": information-dense and easy for players to understand.

## 6. Data Config Design

### 6.1 Recommended new config file

Suggested addition:

- `static/game_configs/cultivation_alias.csv`

Recommended fields:

```csv
profile_id,realm_id,stage_id,realm_name_id,stage_name_id,full_name_id,sort_order
```

Field meanings:

| Field | Description |
|---|---|
| `profile_id` | Display system ID, e.g. `wu`, `yao` |
| `realm_id` | Standard realm ID |
| `stage_id` | Standard stage ID; may be empty, meaning the row only defines the major realm name |
| `realm_name_id` | i18n key for the major realm display name |
| `stage_name_id` | i18n key for the stage display name |
| `full_name_id` | i18n key for the full display name; allowed to override the `{realm}{stage}` concatenation |
| `sort_order` | Optional; only used for wiki / config display |

### 6.2 Why allow full_name_id

Stage concatenation in different systems does not always fit "realm + early/middle/late".

For example:

- Daoist: "Foundation Establishment Middle Stage" works with concatenation.
- Martial Path: "Martial Master, Middle Realm" has more flavor than "Martial Master Middle Stage".
- Confucian Path: "Vital Qi Cultivation, Completion" fits the Confucian tone better than "Vital Qi Cultivation Late Stage".
- English word order: `Middle Tendon-Tempering` may read more naturally than `Tendon-Tempering Middle Stage`, depending on the phrasing.

Therefore the rule should be:

1. If `full_name_id` exists, prefer the full translation.
2. Otherwise concatenate using `{realm_name}{stage_name}` or a template configured per locale.

### 6.3 i18n key naming suggestions

Suggested new module:

- `static/locales/en-US/modules/cultivation_alias.po`

Key examples:

```po
msgid "cultivation_alias.profile.wu"
msgstr "Martial Path"

msgid "cultivation_alias.wu.realm.qi_refinement"
msgstr "Body Tempering"

msgid "cultivation_alias.wu.stage.early"
msgstr ", Initial Attainment"

msgid "cultivation_alias.wu.full.qi_refinement.early"
msgstr "Body Tempering, Initial Attainment"
```

Notes:

- The `msgid` of a `.po` entry must be a stable key, never display text.
- Display text goes only in `msgstr`.
- `en-US` is the sole and source locale. Maintain entries in the split source file under `modules/` (`LC_MESSAGES/*.po` are merged artifacts), and run `python tools/i18n/build_mo.py` after editing.

## 7. Backend Service Design

### 7.1 New display builder service

Suggested addition:

- `src/systems/cultivation_display.py`

Core functions:

```python
def build_cultivation_display(
    cultivation_progress: CultivationProgress,
    *,
    profile_id: str,
) -> dict[str, Any]:
    ...

def build_avatar_cultivation_display(avatar: Avatar) -> dict[str, Any]:
    ...
```

Return structure:

```json
{
  "profile_id": "wu",
  "profile_name": "Martial Path",
  "realm_id": "FOUNDATION_ESTABLISHMENT",
  "stage_id": "MIDDLE_STAGE",
  "level": 42,
  "canonical_realm_name": "Foundation Establishment",
  "canonical_stage_name": "Middle Stage",
  "canonical_full_name": "Foundation Establishment Middle Stage",
  "display_realm_name": "Tendon-Tempering",
  "display_stage_name": "Mid Attainment",
  "display_full_name": "Tendon-Tempering, Mid Attainment"
}
```

### 7.2 Boundary with `CultivationProgress`

`CultivationProgress` remains responsible only for:

- `level`
- `exp`
- `realm`
- `stage`
- Breakthrough
- Experience
- Realm effects

Do not introduce avatar, race, or orthodoxy into `CultivationProgress`.  
Display aliases are the responsibility of the external presentation/service layer.

### 7.3 `Realm.__str__()` does not become a dynamic alias

`Realm.__str__()` still returns the standard name under the current locale, e.g. "Foundation Establishment".  
This is the global canonical name, not the avatar's display name.

If business logic needs the alias, it must call explicitly:

```python
build_avatar_cultivation_display(avatar)["display_full_name"]
```

## 8. API / DTO Design

### 8.1 Avatar detail

Add structured fields to the avatar detail:

```json
{
  "realm": "Foundation Establishment Middle Stage",
  "realm_id": "FOUNDATION_ESTABLISHMENT",
  "level": 42,
  "cultivation": {
    "profile_id": "wu",
    "profile_name": "Martial Path",
    "realm_id": "FOUNDATION_ESTABLISHMENT",
    "stage_id": "MIDDLE_STAGE",
    "level": 42,
    "canonical_full_name": "Foundation Establishment Middle Stage",
    "display_full_name": "Tendon-Tempering, Mid Attainment"
  }
}
```

Notes:

- `realm` is kept for now, to avoid a big-bang frontend migration.
- New code prefers reading `cultivation.display_full_name`.
- Read `realm_id` / `stage_id` / `level` when filtering, sorting, or passing parameters.

### 8.2 World state and websocket

The map avatar list and tick updates can keep returning `realm` as the standard ID for now:

```json
{
  "realm": "FOUNDATION_ESTABLISHMENT"
}
```

If the frontend needs to show the alias directly on cards, it can be returned incrementally:

```json
{
  "realm": "FOUNDATION_ESTABLISHMENT",
  "cultivation_display": "Tendon-Tempering, Mid Attainment"
}
```

Changing the original `realm` field into an alias is not recommended.

### 8.3 External control API

External agent / Claw integrations need a stable contract:

- Queries may return aliases as auxiliary fields.
- Commands must continue to accept standard IDs.
- The documentation should state clearly that `display_full_name` cannot be used as a command parameter.

Example:

```json
{
  "realm_id": "CORE_FORMATION",
  "display_full_name": "Arhat, Completion",
  "canonical_full_name": "Core Formation Late Stage"
}
```

If an external agent wants to create an item or pick a target realm, it should pass:

```json
{
  "realm": "CORE_FORMATION"
}
```

rather than:

```json
{
  "realm": "Arhat"
}
```

## 9. Frontend Design

### 9.1 Types

Add to `AvatarDetail` in `web/src/types/core.ts`:

```ts
interface CultivationDisplay {
  profile_id: string
  profile_name: string
  realm_id: string
  stage_id: string
  level: number
  canonical_realm_name: string
  canonical_stage_name: string
  canonical_full_name: string
  display_realm_name: string
  display_stage_name: string
  display_full_name: string
}
```

`AvatarDetail`:

```ts
cultivation?: CultivationDisplay
```

### 9.2 Display priority

Frontend display recommendations:

1. If `cultivation.display_full_name` exists: show the alias.
2. If `cultivation.canonical_full_name` exists: it can be used as a tooltip or secondary text.
3. If only the legacy `realm` field exists: use the existing `formatCultivationText`.

Recommended display on the avatar detail page:

```text
Tendon-Tempering, Mid Attainment
Equivalent: Foundation Establishment Middle Stage
```

Compact cards can show only:

```text
Tendon-Tempering, Mid Attainment
```

Filtering, colors, and sorting continue to use `realm_id` or `level`.

### 9.3 Do not grow the frontend alias map further

`web/src/utils/cultivationText.ts` currently maintains an alias map for the standard realms.  
From now on, do not keep stuffing all the Martial, Confucian, Buddhist, and Yao aliases into this map.

Reasons:

- This is a display derivation, not a frontend parsing source of truth.
- The alias set would keep growing.
- The same alias may mean different things in different profiles.

New UI should prefer consuming the structured backend DTO.

## 10. LLM Context Design

The LLM needs both the flavored title and the standard equivalence.  
Recommended context structure:

```json
{
  "cultivation": {
    "display": "Tendon-Tempering, Mid Attainment",
    "canonical": "Foundation Establishment Middle Stage",
    "realm_id": "FOUNDATION_ESTABLISHMENT",
    "stage_id": "MIDDLE_STAGE",
    "profile_id": "wu"
  }
}
```

The prompt can state explicitly:

```text
This character belongs to the Martial Path system. Their current rank is called "Tendon-Tempering, Mid Attainment", equivalent to the standard realm "Foundation Establishment Middle Stage".
Narrative may use "Tendon-Tempering, Mid Attainment", but action parameters, item grades, and target realms must use the standard realm_id.
```

This prevents the LLM from outputting, during action planning:

```json
{"target_realm": "Tendon-Tempering"}
```

and instead it should output:

```json
{"target_realm": "FOUNDATION_ESTABLISHMENT"}
```

## 11. World Info Design

### 11.1 Add a world info entry

Add an entry to `static/game_configs/world_info.csv` explaining the equivalence between rank aliases of different orthodoxies / races.

Suggested entry:

```csv
Realm Aliases,WORLD_INFO_CULTIVATION_ALIAS_TITLE,WORLD_INFO_CULTIVATION_ALIAS_NAME,WORLD_INFO_CULTIVATION_ALIAS_DESC,"The same cultivation ranks have different names in each tradition: Daoists and rogue cultivators use Qi Refinement, Foundation Establishment, Core Formation, and Nascent Soul; martial cultivators use Body Tempering, Tendon-Tempering, Martial Master, and Martial Saint; Confucian cultivators use Vital Qi Cultivation, Principle Illumination, Mandate Establishment, and Great Scholar; Buddhist cultivators use Novice Monk, Monk, Arhat, and Bodhisattva; yao cultivators use Spirit Awakening, Form Transformation, Demon Core, and Demon King. These names map to the same underlying realm sequence; they change narrative and interface wording, but not breakthrough, power, lifespan, item grade, or other rules."
```

### 11.2 Role of the World Info entry

This entry serves three kinds of users at once:

1. Players: understand why avatars of the same level show different titles.
2. LLM: knows, when generating stories, objectives, and nicknames, that aliases are not independent progression lines.
3. External agents: understand the relationship between display name and canonical realm.

### 11.3 Locale sync

Because `world_info.csv` is already read by the frontend and translated via `game_configs_modules/world_info.po` / the frontend locale namespace, adding an entry requires syncing:

- `static/locales/en-US/game_configs_modules/world_info.po`
- Frontend `web/src/locales/en-US/world_info.json`
- Run `python tools/i18n/build_mo.py`
- Cover the related checks in `tests/test_frontend_locales.py` / `tests/test_backend_locales.py`

## 12. Naming and Translation Strategy

Xianxia vocabulary is not ordinary UI text and cannot be handled by word-for-word literal translation alone. The naming needs deliberate design.

### 12.1 Overall strategy

Display names should keep two layers of information at the same time:

1. **Flavored title**: reads to players like a genuine cultivation system.
2. **Standard equivalence**: shows the canonical name or a tooltip when needed, so players know which power level it corresponds to.

Recommended UI:

```text
Tendon-Tempering, Mid Attainment (Foundation Establishment)
```

### 12.2 Naming principles

`en-US` is the source and only locale; prioritize flavor and concision.

Principles:

- Daoist / rogue cultivator keeps the existing standard xianxia names.
- The Martial Path uses wuxia-leaning, body-cultivation vocabulary.
- The Confucian Path uses literary terms such as "Vital Qi Cultivation, Principle Illumination, Mandate Establishment, Great Scholar".
- The Buddhist Path uses widely recognizable Buddhist ranks.
- Yao use common xuanhuan terms such as "Spirit Awakening, Form Transformation, Demon Core, Demon King".

Not recommended:

- Naming Confucian ranks after imperial examination degrees (e.g. Child Student, Licentiate, Provincial Graduate, Metropolitan Graduate), which binds them too tightly to dynasty / official post / imperial examination imagery.
- Calling early Buddhist ranks "Buddha" or "Bodhi"; early titles would be too powerful.
- Making martial full names too long; maps and cards would get crowded.

### 12.3 en-US terminology

English should not mechanically transliterate every term, or readability suffers badly; nor should it translate everything into generic fantasy ranks, or the xianxia flavor is lost. The recommended strategy is a hybrid of "translate the key system terms by meaning + keep necessary terms".

Realms by profile:

| realm_id | `dao` / `sanxiu` | `wu` | `confucianism` | `buddhism` | `yao` |
|---|---|---|---|---|---|
| `QI_REFINEMENT` | Qi Refinement | Body Tempering | Vital Qi Cultivation | Novice Monk | Spirit Awakening |
| `FOUNDATION_ESTABLISHMENT` | Foundation Establishment | Tendon-Tempering | Principle Illumination | Monk | Form Transformation |
| `CORE_FORMATION` | Core Formation | Martial Master | Mandate Establishment | Arhat | Demon Core |
| `NASCENT_SOUL` | Nascent Soul | Martial Saint | Great Scholar | Bodhisattva | Demon King |

Stages:

| stage_id | Standard form (`dao` / `sanxiu` / `yao`) | Attainment form (`wu`) | Realm form (`confucianism` / `buddhism`) |
|---|---|---|---|
| `EARLY_STAGE` | Early Stage | Initial Attainment | Early Realm |
| `MIDDLE_STAGE` | Middle Stage | Mid Attainment | Middle Realm |
| `LATE_STAGE` | Late Stage | Great Attainment | Completion |

English UI should prefer the full configured `full_name_id`, because English word order does not always suit direct concatenation.

Examples:

- `Body Tempering, Initial Attainment`
- `Tendon-Tempering, Mid Attainment`
- `Martial Saint, Completion`
- `Arhat, Middle Realm`

### 12.4 Missing-alias fallback

If an alias text is missing:

1. Fall back to the canonical realm/stage name first.
2. Only fall back to the ID as a last resort.

## 13. Saves and Compatibility

Saves only store:

- `level`
- `exp`
- The existing `realm` / `stage` enum info
- The avatar's `race_id`
- Sect / orthodoxy relations

Not stored:

- `display_realm_name`
- `display_stage_name`
- `display_full_name`
- `profile_name`

Reasons:

- Display names are derived from config and locale.
- When locale text changes, the updated display names should be shown.
- After the alias table is modified later, old saves should automatically use the new display names.

## 14. Testing Strategy

### 14.1 Backend unit tests

Suggested new test:

- `tests/test_cultivation_display.py`

Coverage:

1. The same `level` returns different `display_full_name` under different profiles.
2. `realm_id` / `stage_id` are always standard IDs.
3. Yao avatars prefer the `yao` profile.
4. Human sect members use the profile from `orthodoxy.id`.
5. A missing profile falls back to `dao` or canonical.
6. `CultivationProgress` itself does not depend on avatar / orthodoxy / race.

### 14.2 API tests

Coverage:

1. Avatar detail returns the `cultivation` structure.
2. `realm_id` matches `cultivation.realm_id`.
3. The legacy `realm` field still exists for now.
4. External queries return aliases, but command parameters still require standard IDs.

### 14.3 Action parameter tests

Coverage:

1. `param_options.target_realm.value` is still `Realm.value`.
2. `param_options.target_realm.id` is still `Realm.value`.
3. `can_start("FOUNDATION_ESTABLISHMENT")` still succeeds.
4. `can_start("Tendon-Tempering")` is not required to become the main path.

### 14.4 Frontend tests

Coverage:

1. Avatar detail prefers showing `cultivation.display_full_name`.
2. Tooltip / secondary text can show `canonical_full_name`.
3. Falls back to the existing `formatCultivationText` when `cultivation` is missing.
4. Type definitions do not use `any`.

### 14.5 i18n tests

Coverage:

1. The `en-US` `cultivation_alias.po` keys are complete.
2. The new world info entry exists in the frontend locale namespace.
3. The backend can read it after compiling `.mo`.

## 15. Recommended Rollout Order

### Phase 1: Structured display

1. Add `cultivation_alias.csv`.
2. Add the `en-US` entries to `cultivation_alias.po`.
3. Add `src/systems/cultivation_display.py`.
4. Add the `cultivation` structure to avatar detail.
5. Show the alias on the avatar detail page, keeping canonical as secondary text.
6. Add the world info entry explaining the equivalence.
7. Add backend display tests and frontend detail tests.

### Phase 2: Narrative integration

1. Add the `cultivation` structure to the AI decision context.
2. Story event / roleplay / nickname / long-term objective prompts can use display + canonical.
3. Avatar cultivation in event text prefers display.
4. LLM prompts state explicitly that "action parameters use realm_id".

### Phase 3: Global display entry points

1. Map cards / hover use display.
2. Relation lists use display.
3. Rankings show display, but grouping still follows `Realm`.
4. The frontend gradually reduces new dependencies on `formatCultivationText`.
5. External API docs add display/canonical semantics.

## 16. Risks and Mitigations

### 16.1 Risk: display names misused as logical values

Mitigations:

- DTOs return both `realm_id` and `display_full_name`.
- Command parameter docs state clearly that only IDs are accepted.
- Tests ensure `param_options.value` is an ID.

### 16.2 Risk: LLM outputs an alias and the action fails

Mitigations:

- The LLM context provides both display and realm_id.
- The prompt states explicitly that action parameters must use `realm_id`.
- The action layer does not expand natural-language alias parsing as a main path.

### 16.3 Risk: inconsistent naming style

Mitigations:

- Use `full_name_id`; do not rely heavily on concatenation.
- Maintain a dedicated terminology table.

### 16.4 Risk: the frontend keeps guessing realms from strings

Mitigations:

- Add the structured `cultivation` type.
- New UI prefers reading structured fields.
- `formatCultivationText` serves only as a fallback for legacy data.

### 16.5 Risk: conflict between yao and sect orthodoxy

Mitigations:

- Phase one makes it explicit that yao takes priority.
- If needed later, the UI can show "yao title + sect equivalent".

## 17. Development Rules Summary

1. Add display aliases without changing `Realm` enum values.
2. Do not make `Realm.__str__()` depend on the avatar.
3. Aliases do not go into saves.
4. Action parameters keep using `Realm.value`.
5. The API adds structured fields; do not change the legacy `realm` field into an alias.
6. LLM context provides both display and canonical.
7. World Info must explain the alias equivalence.
8. Alias naming and translation should follow the xianxia style, not mechanical literal translation.
9. The frontend does not grow the realm alias map further.
10. Tests must cover "the alias display changes but the underlying ID does not".
