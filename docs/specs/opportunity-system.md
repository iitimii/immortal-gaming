# Opportunity System Design Notes

This document describes the phase-one design of the "opportunity" system. Opportunity differs from the existing `fortune` encounter: `fortune` is a world event that is resolved immediately after a monthly random hit; an opportunity first generates a time-limited sense bound to a single person, and is only resolved later when the avatar moves to or approaches the target.

The current design goal is to make the core experience solid first: no new actions, no quest navigation, no complex tiered rewards, no direct breakthroughs.

## 1. Goals

The opportunity system aims to express the xianxia narrative of "the pull of fate":

1. An avatar occasionally has a sudden flash of insight, sensing that some person or place is tied to their own fate.
2. The sense is not an explicit quest, nor system navigation; it is just a vague clue.
3. Whether and how the avatar pursues it is left to the existing AI decision-making.
4. If the avatar reaches the target place or approaches the target person within the time limit, resolution is triggered.
5. Resolution may yield a treasure, yield a boon, return empty-handed, or encounter danger leading to injury or even death.

## 2. Boundaries with Existing Systems

### 2.1 Difference from fortune

The existing `fortune` lives in `src/systems/fortune.py`, with the semantics "triggered this month, resolved this month".

Opportunity does not reuse those semantics:

- `fortune`: an instant encounter; once triggered, it immediately grants equipment, techniques, cultivation, spirit stones, and other results.
- `opportunity`: a time-limited clue; it first enters an active state, and is resolved later when the avatar's movement hits the target.

Therefore opportunity should have its own probability, configuration, state, and story type, and should not keep being squeezed into `fortune_probability` or `StoryEventKind.WORLD_FORTUNE`.

### 2.2 Difference from hidden domain

A hidden domain is world-level or gathering-type content, usually opened by the system and attracting multiple participants.

An opportunity is a single avatar's private fate:

- Not publicly displayed as a world entrance.
- Not a standalone frontend section.
- Multiple avatars are not allowed to share the same opportunity state.

### 2.3 Relationship with the action system

Phase one of opportunity adds no new actions.

Pursuing an opportunity only reuses existing actions:

- `MoveToDirection`
- `MoveToRegion`
- `MoveToAvatar`

The system does not provide new actions such as `SearchOpportunity` or `FollowOpportunity`.

## 3. Non-goals

Phase one explicitly does not include the following:

1. No new dedicated opportunity-pursuit action.
2. No new frontend opportunity section.
3. No coordinate-based opportunities.
4. No direction-type targets; direction can only be part of the vague sense text.
5. No direct breakthrough rewards.
6. No two-level ordinary success / great success judgment.
7. No complex risk forecasting.
8. Do not provide `suggested_search`, `risk_hint`, recommended actions, or real target IDs in the AI context.
9. Do not make opportunities into clickable quest navigation.

## 4. Core Model

An opportunity is a time-limited piece of world state bound to a single avatar.

Suggest adding a manager or equivalent service to maintain active opportunities, for example:

- `world.opportunity_manager`
- or `world.active_opportunities`

The same avatar can have at most one active opportunity at a time.

Suggested internal record structure:

```python
{
    "id": "...",
    "avatar_id": "...",
    "target_type": "region|avatar",
    "target_id": "...",
    "hint_text": "...",
    "created_month": 1234,
    "expires_month": 1294,
}
```

Where:

- `target_type` only allows `region` or `avatar`.
- `target_id` stores the real region id or avatar id.
- `hint_text` is the vague text shown to the avatar and the event system.
- `created_month` is used to avoid triggering in the same month it is generated.
- `expires_month` is used for expiry cleanup.

If reward profiles or story archetypes need to be extended in the future, fields can be appended to this record, but phase one does not require complicating it in advance.

## 5. Target Types

### 5.1 Region target

A region target means the opportunity lies in some region.

Hit condition:

- The avatar's current tile has a region;
- and `avatar.tile.region.id == opportunity.target_id`;
- and `current_month > created_month`.

Entering any tile of the target region triggers it; exact coordinates are not required.

Generation constraints:

- Do not select wilderness `-1`.
- Do not select the region the avatar is currently in.
- Do not select a region that does not exist.
- Regions that are usually not enterable, such as enemy sect headquarters, should be filtered carefully, unless high-risk opportunities are explicitly designed later.

### 5.2 Avatar target

An avatar target means the opportunity is tied to a specific avatar.

Hit condition:

- The target avatar still exists;
- the target avatar is not dead;
- the target enters the owner avatar's observation range;
- and `current_month > created_month`.

Same tile is not required.

Subsequent movement or breakthroughs of the target avatar do not affect the opportunity. After the target dies, the opportunity dissipates.

There is currently no renaming mechanism, so no special rule is needed for renaming; if renaming is added in the future, avatar id is still used internally.

