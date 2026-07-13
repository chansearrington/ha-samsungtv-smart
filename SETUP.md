# Samsung Frame TV — Complete Setup Guide

This is the single, top-to-bottom guide for configuring the **Samsung TV Smart – Frame
Art Edition** integration. It walks you from install through OAuth2, IP-Control pairing,
the entities you get, the art services, the `/frame-art` dashboard, the presence-aware
auto-art blueprint, and troubleshooting.

It is written to be followed in order. Where a topic already has a deep reference doc in
this repo, this guide gives you the gist and links you there instead of repeating it.

> **The running example throughout this guide is a real two-Frame install:**
>
> | | Living Room Frame | Kitchen Frame |
> |---|---|---|
> | Model | 65" Samsung Frame | 65" Samsung Frame |
> | Config entry | its own entry | its own entry |
> | TV IP address | `192.168.1.182` | `192.168.1.186` |
> | Media player | `media_player.living_room_tv` | `media_player.kitchen_smartthings_hub` |
> | Art Mode switch | `switch.living_room_tv_art_mode` | `switch.kitchen_tv_art_mode` |
> | Frame Art sensor | `sensor.living_room_tv_frame_art` | `sensor.kitchen_tv_frame_art` |
>
> **Heads-up naming quirk:** the two Frames name their entities differently because of how
> each config entry was set up.
> - The Living Room media player is the tidy `media_player.living_room_tv`; the Kitchen media
>   player is `media_player.kitchen_smartthings_hub` (**not** `media_player.kitchen_tv`).
> - The picture/IP-Control entities carry a **doubled** prefix — `living_room_living_room_tv_*`
>   and `kitchen_kitchen_tv_*` — while the Art Mode switch and Frame Art sensor use the single
>   `living_room_tv_*` / `kitchen_tv_*` prefix.
>
> Always confirm the exact entity id in **Settings → Devices & services → Entities** rather
> than assuming — the tables below use the real ids from this install.

---

## 1. Overview

This integration is a fork of `ollo69/ha-samsungtv-smart` focused on **Samsung Frame TVs**.
On top of normal Samsung TV control (power, volume, sources, media) it adds:

- **OAuth2 SmartThings auth** so tokens auto-refresh instead of expiring every few months.
- **Full Art Mode control** — turn Art Mode on/off, pick artwork, set brightness / color
  temperature, change mattes, run slideshows, upload your own photos, download thumbnails.
- **A local IP-Control channel** (see section 4) that gives reliable power on/off even from
  Art Mode, plus picture-calibration controls and a reboot button — without going through
  the SmartThings cloud.
- **A browsable art gallery** — both a tap-to-display Lovelace dashboard and a native HA
  Media Source you can browse.

Each physical Frame is added as its **own config entry**, so the two 65" Frames in the
example above are fully independent — separate entities, separate settings, separate
pairing.

---

## 2. Install

