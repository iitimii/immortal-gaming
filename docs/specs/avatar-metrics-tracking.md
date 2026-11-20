# Avatar Metrics Tracking

## Overview

Adds an optional Avatar metrics tracking feature for recording an avatar's growth trajectory. The feature is disabled by default and does not affect existing game logic.

## Features

- **Optional**: disabled by default, does not affect existing functionality
- **Lightweight**: only records key metrics (cultivation, resources, social, etc.)
- **Immutable**: a snapshot is never modified once created
- **Persistent**: supports save/load
- **Automatic cleanup**: keeps at most 1200 records by default (100 years)

## Usage

### Enabling Tracking

```python
# Enable Avatar metrics tracking
avatar.enable_metrics_tracking = True
```

### Automatic Recording

Once tracking is enabled, the simulator automatically calls `record_metrics()` every month:

```python
# Executed automatically in src.sim.simulator_engine.finalizer.finalize_step()
# avatar.record_metrics()  # called automatically every month
```

### Manual Recording with Event Tags

```python
from src.classes.avatar_metrics import MetricTag

# Manually record state (optional event tags)
avatar.record_metrics(tags=["breakthrough"])
avatar.record_metrics(tags=[MetricTag.INJURED.value, MetricTag.BATTLE.value])
avatar.record_metrics(tags=["custom_event"])  # custom tags are supported
```

### Viewing the Summary

```python
# Get the metrics tracking summary
summary = avatar.get_metrics_summary()
print(summary)
# Example output:
# {
#     "enabled": True,
#     "count": 120,
#     "first_record": 100,
#     "latest_record": 220,
#     "cultivation_growth": 5
# }
```

### Accessing the History

```python
# Access the history list directly
for metrics in avatar.metrics_history:
    print(f"Month {metrics.timestamp}: Level {metrics.cultivation_level}, HP {metrics.hp}")
```

## Design Principles

### 1. Optional

- Disabled by default (`enable_metrics_tracking = False`)
- Does not affect existing APIs and logic
- Can be enabled or disabled at any time

### 2. Lightweight

Only key metrics are recorded:

| Field | Type | Description |
|------|------|------|
| `timestamp` | `MonthStamp` | Record time |
| `age` | `int` | Age |
| `cultivation_level` | `int` | Cultivation level |
| `cultivation_progress` | `int` | Cultivation progress |
| `hp` | `float` | Current HP |
| `hp_max` | `float` | Max HP |
| `spirit_stones` | `int` | Spirit stone count |
| `relations_count` | `int` | Relation count |
| `known_regions_count` | `int` | Known region count |
| `tags` | `List[str]` | Event tags |

### 3. Immutability

- A snapshot is never modified once created
- Uses a dataclass to keep the structure clear
- Supports serialization/deserialization

### 4. Backward Compatibility

- Uses `default_factory` to avoid breaking old code
- Fully compatible with save/load
- Old saves use default values (empty list, False)

## Performance Impact

### When Disabled

- Zero impact (no extra memory or CPU)
- `record_metrics()` returns `None` immediately

### When Enabled

- About 200 bytes of new snapshot data per month
- About 240 KB per 100 years
- **Capped**: keeps at most 1200 records by default (adjustable via `max_metrics_history`)

```python
# Adjust the history cap
avatar.max_metrics_history = 600  # change to 50 years
```

## Default Tags

Using the default tags in the `MetricTag` enum is recommended:

| Tag | Value | Description |
|------|-----|------|
| `BREAKTHROUGH` | `"breakthrough"` | Breakthrough |
| `INJURED` | `"injured"` | Injured |
| `RECOVERED` | `"recovered"` | Recovered |
| `SECT_JOIN` | `"sect_join"` | Joined a sect |
| `SECT_LEAVE` | `"sect_leave"` | Left a sect |
| `TECHNIQUE_LEARN` | `"technique_learn"` | Learned a technique |
| `DEATH` | `"death"` | Death |
| `BATTLE` | `"battle"` | Battle |
| `DUNGEON` | `"dungeon"` | Explored a hidden domain |

### Using Tags

```python
from src.classes.avatar_metrics import MetricTag

# Use the enum (recommended)
avatar.record_metrics(tags=[MetricTag.BREAKTHROUGH.value])

# Multiple tags
avatar.record_metrics(tags=[
    MetricTag.INJURED.value,
    MetricTag.BATTLE.value
])

# Custom tags (also supported)
avatar.record_metrics(tags=["custom_event", "special_occurrence"])
```

## Data Structures

### AvatarMetrics

```python
@dataclass
class AvatarMetrics:
    timestamp: MonthStamp
    age: int
    cultivation_level: int
    cultivation_progress: int
    hp: float
    hp_max: float
    spirit_stones: int
    relations_count: int
    known_regions_count: int
    tags: List[str]

    def to_save_dict(self) -> dict:
        """Convert to a serializable dict"""
        pass

    @classmethod
    def from_save_dict(cls, data: dict) -> "AvatarMetrics":
        """Rebuild from a dict"""
        pass
```

## Serialization

### Save

Metrics tracking data is automatically included in the save:

```python
save_dict = avatar.to_save_dict()
# Contains:
# - "metrics_history": [...]
# - "enable_metrics_tracking": True
```

### Load

Restored automatically on load:

```python
avatar = Avatar.from_save_dict(data, world)
# metrics_history and enable_metrics_tracking are restored automatically
```

## Notes

### 1. Tag Flexibility

The `tags` field uses `List[str]` rather than `List[MetricTag]` for flexibility:
- Supports default tags (using `MetricTag.value`)
- Supports custom tags
- Allows mixing both

### 2. Automatic Cleanup

When the history exceeds `max_metrics_history`, old records are cleaned up automatically:
```python
# Keep the latest N records
if len(self.metrics_history) > self.max_metrics_history:
    self.metrics_history = self.metrics_history[-self.max_metrics_history:]
```

### 3. Immutability

The snapshot object itself is mutable (Python dataclass default), but by design it should be treated as immutable:
- Do not modify an `AvatarMetrics` object after creation
- To update, create a new snapshot

## Use Cases

### Tracking Cultivation Growth

```python
# Enable tracking
avatar.enable_metrics_tracking = True

# Run the simulation...
# State is recorded automatically every month

# Analyze growth
first = avatar.metrics_history[0]
latest = avatar.metrics_history[-1]
print(f"Cultivation growth: {latest.cultivation_level - first.cultivation_level}")
```

### Tagging Major Events

```python
# Tag on breakthrough
if avatar.cultivation_progress.realm != old_realm:
    avatar.record_metrics(tags=[MetricTag.BREAKTHROUGH.value])

# Tag when injured
if avatar.hp.value < avatar.hp.max_value * 0.3:
    avatar.record_metrics(tags=[MetricTag.INJURED.value])
```

### Analyzing Game Data

```python
# Export data to CSV/Pandas
import pandas as pd

data = []
for metrics in avatar.metrics_history:
    data.append({
        "timestamp": metrics.timestamp,
        "age": metrics.age,
        "level": metrics.cultivation_level,
        "hp": metrics.hp,
        "spirit_stones": metrics.spirit_stones,
    })

df = pd.DataFrame(data)
df.plot(x="timestamp", y="level")
```