## 6. Hint Text

Hint text only expresses the avatar's subjective sense and provides no system suggestion.

The text is allowed to contain:

- A rough direction;
- vague terrain;
- vague personal characteristics;
- vague karmic imagery;
- a sense of time limit.

The text is not allowed to contain:

- Real target IDs;
- explicit recommended actions;
- action names such as `MoveToDirection` / `MoveToRegion` / `MoveToAvatar`;
- system instructions like "you should go to...";
- risk level hints.

Recommended forms:

```text
So-and-so had a sudden flash of insight, faintly sensing a thread of opportunity tied to somewhere among the marshes to the southeast.
```

```text
So-and-so felt a stir in the heart, as if a thread of opportunity were tied to a certain Core Formation sword cultivator to the north.
```

```text
So-and-so has repeatedly dreamed of a broken bell of late, as if an opportunity lay within an ancient city to the west.
```

The AI context should likewise only expose this kind of natural language, for example:

```text
Opportunity sense: Of late the mind has stirred now and then, as if a thread of opportunity were tied to a certain Core Formation sword cultivator to the north. This sense may last a little over three more years.
```

Do not additionally provide `suggested_search` or `risk_hint`.

## 7. Generation Rules

### 7.1 Trigger timing

Opportunity generation can be placed in the monthly world event phase, similar to fortune / misfortune, but with its own probability.

Before generation, check:

1. The avatar is alive.
2. The avatar can trigger world events.
3. The avatar currently has no active opportunity.
4. The avatar is not in an opportunity cooldown.
5. The random probability hits.

### 7.2 Configuration suggestion

Suggested addition to `static/config.yml`:

```yaml
world:
  opportunity:
    probability: 0.001
    duration_months: 60
    cooldown_months_after_dissipated: 12
    cooldown_months_after_resolved: 60
    target_weights:
      region: 70
      avatar: 30
    outcome_weights:
      equipment: 35
      boon: 35
      empty: 20
      injury: 10
```

These fields are built-in static balance configuration for the version and should live in `static/config.yml`; they are not user settings or `RunConfig`.

### 7.3 Probability modifiers

Opportunity trigger probability should be independent of `fortune_probability`.

Suggest adding an effect field:

- `extra_opportunity_probability`

This field modifies the opportunity generation probability.

Luck, goldfinger, persona, etc. can provide this field through the existing effect system. Whether luck additionally derives an opportunity probability can be decided at implementation time according to balance needs, but naming should not reuse `extra_fortune_probability` as the sole entry point for opportunity.

Phase one does not yet add complex success rate, danger rate, or outcome weight effects, to avoid diverging too early.

## 8. AI Decision Context

When an avatar has an active opportunity, the AI decision context should include the sense.

Recommended to expose it only as natural language:

```text
Opportunity sense: So-and-so had a sudden flash of insight, faintly sensing a thread of opportunity tied to somewhere among the marshes to the southeast. This sense may last about four more years.
```

Exposing structured walkthrough fields is not recommended.

Structured fields may be used internally to manage state, but content given to the LLM should keep the "avatar's subjective sense" semantics.

The influence of persona on pursuit behavior falls into two categories:

1. Numeric influence: modify trigger probability through effects.
2. Behavioral influence: reflect a tendency to chase or avoid opportunities in the persona / goldfinger narrative hints.

For example:

- An adventurous personality can state in its behavior hint that it is "more willing to chase unknown opportunities".
- A cautious personality can state that it "does not lightly take risks for a vague opportunity".

These behavioral influences are left to LLM decision-making; no hardcoded action selection is done.

## 9. Detection and Cleanup

### 9.1 Hit detection

Hit detection is placed after action execution.

Reasons:

- After `MoveToDirection` moves into the target region in the current month, it can trigger.
- After `MoveToRegion` reaches the target region, it can trigger.
- After `MoveToAvatar` or natural movement approaches the target, it can trigger.
- Avoids inexplicable resolution before actions.

Detection should skip opportunities from their generation month, i.e. no trigger when `current_month <= created_month`.

### 9.2 Expiry cleanup

When `current_month >= expires_month`, the opportunity dissipates.

After dissipating:

- Clear the active opportunity.
- Record the cooldown.
- Generate an ordinary event.

Recommended event:

```text
The faint sense of opportunity in So-and-so's heart gradually faded; in the end it was never found.
```

### 9.3 Target invalidation

When the target becomes invalid, the opportunity dissipates.

Region target invalidation:

- The target region does not exist.

Avatar target invalidation:

- The target avatar does not exist;
- the target avatar is dead.

Recommended event:

```text
The faint sense of opportunity in So-and-so's heart was abruptly severed; in the end there was nowhere to seek it.
```

### 9.4 Owner death

When the opportunity owner dies, clear the active opportunity.

