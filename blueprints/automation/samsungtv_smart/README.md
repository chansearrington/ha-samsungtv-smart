# Samsung Frame Presence-Aware Auto-Art blueprint

`presence_aware_frame_art.yaml` keeps a Samsung Frame in Art Mode
intelligently, without ever fighting you when you actually want to watch TV.

Inspired by [`sharkpunch5/frametv`](https://github.com/sharkpunch5/frametv),
but built for **this** integration and grounded in its real services.

## What it does

On a configurable interval, **while the room is occupied**:

1. **Self-recovery** — if the Frame has dropped out of Art Mode, it turns the
   Art Mode switch back on. (This relies on the `in_artmode()` bug-1 fix, which
   is what makes the Art Mode switch report the true state on 2025 Frames.)
2. **Next artwork** — it advances to the next piece of art using the TV's own
   native selection, by sending the `KEY_RIGHT` remote key via
   `media_player.play_media` (`media_content_type: send_key`,
   `media_content_id: KEY_RIGHT`) — the same key path the physical remote uses.

**When the room is empty it does nothing** — no key presses, no forcing Art
Mode. So it will not interrupt a movie and it will not wake a panel you meant
to leave off.

## Inputs

| Input | Type | Purpose |
|-------|------|---------|
| **Frame TV media player** (`target_media_player`) | media_player target | The Frame the `KEY_RIGHT` "next art" key is sent to. |
| **Art Mode switch** (`art_mode_switch`) | switch entity | Turned on for self-recovery when occupied but out of Art Mode. |
| **Room presence / occupancy sensor** (`presence_sensor`) | binary_sensor / person / device_tracker | The occupancy signal. Occupied = `on` (binary_sensor) or `home` (person/device_tracker). |
| **Rotate interval** (`rotate_interval`) | duration | How often to advance the artwork while occupied. Default 1 hour. |
| **Frame Art sensor** (`frame_art_sensor`) | sensor (optional) | Extra Art-Mode confirmation. If set, self-recovery only fires when the switch **and** this sensor both say Art Mode is off. Leave blank to use the switch alone. |

## Install

1. Copy `presence_aware_frame_art.yaml` to your Home Assistant config under
   `config/blueprints/automation/samsungtv_smart/` (this repo already lays it
   out that way — the folder maps 1:1 into HA's blueprints directory), **or**
   go to **Settings → Automations & scenes → Blueprints → Import blueprint**
   and paste the raw GitHub URL of the file.
2. Go to **Settings → Automations & scenes → Blueprints**, find
   **Samsung Frame Presence-Aware Auto-Art**, and click **Create automation**.
3. Pick the inputs for the Frame you are wiring up (see examples below).
4. Repeat once per Frame — each Frame gets its own automation instance.

The loop that drives the interval is (re)started automatically on Home
Assistant startup and whenever you reload automations.

## Example instances (one per Frame)

### Living Room Frame

```yaml
alias: Living Room Frame — presence-aware art
use_blueprint:
  path: samsungtv_smart/presence_aware_frame_art.yaml
  input:
    target_media_player:
      entity_id: media_player.living_room_tv
    art_mode_switch: switch.living_room_tv_art_mode
    presence_sensor: binary_sensor.living_room_occupancy
    rotate_interval:
      hours: 1
      minutes: 0
      seconds: 0
    # frame_art_sensor: sensor.living_room_tv_frame_art   # optional
```

### Kitchen Frame

```yaml
alias: Kitchen Frame — presence-aware art
use_blueprint:
  path: samsungtv_smart/presence_aware_frame_art.yaml
  input:
    target_media_player:
      entity_id: media_player.kitchen_smartthings_hub   # note: NOT kitchen_tv
    art_mode_switch: switch.kitchen_tv_art_mode
    presence_sensor: binary_sensor.kitchen_motion
    rotate_interval:
      minutes: 30
      seconds: 0
    # frame_art_sensor: sensor.kitchen_tv_frame_art      # optional
```

> Replace the `presence_sensor` entity ids with your real motion/occupancy
> sensors. The kitchen Frame's media player is `media_player.kitchen_smartthings_hub`
> — a naming quirk of that config entry, not `media_player.kitchen_tv`.
