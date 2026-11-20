# Background NPC / Mortal Scene System Design

This document describes the phase-one design of "background NPCs". The NPCs here are not `Avatar`s, nor long-lived world entities; they are nameless mortal portraits and pre-written scene events used to fill the world with the bustle of everyday life.

The phase-one goal is to use a low-cost, config-driven approach to bring echoes of mortal life into scenes such as cities, ports, mountain ranges, the foot of sect mountains, government offices, and markets, while letting Avatars of different identities encounter different mortal vignettes. The system does not call an online LLM, does not change world state, and does not introduce an NPC lifecycle.

## 1. Goals

The background NPC system solves three problems:

1. The world should not consist only of slow LLM interactions between Avatars; it should also have low-cost mortal background events.
2. An Avatar's race, alignment, realm, sect identity, official post, etc. should be "seen" by the mortal world, without changing any numbers.
3. Some Avatar minor events and action results can carry a mortal reaction, strengthening the narrative sense of cultivators towering over the mortal world.

The standard phase-one experience is:

- Cities have nameless occupational silhouettes such as herb vendors, medicine shop assistants, teahouse storytellers, and street patrol runners.
- Ports have nameless occupational silhouettes such as ship captains, sailors, tide guides, and port tax collectors.
- The foot of sect mountains has nameless occupational silhouettes such as sect gate children, outer sect servants, immortal-seeking parents, and buyers.
- Yao, evil-path cultivators, high-realm cultivators, officials, sect disciples, etc. can meet different mortal reactions.
- Background NPCs do not create relations, do not enter save files, and do not become entities you can talk to.

## 2. Design Principles

### 2.1 Background NPCs are not Avatars

In phase one, background NPCs do not enter:

1. `AvatarManager`
2. The action system
3. The relation system
4. The sect membership system
5. Entity lifecycles such as death, age, inventory, realm, and location

They exist only as config material in the form of "portrait + pre-written event template".

### 2.2 All background NPCs are nameless

Phase one forbids giving background NPCs specific personal names.

Recommended:

- `herb vendor`
- `old man at the tea shed`
- `post courier`
- `sect gate child`
- `ship captain`
- `night watchman`
- `black-market broker`
- `several dock porters`
- `an aged herb gatherer`
- `the boy keeping watch outside the sect gate`

Not recommended:

- `Old Chen`
- `Bookkeeper Zhao`
- `Shopkeeper Liu`
- `Captain So-and-so`

The reason is that phase one does not support repeat appearances. Repeated occupational identities are reasonable, but repeated personal names would make players think the same person keeps showing up.

### 2.3 Background only, no state changes

Phase-one background NPC events should not directly change:

1. Avatar attributes, resources, relations, or action plans
2. City population, economy, goods, or public order
3. Sect income, relations, wars, or inventory
4. The court, government offices, the map, POIs, opportunities, hidden domains, or other world state

All events only produce an `Event`.

Config fields expressing future effects may be reserved, but the phase-one loader / service does not execute them.

### 2.4 No online LLM calls

All event text uses pre-written templates. At runtime the system only does:

1. Condition filtering
2. Weighted sampling
3. Variable substitution
4. `Event` generation

During development, AI may be used to batch-generate candidate text, but content that ships in the game must live in config and locale source files.

### 2.5 Portraits and events are separate

One background NPC portrait can be bound to multiple different events. The portrait decides "who appears"; the event decides "which scene plays out when they appear".

For example:

- `herb_vendor` herb vendor
  - An argument over goods inspection at the city market
  - The shopkeeper puts away mortal-grade herbs when an Avatar buys medicine
  - The stallholder lowers their voice when a yao passes by
  - Only jade-boxed spirit materials are shown when a high-realm cultivator asks about prices

Portraits hold no runtime state, and events make no promise that the same NPC will appear again.

## 3. Non-Goals

Phase one explicitly does not do the following:

1. No NPC repeat appearances.
2. No NPCs as conversation targets.
3. No NPC relations, favor, or grudges.
4. No NPC long-term memory.
5. No NPC roster.
6. No NPC population simulation inside cities or sects.
7. No numeric effects on the economy, public order, population, sect income, etc.
8. Background NPCs are not added to the list of objects observable by Avatar AI.
9. Background NPCs do not enter save files.
10. No new player quests, navigation, POIs, or clickable targets.

