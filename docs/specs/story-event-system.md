# Story Event System Refactor Notes

> This document describes the story event (Story Event) mechanism that has already landed in the current repository.
>
> For the current implementation, refer to the following code first:
>
> - `src/classes/story_event_service.py`
> - `src/systems/battle.py`
> - `src/systems/fortune.py`
> - `src/classes/action/**/*.py`
> - `src/classes/mutual_action/**/*.py`
> - `src/classes/gathering/**/*.py`
> - `static/config.yml`

## Goals

The goal of this refactor is to change "story events" from "calling the LLM directly in several business files and producing events" into a structure of "a unified story entry service + per-kind configured probabilities".

This mainly solves three problems:

1. Previously, many entry points produced a story event unconditionally, so the frequency was too high and stories were often repetitive.
2. Probability logic was scattered across different files, which made it hard to maintain and hard to tune uniformly.
3. Stories from different sources such as `gathering`, combat, social interaction and fortunate encounters had inconsistent semantics, which made it easy for later agent changes to keep spreading the inconsistency.

## Design Principles

### 1. A story event is an add-on layer on top of a result event

All actions, systems and gatherings should first complete their business settlement, then generate the base result event.  
A story event is only a text-expansion layer that "attempts to elaborate" after the result event.

Therefore the standard flow is:

1. Settle state changes
2. Generate the base event
3. Call `StoryEventService.maybe_create_story(...)`
4. On a hit, append a story event; on a miss, skip

### 2. Unified entry point, no scattering

All story generation goes through `StoryEventService`:

- `maybe_create_story(...)`
- `maybe_create_gathering_story(...)`

The business layer no longer decides probabilities itself, and should avoid constructing `Event(..., is_story=True)` directly where possible.

### 3. `gathering` is fixed at 100%

The story probability for gathering events is fixed at `100%` and no longer takes part in the regular probability roll.  
The frequency of these events is already controlled by external systems, and they are naturally suited to summarizing a group event with one long piece of text.

## Story Kind Classification

Story sources are currently classified uniformly through `StoryEventKind`:

- `combat`
- `relationship_major`
- `cultivation_major`
- `crafting`
- `daily_social`
- `world_fortune`
- `world_misfortune`
- `gathering`

The probability configuration for these kinds lives in one place:

- `static/config.yml -> game.story.probabilities`

## Event Semantics Conventions

### Base events

Base result events keep their original semantics:

- `is_major=True`: a major fact, enters long-term memory
- `is_major=False`: an ordinary fact, enters short-term memory

### Story events

All "narrative-body stories" expanded by the LLM uniformly use:

- `is_story=True`

These events still:

- appear in the event panel
- appear in the paginated events API

But they should not replace the base fact event itself.

## Current Coverage

### Old paths refactored onto the unified story entry

- Battle wrap-up
- Successful assassination
- Breakthrough
- Secluded cultivation
- Confession of love
- Dual cultivation
- Sworn brotherhood
- Sparring
- Fortunate encounter
- Misfortune

### New low-probability story entry points

- Tea party
- Playing chess
- Gift giving
- Preaching the Dao
- Conversation
- Forging
- Alchemy
- Beast taming

### Gatherings that always (100%) produce a story

- Auction
- Hidden domain
- World martial tournament
- Sect Dao-preaching conference

## Testing Strategy

Tests related to story events should follow these principles:

1. Use `StoryEventService.should_trigger(...)` to control whether a story is produced.
2. Do not depend on real random numbers.
3. Business tests fall into two categories:
   - Verify that the base result event is still correct
   - Verify that when a story hits or misses, the event list structure matches expectations
4. Gathering tests should verify that their story events are `is_story=True`.

## Maintenance Recommendations

If a new story entry point is added later, first check whether it meets the following conditions:

- Whether there is a clear "result event" that can serve as the anchor for expanding the story
- Whether it has enough narrative tension, rather than being a high-frequency routine behavior
- Whether it can be classified under an existing `StoryEventKind`

If it is just a high-frequency, repetitive, mechanical action, it is not recommended to hook it into story events directly, so as not to bring back the problem of flooding the event panel.
