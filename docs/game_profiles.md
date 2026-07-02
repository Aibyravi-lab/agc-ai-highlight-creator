# Game Intelligence Profiles

## Architecture

Game Intelligence Profiles decouple CLIP prompt sets from the core AI pipeline. Each profile is a self-contained class that describes how to detect highlights for a specific game. The pipeline selects a profile once per video, then passes it to `ClipService` for every frame analysis.

```
video_path
    │
    ▼
ProfileRegistry.detect_profile(video_path)
    │
    ├── Match found → GameProfile (e.g. GTAProfile)
    │
    └── No match    → DefaultProfile (generic prompts)
              │
              ▼
     PipelineService._run_pipeline(profile=...)
              │
              ▼
     ClipService.get_highlight_result(frame_path, profile)
              │
              ├── profile.get_all_prompts()       → CLIP model input
              ├── profile.get_positive_categories() → highlight classification
              └── profile.get_negative_categories() → non-highlight classification
```

## Detection Flow

```
Filename: "a1b2c3d4_gta_v_ranked.mp4"
              │
              ▼
  Path.stem → "a1b2c3d4_gta_v_ranked"
              │
              ▼
  Normalize  → "a1b2c3d4 gta v ranked"   (underscores/dashes → spaces, lowercase)
              │
              ▼
  Alias scan → "gta v" found in GTAProfile.aliases
              │
              ▼
  Return GTAProfile
```

If no alias matches, `DefaultProfile` is returned, which contains the same generic prompts as the original `GAME_EVENTS` config — preserving identical pipeline behavior for unknown games.

## File Layout

```
backend/app/services/game_profiles/
├── __init__.py              exports BaseProfile, DefaultProfile, ProfileRegistry
├── base_profile.py          BaseProfile (abstract) + DefaultProfile (generic fallback)
├── profile_registry.py      ProfileRegistry — detect_profile, detect_profile_from_text, get_default_profile
├── gta_profile.py           GTAProfile
├── valorant_profile.py      ValorantProfile
├── cs2_profile.py           CS2Profile
├── pubg_profile.py          PUBGProfile
├── snowrunner_profile.py    SnowRunnerProfile
├── forza_profile.py         ForzaProfile
├── minecraft_profile.py     MinecraftProfile
└── rocketleague_profile.py  RocketLeagueProfile
```

## Profile Interface

Every profile extends `BaseProfile` and must implement:

| Property | Type | Description |
|---|---|---|
| `game_name` | `str` | Human-readable game name |
| `aliases` | `list[str]` | Lowercase strings to match in filename |
| `clip_positive_prompts` | `dict[str, list[str]]` | Categories whose frames count as highlights |
| `clip_negative_prompts` | `dict[str, list[str]]` | Categories whose frames count as non-highlights |
| `priority_actions` | `list[str]` | Ordered category preference (for future ranking use) |
| `thumbnail_preferences` | `dict` | Hints for thumbnail selection (reserved for future use) |
| `metadata` | `dict` | Genre, platform, version info |

Helper methods provided by `BaseProfile` (no override needed):

- `get_all_prompts()` — flattens positive + negative dicts into `[{"category": ..., "prompt": ...}]`
- `get_positive_categories()` — list of keys from `clip_positive_prompts`
- `get_negative_categories()` — list of keys from `clip_negative_prompts`

## Fallback Logic

```
detect_profile(filename)
    │
    ├── Alias matched → return matched GameProfile
    │
    └── No alias matched → return DefaultProfile()

DefaultProfile contains the original GAME_EVENTS prompts:
  Positive: combat, vehicle, action, victory, danger
  Negative: exploration
```

Behavior with `DefaultProfile` is byte-for-byte identical to the pre-profile pipeline.

## Adding a New Game

1. Create `backend/app/services/game_profiles/mygame_profile.py`:

```python
from app.services.game_profiles.base_profile import BaseProfile

class MyGameProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "My Game"

    @property
    def aliases(self) -> list[str]:
        return ["my game", "mygame"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "action": ["exciting moment in My Game", ...],
            "victory": ["winning screen My Game", ...],
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": ["slow walking in My Game", ...]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["action", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {"prefer_action": True}

    @property
    def metadata(self) -> dict:
        return {"genre": "...", "platform": "...", "version": "1.0"}
```

2. Register it in `profile_registry.py` — add to the `_PROFILES` list:

```python
from app.services.game_profiles.mygame_profile import MyGameProfile

_PROFILES: list[BaseProfile] = [
    ...
    MyGameProfile(),
]
```

No other files need to change.

## Alias Matching Rules

- Aliases are matched as substrings against the normalized filename stem
- Normalization: lowercase, underscores and dashes replaced with spaces
- First match wins (profile order in `_PROFILES` is the tiebreak)
- Aliases should be ordered from most specific to least specific within each profile

## Supported Games

| Game | Profile Class | Key Aliases |
|---|---|---|
| Grand Theft Auto V | `GTAProfile` | gta v, gtav, gta 5, grand theft auto |
| Valorant | `ValorantProfile` | valorant, valo |
| Counter-Strike 2 | `CS2Profile` | cs2, counter strike, csgo |
| PUBG: Battlegrounds | `PUBGProfile` | pubg, battlegrounds |
| SnowRunner | `SnowRunnerProfile` | snowrunner, snow runner, spintires |
| Forza | `ForzaProfile` | forza, forza horizon |
| Minecraft | `MinecraftProfile` | minecraft |
| Rocket League | `RocketLeagueProfile` | rocket league, rocketleague |
| Unknown | `DefaultProfile` | (automatic fallback) |