## 4. Event Types

Phase one supports three trigger semantics.

### 4.1 `region_tick`

Background events that happen naturally in a region, not bound to a specific Avatar.

Example:

```text
In the city, a herb vendor and an herb gatherer argued for half a day over the age of a bundle of herbs; only after the medicine shop assistant fetched the shopkeeper to inspect it did the crowd of onlookers slowly disperse.
```

Event semantics:

- `related_avatars=None`
- `related_sects` optional
- `is_major=False`
- `is_story=False`
- `event_type="background_npc"`

### 4.2 `avatar_witness`

A mortal vignette an Avatar sees while staying in or passing through a place, or when meeting identity conditions.

Example:

```text
As {avatar_name} passed the medicine shop, the shop assistant wiped the counter again and again, never daring to hurry them.
```

Event semantics:

- `related_avatars=[avatar.id]`
- `is_major=False`
- `is_story=False`
- `event_type="background_npc"`

### 4.3 `action_echo`

A mortal reaction appended after an Avatar completes certain actions; it does not change the action's resolution.

Example:

```text
After {avatar_name} left, the clinic physician took the remaining blood-staunching powder to the gruel shed, and a few refugees murmured their thanks under the eaves.
```

Actions suitable for early integration:

- `Buy`
- `Sell`
- `Govern`
- `HelpPeople`
- `PlunderPeople`
- `EatMortals`
- `DevourPeople`
- `SectMission`
- `MoveToRegion`

Event semantics:

- `related_avatars=[avatar.id]`
- `is_major=False`
- `is_story=False`
- `event_type="background_npc"`

## 5. Config Overview

Phase one recommends three config tables:

1. `static/game_configs/background_npc_profile.csv`
2. `static/game_configs/background_npc_event.csv`
3. `static/game_configs/background_npc_region_binding.csv`

Of these:

- The profile table defines nameless occupational portraits.
- The event table defines the multiple events a portrait can trigger.
- The region binding table binds map regions to scene tags, so events do not hard-code specific regions.

All user-visible text should point to locale entries via `*_id`. The CSV may keep a remark column for maintenance, but the runtime should not depend on the remark column as the source of truth for user-visible text.

Suggested new locale source files:

```text
static/locales/en-US/game_configs_modules/background_npc_profile.po
static/locales/en-US/game_configs_modules/background_npc_event.po
```

`en-US` is the sole and source locale; maintain entries in these split source files, and run `python tools/i18n/build_mo.py` after editing them (`LC_MESSAGES/*.po` are merged artifacts).

## 6. Profile Table

`background_npc_profile.csv` defines background NPC portraits.

Suggested fields:

```csv
id,profile_key,role_label_id,category,default_scene_tags,comment
1,herb_vendor,BACKGROUND_NPC_ROLE_HERB_VENDOR,city_market,city_market|medicine,herb vendor
2,storyteller,BACKGROUND_NPC_ROLE_STORYTELLER,city_market,city_market|rumor|teahouse,teahouse storyteller
3,tide_guide,BACKGROUND_NPC_ROLE_TIDE_GUIDE,port,port|tide|sea_trade,tide guide
4,sect_gate_child,BACKGROUND_NPC_ROLE_SECT_GATE_CHILD,sect_edge,sect_edge|pilgrimage,sect gate child
```

Field descriptions:

1. `id`: numeric ID, used only for config references.
2. `profile_key`: stable key; business code, tests, and tools should prefer it.
3. `role_label_id`: i18n key for the occupational title.
4. `category`: coarse portrait category, e.g. `city_market`, `port`, `mountain_frontier`, `sect_edge`, `official_order`, `black_market`.
5. `default_scene_tags`: scene tags the portrait naturally fits, separated by `|`.
6. `comment`: maintenance remark, not used as user-visible text at runtime.

The portrait layer only describes "who this kind of person is". Do not write event text in the profile.

### 6.1 Portrait naming conventions

`profile_key` uses English snake_case; avoid non-English keys:

- `herb_vendor`
- `inn_keeper`
- `yamen_clerk`
- `dock_laborer`
- `mountain_hunter`
- `sect_errand_servant`

`role_label_id` uses stable English keys:

- `BACKGROUND_NPC_ROLE_HERB_VENDOR`
- `BACKGROUND_NPC_ROLE_INN_KEEPER`
- `BACKGROUND_NPC_ROLE_YAMEN_CLERK`