An additional dissipation event is not required; the death event itself is enough to express the major fact.

## 10. Resolution Outcomes

Phase one outcomes include only four kinds:

- `equipment`
- `boon`
- `empty`
- `injury`

Death is not a separate outcome, but a result that naturally follows from `injury` reducing HP.

### 10.1 Equipment

Equipment reward rules:

1. The reward equipment grade is the avatar's current realm +1 rank.
2. Capped at the highest realm.
3. No +2 rank.
4. No two-level ordinary success / great success judgment.
5. Equipment types include weapon and auxiliary.
6. Prefer filling the avatar's weak spots:
   - When there is no weapon or the weapon is below the current realm, increase the weapon weight.
   - When there is no auxiliary or the auxiliary is below the current realm, increase the auxiliary weight.
   - When neither is lacking, it can be random or converted to a boon.
7. When obtaining equipment, reuse the existing item exchange logic to avoid silently overwriting existing equipment.

Recommended event:

```text
So-and-so followed the opportunity and obtained an ancient cultivator's relic: {item_name}.
```

### 10.2 Boon

Great boons should preferentially reuse the existing effect system, without creating a parallel attribute system.

Suggest driving boons through config tables rather than hardcoding the bonus rules in business code.

Optional config table fields:

```csv
id,effects,duration_months,weight,min_realm,max_realm,title_id,desc_id
```

Example:

```csv
1,"{extra_luck: 1}",0,10,QI_REFINEMENT,NASCENT_SOUL,...
2,"{extra_max_lifespan: 10}",0,10,QI_REFINEMENT,NASCENT_SOUL,...
3,"{extra_respire_exp_multiplier: 0.5}",60,10,QI_REFINEMENT,NASCENT_SOUL,...
4,"{extra_battle_strength_points: 2}",60,10,QI_REFINEMENT,NASCENT_SOUL,...
```

Where:

- `duration_months = 0` means a permanent effect, written into `persistent_effects`.
- `duration_months > 0` means a temporary effect, written into `temporary_effects`.

After adding effects, the avatar's effects must be recalculated.

Recommended event:

```text
So-and-so followed the opportunity and gained insight; their qi was tempered and refined, gaining a new boon.
```

### 10.3 Empty

Nothing happening means the avatar found the source of the sense, but the opportunity had already dissipated or never came true.

Recommended event:

```text
So-and-so followed the sense, but only found the spiritual trace already gone, and in the end gained nothing.
```

This result is still treated as resolved: clear the active opportunity and enter the resolved cooldown.

### 10.4 Injury

Injury means the avatar encountered danger while pursuing the opportunity.

Damage is suggested to be calculated as a percentage of max HP, to avoid fixed values becoming unbalanced across realms.

If HP after deduction is less than or equal to 0, handle it via the existing death flow. Death does not need a separate outcome.

Recommended event:

```text
So-and-so followed the opportunity, but suffered backlash from lingering danger and was injured for {damage} HP.
```

If death:

```text
So-and-so followed the opportunity, but suffered backlash from lingering danger and perished.
```

## 11. Event Semantics

### 11.1 Sense event

When an active opportunity is generated, write an ordinary factual event.

Suggested:

- `is_major=False`
- `is_story=False`
- `related_avatars=[owner.id]`

### 11.2 Dissipation event

On expiry or target invalidation, write an ordinary factual event.

Suggested:

- `is_major=False`
- `is_story=False`
- `related_avatars=[owner.id]`

### 11.3 Resolution event

After a hit, write a resolution factual event.

Suggested:

- equipment / boon / injury death can be set to `is_major=True`
- empty / non-lethal injury can be set to `is_major=False`
- `related_avatars` includes at least the owner id
- when an avatar target is hit, include the target avatar id

### 11.4 Story event

Sense and dissipation do not go through the LLM.

After a hit is resolved, a story event can be appended by probability.

Suggested additions:

- `StoryEventKind.OPPORTUNITY`
- `static/config.yml -> world.story.probabilities.opportunity`

Story events still follow the existing story event system rules:

- Generate the base factual event first.
- Then try to append a story via `StoryEventService.maybe_create_story(...)`.
- LLM-expanded body events use `is_story=True`.
- Default `allow_relation_changes=False`.

## 12. Save Structure

Active opportunities are long-term world state and should go into the save file.

They should not only be written into the event database, nor treated as temporary runtime state.

Suggested save structure:

```json
"opportunities": {
  "active": {
    "avatar_id": {
      "id": "...",
      "avatar_id": "...",
      "target_type": "region",
      "target_id": "201",
      "hint_text": "...",
      "created_month": 1234,
      "expires_month": 1294
    }
  },
  "cooldowns": {
    "avatar_id": 1354
  }
}
```

After loading, active opportunities and cooldowns should be restored.

