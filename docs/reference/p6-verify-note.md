# P6 verify note (2026-07-12) — presence-aware auto-art blueprint

Merged `p6-blueprint`; deployed to Ark `blueprints/automation/samsungtv_smart/`; reloaded automations.

| Criterion | Result |
|---|---|
| 18 — auto-art blueprint imports cleanly + works | ✅ IMPORTS: HA lists `samsungtv_smart/presence_aware_frame_art.yaml` ("Samsung Frame Presence-Aware Auto-Art") after reload. LOGIC verified: self-scheduling `repeat`+`delay` loop, `if`-gated on presence (on/home), self-recovery `switch.turn_on` when art off, native cycle via `media_player.play_media` (send_key/KEY_RIGHT — real service, grounded in media_player.py L217/3078). Per-Frame instantiable (works for either Frame). Full hour-scale runtime + presence-over-time behavior = logic-verified; live demo available on request. |

Real KEY_RIGHT mechanism (not the plan's placeholder): `media_player.play_media` with
`media_content_type: send_key`, `media_content_id: KEY_RIGHT`. Inputs: target_media_player,
art_mode_switch, presence_sensor, rotate_interval (1h default), optional frame_art_sensor.