Corresponding en-US `.po`:

```po
msgid "BACKGROUND_NPC_ROLE_HERB_VENDOR"
msgstr "herb vendor"
```

## 7. Event Table

`background_npc_event.csv` defines concrete events. One `profile_key` can be bound to multiple events.

Suggested fields:

```csv
id,event_key,profile_key,trigger_kind,region_types,required_tags,excluded_tags,map_ids,avatar_filters,action_keys,weight,cooldown_months,max_per_month,text_id,comment
1,herb_vendor_market_argument,herb_vendor,region_tick,city,city_market|medicine,, , , ,1.0,24,1,BACKGROUND_NPC_EVENT_HERB_VENDOR_MARKET_ARGUMENT,herb age dispute
2,herb_vendor_avatar_buy_echo,herb_vendor,action_echo,city,medicine,, , ,Buy,1.0,12,1,BACKGROUND_NPC_EVENT_HERB_VENDOR_AVATAR_BUY_ECHO,medicine purchase echo
3,market_reacts_to_yao,herb_vendor,avatar_witness,city,city_market,, ,race=yao, ,1.0,12,1,BACKGROUND_NPC_EVENT_MARKET_REACTS_TO_YAO,yao passing through the market
```

Field descriptions:

1. `id`: numeric ID.
2. `event_key`: stable event key.
3. `profile_key`: references `background_npc_profile.csv`.
4. `trigger_kind`: `region_tick`, `avatar_witness`, `action_echo`.
5. `region_types`: coarse filter on region type, separated by `|`; valid values follow the runtime region type, e.g. `city`, `sect`, `normal`, `cultivate`.
6. `required_tags`: scene tags that must match, separated by `|`.
7. `excluded_tags`: excluded tags, separated by `|`.
8. `map_ids`: restrict to maps, separated by `|`; empty means all maps.
9. `avatar_filters`: Avatar identity conditions; empty means unrestricted.
10. `action_keys`: used by `action_echo`; allows multiple action keys separated by `|`; empty for other trigger types.
11. `weight`: weight.
12. `cooldown_months`: cooldown in months for the same `event_key`.
13. `max_per_month`: maximum occurrences of the same event per month, usually `1`.
14. `text_id`: i18n key for the event text.
15. `comment`: maintenance remark.

### 7.1 Text i18n

Event text is not written into the runtime fields of the main CSV; it all lives in locale `.po` files.

Example:

```po
#. background_npc_event.csv: herb age dispute
msgid "BACKGROUND_NPC_EVENT_HERB_VENDOR_MARKET_ARGUMENT"
msgstr "In the city, a herb vendor and an herb gatherer argued for half a day over the age of a bundle of herbs; only after the medicine shop assistant fetched the shopkeeper to inspect it did the crowd of onlookers slowly disperse."

#. background_npc_event.csv: medicine purchase echo
msgid "BACKGROUND_NPC_EVENT_HERB_VENDOR_AVATAR_BUY_ECHO"
msgstr "While {avatar_name} chose spirit materials, the medicine shop assistant wiped the counter again and again, never daring to hurry them."
```

`msgid` must be a stable English key; the display text goes in `msgstr`.

### 7.2 Available template variables

Phase one should support only a small set of stable variables:

1. `{avatar_name}`
2. `{region_name}`
3. `{sect_name}`
4. `{dynasty_title}`
5. `{npc_role}`

Variable sources:

- `{avatar_name}`: the current Avatar.
- `{region_name}`: display name of the triggering region, preferring the name after the map's `region_overrides`.
- `{sect_name}`: name of the sect associated with the region or Avatar; if there is no value, the event should not be selected unless its text does not use this variable.
- `{dynasty_title}`: title of the current dynasty; if there is no dynasty, the event should not be selected unless its text does not use this variable.
- `{npc_role}`: localized result of `role_label_id`.

Phase one should not allow arbitrary Python expressions or complex conditional substitution.

## 8. Region Binding Table

`background_npc_region_binding.csv` maps specific maps and regions to scene tags.

Recommended fields:

```csv
id,map_id,region_id,scene_tags,comment
1,classic,301,city_market|medicine|official_order,Qingyun City
2,classic,304,port|river_trade|sea_trade,Canglan City
3,island_seas,305,port|sea_trade|shipyard,island port city
4,mountain_frontier,305,mountain_pass|mining|frontier,mountain frontier city
```