Full install steps live in the **[README](./README.md#-installation)**. In short:

- **HACS (recommended):** HACS → Integrations → ⋮ → Custom repositories → add
  `https://github.com/TheFab21/ha-samsungtv-smart` as an **Integration** → install
  **Samsung TV Smart** → restart Home Assistant.
- **Manual:** copy the `samsungtv_smart` folder into `/config/custom_components/` and
  restart.

Requirements: a Samsung Smart TV (2016+), a Frame TV for the art features, Home Assistant
2024.1+, and a SmartThings account linked to the TV.

---

## 3. OAuth2 / SmartThings setup

**Do this once per Home Assistant instance** (the credentials are shared by all Frames).
Step-by-step with the exact SmartThings Developer Workspace screens is in the
**[README OAuth2 section](./README.md#-oauth2-setup-recommended)**. The gist:

1. In the [SmartThings Developer Workspace](https://smartthings.developer.samsung.com/workspace),
   create a project and register an OAuth app. Scopes: `r:devices:*` and `x:devices:*`.
   Redirect URI: `https://my.home-assistant.io/redirect/oauth`. Note the **OAuth Client Id**
   and **Client Secret** (use the *OAuth Client Id*, not the App Id).
2. In HA, **Settings → Devices & Services → Application Credentials → Add Credentials**,
   pick **Samsung TV Smart**, and paste the Client ID / Secret.
3. **Settings → Devices & Services → Add Integration → Samsung TV Smart**, choose the
   **SmartThings OAuth** method, and complete the browser flow.
4. Repeat step 3 once per Frame (each Frame becomes its own config entry).

Once done, tokens refresh automatically (~24h validity, refreshed 5 minutes before
expiry). No more manual token renewal.

---

## 4. IP-Control pairing (the important extra step)

**This is the step the other docs don't spell out.** SmartThings alone can be flaky at
powering a Frame on/off from Art Mode and does not expose picture calibration. This
integration adds a **local IP-Control channel** (Samsung's JSON-RPC "IP Remote" interface)
that talks straight to the TV over your LAN. Pairing it is a **one-time** action per Frame,
and the token it returns is stored in the config entry and survives reboots — you do not
have to re-pair.

### 4a. Turn on IP Remote on the TV

On the Frame itself:

**Settings → All Settings → Connections → Network → Expert Settings → enable "IP Remote"**

Leave the TV **ON and in normal viewing** (an app or a live input) — **not** Art Mode and
not standby. Pairing fails from Art Mode/standby.

### 4b. Pair from Home Assistant

1. **Settings → Devices & services → Samsung TV Smart**.
2. Click the Frame you want (e.g. the Living Room entry), then **⋮ → Reconfigure**.
3. On the reconfigure menu choose **"IP Control (reliable power & pairing)"**.
4. Check **"Pair now"** and **Submit**.
5. Watch the TV — an **authorization prompt** appears on screen. **Select Allow** on the TV
   with the physical remote.
6. HA confirms *"IP Control paired successfully. The access token has been stored."*

Repeat 1–6 for the second Frame.

> If pairing fails, it's almost always because the TV was in Art Mode / standby, or IP
> Remote wasn't enabled. Put the TV into a normal input, re-check the setting, and try again.

### 4c. What pairing turns on

Once a Frame is paired, IP-Control-backed entities appear for it (all confirmed present on
the live install). Using the doubled-prefix naming:

- **Reboot button** — `button.living_room_living_room_tv_reboot_tv` /
  `button.kitchen_kitchen_tv_reboot_tv`. Reboots the TV over IP-Control; the token survives
  the reboot.
- **Picture-calibration numbers** — `backlight`, `contrast`, `sharpness`, `color`, `tint`,
  and a picture `brightness` (e.g. `number.living_room_living_room_tv_backlight`, …). These
  drive the TV's expert picture settings live.
- **Color-tone and speaker selects** — `select.living_room_living_room_tv_color_tone` and
  `select.living_room_living_room_tv_speaker_select` (audio output).
- **More reliable Art-Mode power** — if you also tick **"Use IP Control for Art Mode"** (a
  toggle that appears once paired), Art-Mode on/off is driven over IP-Control instead of the
  cloud.

Two toggles on that same reconfigure screen (visible only after pairing) let you **Enable /
disable IP Control** and **Use IP Control for Art Mode**. Turning IP Control off removes the
reboot button and picture/color-tone/speaker entities again.

For the wire-level protocol details, see the integration's IP-Control client module
`custom_components/samsungtv_smart/api/ipcontrol.py` and the research notes in
**[docs/reference/frame-art-research.md](./docs/reference/frame-art-research.md)** (reference
only — you don't need either to set things up).

---

## 5. Entities reference

Each Frame creates a family of entities. The most useful ones for Frame use are below, with
the real ids from this install. (There are also standard TV entities — volume, mute, input
source, power, sound mode, energy — created on the media player device.)

| Entity | Example id (Living Room) | What it does |
|--------|--------------------------|--------------|
| **Media player** | `media_player.living_room_tv` | Main TV control (power, volume, source, media). The **target for every `samsungtv_smart.art_*` service**. Kitchen's is `media_player.kitchen_smartthings_hub`. |
| **Art Mode switch** | `switch.living_room_tv_art_mode` | Toggle Art Mode on/off (with retry logic). |
| **Frame Art sensor** | `sensor.living_room_tv_frame_art` | Reports current Art-Mode state; attributes include `current_content_id`, `current_matte_id`, thumbnail info, artwork count. |
| **Matte selects** | `select.living_room_living_room_tv_matte_type`, `…_matte_color` | Pick the matte style/color for artwork. Options are pulled live from the TV. |
| **Picture mode select** | `select.living_room_living_room_tv_picture_mode` | TV picture preset (via SmartThings). |
| **Motion selects** | `select.living_room_living_room_tv_motion_sensitivity`, `…_motion_timer` | Frame motion-sensor behavior (only created on models that have it). |
| **Brightness sensor select** | `select.living_room_living_room_tv_brightness_sensor` | Art-Mode ambient brightness-sensor mode. |
| **Color tone select** *(IP-Control)* | `select.living_room_living_room_tv_color_tone` | Warm/cool color tone. |
| **Speaker select** *(IP-Control)* | `select.living_room_living_room_tv_speaker_select` | Audio output device. |
| **Art-mode numbers** | `number.living_room_living_room_tv_art_mode_brightness`, `…_art_mode_color_temperature` | Art-Mode display brightness and warm/cool. |
| **Picture numbers** *(IP-Control)* | `number.living_room_living_room_tv_{backlight,contrast,sharpness,color,tint,brightness}` | Expert picture calibration. |
| **Reboot button** *(IP-Control)* | `button.living_room_living_room_tv_reboot_tv` | Reboot the TV over IP-Control. |

Entities tagged *(IP-Control)* only exist after you complete section 4. Swap `living_room` /
`living_room_tv` for `kitchen` / `kitchen_tv` (and remember `media_player.kitchen_smartthings_hub`)
for the Kitchen Frame.

For a deeper explanation of the Frame-Art entities and their attributes, see
**[Frame_Art.md](./Frame_Art.md#entities)**.

---

## 6. Art services

The full catalog of `samsungtv_smart.art_*` services (get/set Art Mode, `art_select_image`,
`art_available`, `art_upload`, `art_delete`, `art_set_brightness`, `art_change_matte`,
`art_set_slideshow`, `art_set_auto_rotation`, thumbnails, favorites, photo filters, etc.) is
documented in the **[README service list](./README.md#-frame-tv-art-mode-features)** and, with
parameter tables, in **[Frame_Art.md](./Frame_Art.md#available-services)**. Every service
targets the Frame's **media player** entity.

### The added service: `art_upload_folder`

This install adds a convenience service on top of `art_upload`. Instead of uploading one
file at a time, it uploads **every image in a server-side folder** and is safe to re-run:

- **Field:** `folder_path` (required) — a folder on the HA server, e.g.
  `/config/www/frame_art_uploads/`.
- **Deduplication via a sidecar:** it writes a small `.dedup_sidecar.json` inside the folder,
  keyed on each file's name + modified time. A second run of an unchanged folder uploads
  **0 files** — already-sent images are skipped. Edit or add an image and only that image
  uploads on the next run.
- **Throttled:** uploads are spaced by a short delay so the TV isn't hammered.
- **Formats:** `.jpg`, `.jpeg`, `.png`.

> **Permissions matter:** the folder must be writable by the Home Assistant process (uid
> **99:100** on a typical Home Assistant OS / Docker install), because the service writes the
> sidecar file there. Put the folder under `/config` (e.g. `/config/www/frame_art_uploads/`)
> so it inherits the right ownership.

**Example call:**

```yaml
action: samsungtv_smart.art_upload_folder
target:
  entity_id: media_player.living_room_tv
data:
  folder_path: /config/www/frame_art_uploads/
```

Drop new photos into `/config/www/frame_art_uploads/`, call the service, and they appear on
the Frame. Re-running it after adding one photo uploads just that one.

---

## 7. The `/frame-art` dashboard

A ready-to-run **Frame Art dashboard** is live at URL path **`/frame-art`**, with **one view
per Frame** (Living Room, Kitchen). Its exact exported config is
**[docs/gallery/frame-art-dashboard.yaml](./docs/gallery/frame-art-dashboard.yaml)**, and the
build notes are in **[docs/gallery/README.md](./docs/gallery/README.md)**.

Each view is built from:

1. **A row of buttons** — **Art Mode** (calls `art_set_artmode` → enabled), **Bright**
   (`art_set_brightness: 80`), **Dim** (`art_set_brightness: 30`), each targeting that
   Frame's media player.
2. **A `folder-gallery-card`** — a thumbnail grid. **Tap a thumbnail → the art shows on the
   Frame** via `samsungtv_smart.art_select_image` (the card derives `content_id` from the
   thumbnail filename). Long-press opens a full-screen lightbox preview.

The gallery card is **auto-registered by the integration** at
`/api/samsungtv_smart/folder-gallery-card.js` — no HACS resource needed.

**How the thumbnails get there (important):** the card renders a **static `image_list`** — a
snapshot of the thumbnail files that existed on disk when the dashboard was saved. Those
thumbnail files are produced by pre-fetching them with the
**`art_get_thumbnails_batch`** service against each Frame's media player, e.g.:

```yaml
action: samsungtv_smart.art_get_thumbnails_batch
target:
  entity_id: media_player.living_room_tv   # or media_player.kitchen_smartthings_hub
```

Thumbnails land under `www/frame_art/<entry_id>/{personal,store,other}/<content_id>.jpg`.
**The Frame must be reachable (on/Art Mode) when you run the batch**, or nothing downloads.
After favoriting new art and re-running the batch, add the new
`/local/frame_art/<entry_id>/…/<content_id>.jpg` paths to the card's `image_list`.

**Two design notes:**

- **`camera-gallery-card` was intentionally removed.** It needs date-grouped file paths
  (`path_datetime_format`) meant for camera footage and threw a configuration error on
  dateless art thumbnails. The `folder-gallery-card` is the working tap-to-display gallery.
- **Dynamic full-library browsing** is available without any of the above: this integration
  registers a **Media Source**, so **Media → "Samsung Frame Art"** in HA lets you browse each
  Frame's whole live art library (browse/preview only — no tap-to-display there).

---

## 8. Presence-aware auto-art blueprint

The blueprint **`presence_aware_frame_art.yaml`** keeps a Frame in Art Mode intelligently —
advancing to the next artwork on an interval **while the room is occupied**, and doing
nothing when it's empty (so it won't interrupt a movie or wake a panel you left off). Full
docs and per-Frame examples are in
**[blueprints/automation/samsungtv_smart/README.md](./blueprints/automation/samsungtv_smart/README.md)**.

**Inputs:**

| Input | Purpose |
|-------|---------|
| `target_media_player` | The Frame the "next art" `KEY_RIGHT` key is sent to. |
| `art_mode_switch` | Turned on for self-recovery when the room is occupied but Art Mode dropped. |
| `presence_sensor` | Occupancy signal (binary_sensor / person / device_tracker). |
| `rotate_interval` | How often to advance artwork while occupied (default 1 hour). |
| `frame_art_sensor` *(optional)* | Extra Art-Mode confirmation — if set, self-recovery only fires when both the switch and this sensor say Art Mode is off. |

**Behavior:** on each interval, if occupied, it (a) re-enables Art Mode if the Frame fell out
of it, and (b) advances to the next artwork by sending `KEY_RIGHT` (the same key the physical
remote uses). Create **one automation instance per Frame** — e.g. Living Room using
`media_player.living_room_tv` / `switch.living_room_tv_art_mode`, Kitchen using
`media_player.kitchen_smartthings_hub` / `switch.kitchen_tv_art_mode`.

---

## 9. Troubleshooting

- **A TV's IP address changed.** Repoint the config entry: **Settings → Devices & services →
  Samsung TV Smart → [the TV] → ⋮ → Reconfigure → connection step**, and set the new host
  (the example Frames are `192.168.1.182` and `192.168.1.186`). Assigning each Frame a **DHCP
  reservation** on your router avoids this. IP-Control does not need re-pairing after an IP
  change — just update the host.

- **Gallery thumbnails show as broken / 404.** The thumbnail files aren't on disk yet. Run
  `art_get_thumbnails_batch` against the Frame's media player **with the Frame on**, then
  reload the dashboard. If a specific tile 404s, its `content_id` isn't in the pre-fetched
  set — re-run the batch or add the file to `image_list`.

- **Gallery flickers / reloads.** This was fixed by having `folder-gallery-card` render a
  **static `image_list`** (server-side thumbnails) instead of continuously re-scanning. The
  live dashboard already uses that mode (`server_thumbnails: true`).

- **Reboot button / picture numbers / color-tone / speaker selects are missing.** That Frame
  isn't IP-Control paired (or IP Control is disabled). Do section 4: enable IP Remote on the
  TV, then Reconfigure → IP Control → Pair now → Allow on the TV.

- **IP-Control pairing keeps failing.** The TV must be **ON in a normal input — not Art Mode,
  not standby — with IP Remote enabled** (Settings → Connections → Network → Expert Settings).
  Retry from a live input.

- **Art Mode commands fail silently / OAuth token errors.** See the
  **[README troubleshooting](./README.md#-troubleshooting)** and
  **[Frame_Art.md troubleshooting](./Frame_Art.md#troubleshooting)** for debug logging and
  OAuth fixes.

---

## Related docs

- **[README.md](./README.md)** — install, OAuth2, full service list, folder-gallery-card.
- **[Frame_Art.md](./Frame_Art.md)** — deep dive on Art-Mode entities and services.
- **[Frame_Art_Gallery.md](./Frame_Art_Gallery.md)** — interactive gallery specifics.
- **[IP_Control_Protocol_Reference.md](./IP_Control_Protocol_Reference.md)** — IP-Control (JSON-RPC) wire-protocol reference. Client implementation: `custom_components/samsungtv_smart/api/ipcontrol.py`.
- **[docs/gallery/README.md](./docs/gallery/README.md)** — how the `/frame-art` dashboard was built.
- **[blueprints/automation/samsungtv_smart/README.md](./blueprints/automation/samsungtv_smart/README.md)** — presence-aware auto-art blueprint.