During development, there is no requirement to pay complex compatibility costs for old saves; if a `.get` fallback is zero-cost, it can be handled along the way.

## 13. Cooldown Rules

Suggest two kinds of cooldown:

1. Dissipation cooldown: 12 months.
2. Resolved cooldown: 60 months.

Resolved includes:

- equipment
- boon
- empty
- injury
- death after injury

Dissipation caused by the target avatar's death uses the dissipation cooldown.

## 14. World Info

A general "Opportunity" description should be added to `static/game_configs/world_info.csv`.

The description only describes the world concept and does not expose mechanic numbers.

Recommended text:

```text
Cultivators may occasionally feel a sudden stir of fate, sensing that a person or place is tied to their own opportunity. If they follow the sense, they may gain treasure or a boon, return empty-handed, or meet danger; if they delay too long, the opportunity fades away.
```

## 15. i18n

New text should follow the current i18n rules:

1. The game is English-only; `en-US` is the sole and source locale.
2. In `.po` files, `msgid` uses English source text or a stable key.
3. Display text goes in `msgstr`.
4. Do not directly modify the merged `LC_MESSAGES/*.po` artifacts; maintain `modules/` or `game_configs_modules/` instead.
5. After editing source files, run `python tools/i18n/build_mo.py`.

Suggested new module:

- `static/locales/en-US/modules/opportunity.po`

If opportunity / boon config tables are added, correspondingly add:

- `static/locales/en-US/game_configs_modules/opportunity.po`
- or split by the final config table file name.

## 16. Frontend

Phase one does not add a standalone frontend opportunity section.

Opportunities may be reflected through the following existing paths:

1. The event bar shows sense, dissipation, and resolution events.
2. The avatar detail or AI context shows the current opportunity sense text.
3. In roleplay scenarios, when the player takes over an avatar, they should be able to see the current opportunity sense.

If the avatar detail shows the active opportunity, it should also stay restrained: show only one line of natural-language sense, with no quest panel, countdown quest card, or navigation button.

## 17. Suggested Implementation Locations

Later implementation should add independent modules, to avoid spreading further into `src/server/main.py` or the fortune file.

Possible locations:

- `src/systems/opportunity/`
- `src/systems/opportunity_types.py`
- `src/systems/opportunity_loader.py`
- `src/systems/opportunity_service.py`

Phase integration:

- Monthly generation: world passive/world event phase.
- Hit detection: a new phase after action execution.
- Expiry cleanup: can be handled uniformly in the monthly passive phase or in the hit detection phase.

If a new manager is added:

- It can be attached to `World`;
- serialized into `world_data["opportunities"]` on save;
- restored on load.

## 18. Test Suggestions

Should cover at least:

1. When there is no active opportunity and the probability hits, an opportunity is generated.
2. When there is an active opportunity, no new opportunity is generated.
3. During cooldown, no new opportunity is generated.
4. A region target triggers resolution after entering any tile.
5. An avatar target triggers resolution after entering observation range.
6. No immediate trigger in the generation month.
7. After expiry, a dissipation event is written and the active opportunity is cleared.
8. After the target avatar dies, a severance event is written and the active opportunity is cleared.
9. After the owner dies, the active opportunity is cleared.
10. The equipment outcome gives equipment at current realm +1 rank, and reuses item exchange.
11. The boon outcome writes temporary / persistent effects and recalculates effects.
12. The empty outcome clears the opportunity and enters the resolved cooldown.
13. The injury outcome deducts HP.
14. When injury causes HP <= 0, the death flow is followed.
15. Active opportunities and cooldowns can be saved and restored on load.
16. The AI context only exposes the vague sense text, not the target id, suggested action, or risk hint.
17. After adding `StoryEventKind.OPPORTUNITY`, story events still use `is_story=True`.
18. World info includes the general opportunity description.

## 19. Current Decisions

Final conclusions after this round of requirements confirmation:

1. Opportunity is separate from fortune and is an independent time-limited state.
2. Opportunity targets are only region and avatar.
3. The region hit range is any tile of the target region.
4. The avatar hit range is the owner's observation range.
5. Hit detection is placed after action execution.
6. Opportunity hints do not provide suggested search, risk hint, or action recommendations.
7. The AI only sees the natural-language vague sense and the remaining time.
8. Whether the avatar pursues it is decided by the existing AI.
9. Phase one rewards are only one-rank-higher equipment and great boons.
10. No direct breakthroughs.
11. No ordinary success / great success.
12. Injury may naturally lead to death; death is not a separate outcome.
13. Sense, dissipation, and resolution are all written into the event system.
14. Sense and dissipation do not go through the LLM; resolution can optionally go through a story event.
15. Active opportunities and cooldowns go into the save file.
16. The frontend does not add a standalone opportunity section.