Field descriptions:

1. `id`: numeric ID.
2. `map_id`: map ID; must correspond to `static/game_configs/maps/<map_id>`.
3. `region_id`: region ID; must exist in the corresponding map's `region_rows` or region config.
4. `scene_tags`: scene tags the region has.
5. `comment`: maintenance remark.

This way events do not need to be hard-bound to a `region_id`. The same event can appear in every city tagged `medicine`, or be restricted with `map_ids` to appear only on island or mountain maps.

### 8.1 Default tags

If a region has no binding record, basic tags can be derived from the region type:

- `city` -> `city`
- `sect` -> `sect|sect_edge`
- `normal` -> `wild`
- `cultivate` -> `cultivate`

But fine-grained tags must be configured explicitly, for example:

- `port`
- `medicine`
- `black_market`
- `mountain_pass`
- `mining`
- `official_order`
- `teahouse`
- `pilgrimage`

## 9. Avatar Filter

`avatar_filters` lets Avatars of different identities encounter different events.

Phase one should use simple `;`-separated key-value conditions and not implement complex expressions.

Examples:

```text
race=yao
alignment=evil
sect=any
sect=none
official=any
official=none
realm_min=FOUNDATION_ESTABLISHMENT
realm_max=GOLDEN_CORE
```

Multiple conditions mean all must be satisfied:

```text
race=yao;alignment=evil
sect=any;realm_min=FOUNDATION_ESTABLISHMENT
```

Suggested supported fields:

1. `race`
2. `alignment`
3. `sect`
4. `official`
5. `realm_min`
6. `realm_max`

Phase one should not support `or`, parentheses, comparison expressions, or scripted conditions.

## 10. Triggering and Rate Limiting

Phase one should add a dedicated config section at `static/config.yml -> world.background_npc`, at the same level as existing world event settings such as `random_minor_event_prob` and `fortune_probability`.

Recommended config:

```yaml
world:
  background_npc:
    enabled: true
    region_tick_prob: 0.25
    avatar_witness_prob: 0.03
    action_echo_prob: 0.15
    max_region_tick_per_month: 1
    max_avatar_witness_per_month: 2
    max_action_echo_per_month: 2
```

Suggested rate-limiting principles:

1. At most 1 `region_tick` per month.
2. At most 2 `avatar_witness` per month.
3. At most 2 `action_echo` per month.
4. The same `event_key` respects `cooldown_months`.
5. `avatar_witness` events for the same Avatar should not be too frequent; the runtime should additionally track a monthly cooldown keyed by `avatar_id + event_key`.

Cooldown state can be in-memory runtime state and does not go into save files. It is acceptable for cooldowns to reset after a load or restart, because phase-one events do not affect state.

## 11. Simulator Integration Suggestions

Suggested new package:

```text
src/systems/background_npc/
  __init__.py
  loader.py
  models.py
  service.py
```

The simulator phase can sit near `random_minor_events`; semantically it belongs to the low-cost minor event layer.

Candidate integration:

```python
async def phase_background_npc_events(world, living_avatars) -> list[Event]:
    return BackgroundNpcService.try_create_monthly_events(world, living_avatars)
```

Suggested phase placement:

1. After action execution.
2. Near `random_minor_events`.
3. Before `finalize_step()`, which stores events centrally.

Do not spread logic into `src/server/main.py`.

## 12. Boundary with Random Minor Event

The existing `random_minor_event` targets Avatar minor events and currently calls an online LLM to generate text.

The boundary between the background NPC system and it is:

1. `random_minor_event`: micro events about an avatar itself or between avatars.
2. `background_npc`: mortal background, regional bustle, and Avatars being seen by the mortal world.

Both produce ordinary minor events, but:

- `random_minor_event` can change relations.
- `background_npc` does not change any state.
- `random_minor_event` text is generated by the LLM.
- `background_npc` text comes from pre-written i18n templates.

## 13. Relationship with the Event System

Background NPC events uniformly use:

```python
Event(
    month_stamp=world.month_stamp,
    content=rendered_text,
    related_avatars=...,
    related_sects=...,
    is_major=False,
    is_story=False,
    event_type="background_npc",
)
```

Display policy:

1. `region_tick` enters the main event stream but not any Avatar's personal event panel.
2. `avatar_witness` enters the main event stream and the corresponding Avatar's personal event panel.
3. `action_echo` enters the main event stream and the corresponding Avatar's personal event panel.

Do not use `is_story=True`. Background NPC events are not LLM-expanded story text.

## 14. Content Writing Guidelines

### 14.1 Recommended style

The value of background NPCs is a low-fidelity mortal perspective.

Recommended:

- Describe the aftermath; do not explain the truth.
- Write about misreadings, rumors, onlooking, fear, awe, trade, and order.
- Let mortals reflect the social echo of cultivators' actions.
- Use nameless identities and group terms.

Example:

```text
A teahouse storyteller claimed an immortal estate had surfaced in the eastern sea; the listeners cheered, while the bookkeeper only noted three more pots of tea sold.
```

### 14.2 Things to avoid

Avoid:

1. Naming NPCs.
2. Promising that an NPC will appear again in the future.
3. Having mortals accurately explain high-level cultivation truths.
4. Directly generating quests, hidden domains, opportunities, or POIs in events.
5. Writing outcomes that imply state has changed, e.g. "From then on, the price of rice in the city fell."
6. Writing sentences that require follow-up tracking, e.g. "He quietly took note of this; one day he would surely repay it."

## 15. Suggested First Content Packs

Phase one can start with six content packs, each with 8 to 12 events.

### 15.1 City streets

Portraits:

- Herb vendor
- Medicine shop keeper
- Innkeeper
- Teahouse storyteller
- Street patrol runner
- Clinic physician
- Pawnshop appraiser
- Materials broker

### 15.2 Port and islands

Portraits:

- Ship captain
- Sailor
- Fisherman
- Sea goods peddler
- Tide guide
- Pearl diver
- Chart peddler
- Port tax collector

### 15.3 Mountain frontier

Portraits:

- Mountain pass guard
- Mine foreman
- Mine laborer
- Mountain hunter
- Gorge river boatman
- Post station groom
- Ginseng gatherer
- Mine survivor

### 15.4 Foot of the sect mountain

Portraits:

- Outer sect servant
- Sect gate child
- Medicine field farmer
- Spirit beast garden keeper
- Alchemy room fireworker
- Scripture pavilion copyist
- Tenant farmer at the mountain foot
- Immortal-seeking parent
- Buyer

### 15.5 Government and court

Portraits:

- County magistrate
- Prefect
- Tax collector
- Notice crier
- Granary steward
- Private secretary
- Night watchman
- Courier officer
- Retainer of the National Preceptor

### 15.6 Black market and bazaar

Portraits:

- Black-market broker
- Bazaar stallholder
- Goods appraiser
- Consignment house steward
- Shop guard
- Secondhand goods dealer
- Spirit materials broker

## 16. Testing Suggestions

The phase-one implementation should add the following tests:

1. The loader can read profile / event / region binding.
2. One profile can be bound to multiple events.
3. Filtering by `region_types`, `required_tags`, `excluded_tags`, and `map_ids` is correct.
4. `avatar_filters` takes effect for race / alignment / sect / official / realm.
5. `region_tick` events do not carry `related_avatars`.
6. `avatar_witness` / `action_echo` events carry `related_avatars=[avatar.id]`.
7. All generated events have `is_major=False`, `is_story=False`, `event_type="background_npc"`.
8. Rate limiting and cooldowns take effect.
9. Text is rendered via `text_id`, with a controlled fallback when untranslated.
10. `map_id + region_id` in the region binding passes official map validation.

If you change official map bindings, at minimum run:

```bash
python tools/map_presets/validate_presets.py
```

If you add locale source files or entries, run:

```bash
python tools/i18n/build_mo.py
pytest tests/test_backend_locales.py
```

## 17. Phase-Two Extension Points

After phase one is complete, phase two can pick a few high-frequency portraits and turn them into lightweight NPCs that "can appear again", but phase two should not contaminate the phase-one model in reverse.

Possible directions:

1. Upgrade a few profiles into persistable `named_mortal_npc`.
2. Allow conversations with some NPCs in roleplay mode.
3. Have conversation summaries land as events, while raw chat logs do not enter the long-term event stream.
4. Maintain a small number of local resident NPCs for specific cities.

All of these are future designs. Phase one only does nameless, one-off, pre-written, stateless mortal scenes.
