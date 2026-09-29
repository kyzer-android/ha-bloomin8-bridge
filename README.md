# BLOOMIN8 Immich Bridge

Home Assistant add-on that connects [Immich](https://immich.app) to a BLOOMIN8 e-ink photo frame: it builds an album from a recognized person, optimizes photos for the Spectra 6 e-ink display, and lets you resend and manage what's on the frame — all from a panel embedded directly in Home Assistant.

🇫🇷 [Français](#français) · 🇬🇧 [English](#english)

---

## Français

Add-on Home Assistant qui relie [Immich](https://immich.app) à un cadre photo e-ink BLOOMIN8 : constitution d'un album par reconnaissance de personne, optimisation des photos pour l'écran e-ink Spectra 6, et gestion de ce qui est envoyé au cadre — le tout depuis un panneau intégré directement dans Home Assistant.

### Fonctionnalités

| Fonction | Détail |
|---|---|
| `person_to_album` | Ajoute automatiquement les photos d'une personne reconnue à un album Immich |
| `bloomin8_optimize` | Filtre l'album source par orientation, optimise pour l'écran Spectra 6, dépose dans `destination_path/<portrait\|landscape>/` |
| Relance BLOOMIN8 | Bouton manuel + détection auto (silence prolongé) via l'API Home Assistant, notification native |
| Éditeur YAML | Lit/écrit le fichier de configuration de l'intégration `bloomin8_pull`, avec bouton "redémarrer HA" explicite |
| Galerie | Miniatures des images envoyées au cadre, rotation manuelle et suppression, avec sauvegarde en place |

### Installation

1. **Paramètres → Modules complémentaires → Boutique des modules → ⋮ → Dépôts**, ajoutez :
   `https://github.com/kyzer-android/ha-bloomin8-bridge`
2. Installez **BLOOMIN8 Immich Bridge** dans la liste.
3. Remplissez l'onglet **Configuration** (détail de chaque champ ci-dessous).
4. **Démarrer**, puis activez **Afficher dans la barre latérale** pour ouvrir le panneau intégré.

### Configuration — détail de chaque champ

#### Immich

| Champ | Attendu |
|---|---|
| `server` | URL complète de l'instance Immich, avec le port. Ex. `http://192.168.1.205:2283` |
| `api_key` | Clé API Immich. À créer dans Immich : avatar (en haut à droite) → Paramètres du compte → onglet "Clés API" → "Nouvelle clé API". Droits à cocher : `asset.read`, `album.read`, `albumAsset.create` (ajout aux albums, requis pour `person_to_album`) — ou "Tout sélectionner" pour ne pas chercher chaque droit. Copiez-la immédiatement : Immich ne la raffiche plus jamais ensuite. |

#### Person → Album

| Champ | Attendu |
|---|---|
| `enabled` | Active l'exécution planifiée. |
| `schedule` | Expression cron. Ex. `*/30 * * * *` = toutes les 30 minutes. |
| `links[].description` | Libellé libre pour se repérer dans la liste (ex. "Mon fils") — non utilisé par le script. |
| `links[].person_id` | UUID de la personne dans Immich. Explorer par personnes → cliquer la personne → l'UUID est dans l'URL après `/people/` (ex. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`). |
| `links[].album_id` | UUID de l'album cible. Ouvrir l'album → l'UUID est dans l'URL après `/albums/` (ex. `98765432-1abc-4def-9012-345678abcdef`). |

#### Optimisation BLOOMIN8

| Champ | Attendu |
|---|---|
| `enabled` | Active l'exécution planifiée. |
| `schedule` | Expression cron. Ex. `0 4 * * *` = tous les jours à 4h00. |
| `album_id` | UUID de l'album Immich source (même méthode que `links[].album_id` ci-dessus). |
| `orientation` | `portrait` ou `landscape` — détermine le sous-dossier de dépôt (`portrait/` ou `landscape/`) et doit correspondre à l'orientation configurée côté `bloomin8_pull`. |
| `destination_path` | Dossier sous `/media` surveillé par `bloomin8_pull`. Ex. `/media/bloomin8` (les sous-dossiers `portrait/`/`landscape/` sont créés automatiquement). |
| `resolution_width` / `resolution_height` | Taille cible en pixels. Ex. `1600` × `1200`. |
| `color_gamma` | Correction gamma avant dithering. `1.0` = neutre. Ex. `0.85` pour éclaircir légèrement. |
| `color_saturation` | Multiplicateur de saturation. `1.0` = neutre. Ex. `1.15` pour des couleurs plus vives (utile car l'e-ink les atténue). |
| `color_lift` / `color_lift_threshold` | Rehausse les tons sombres en dessous du seuil de luminosité (0-255) pour éviter les aplats noirs bouchés. Ex. `lift=13`, `threshold=90`. |

#### Cadre BLOOMIN8

| Champ | Attendu |
|---|---|
| `ip` | Adresse du cadre **sans** `http://` devant. Ex. `192.168.1.136` (la même que dans `bloomin8_pull`). |
| `token` | Le même `access_token` que celui configuré côté `bloomin8_pull` (`custom_yaml/bloomin8.yaml`). |

#### Relance & intégration HA

| Champ | Attendu |
|---|---|
| `ha_url` | URL de Home Assistant. Ex. `http://homeassistant.local:8123` |
| `ha_yaml_path` | Chemin relatif à `/config`. Ex. `custom_yaml/bloomin8.yaml` — laisser vide pour ne pas utiliser l'éditeur YAML intégré. |
| `ha_device_id` | La **clé** (pas le `name:`) sous `devices:` dans le fichier YAML `bloomin8_pull` — le numéro de série du cadre. Ex. `CB29695B3322ADA29D9578BD1A7B59F2`. |
| `auto_relance_enabled` | Relance automatiquement après une période de silence du cadre. |
| `auto_relance_after_hours` | Nombre d'heures sans pull réussi avant relance automatique. Ex. `12`. |
| `notify_service` | Nom **complet** du service HA, préfixe `notify.` inclus. Correct : `notify.mobile_app_sm_g991b`. Incorrect : `mobile_app_sm_g991b` (ne fonctionnera pas). Trouvable dans Outils de développement → Actions, en recherchant "notify". Laisser vide pour ne pas notifier. |

> ⚠️ Avant de cliquer sur "Relancer maintenant", le cadre doit déjà être **sorti de veille manuellement** (écran allumé) — la commande programme son prochain contact avec Home Assistant, elle ne le réveille pas physiquement.

### Prérequis

- Home Assistant OS ou Supervised (add-on Supervisor)
- Une instance [Immich](https://immich.app) accessible depuis Home Assistant
- L'intégration `bloomin8_pull` installée et configurée pour utiliser la relance et l'éditeur YAML

### Sécurité

Aucune IP, token ou clé API n'est en dur dans le code — tout passe par les options de l'add-on, chiffrées par Supervisor. L'add-on ne modifie jamais `configuration.yaml` directement, uniquement un fichier séparé inclus via `!include`.

### Licence

MIT — utilisation libre, sans garantie.

---

## English

Home Assistant add-on that connects [Immich](https://immich.app) to a BLOOMIN8 e-ink photo frame: it builds an album from a recognized person, optimizes photos for the Spectra 6 e-ink display, and lets you resend and manage what's on the frame — all from a panel embedded directly in Home Assistant.

### Features

| Feature | Detail |
|---|---|
| `person_to_album` | Automatically adds photos of a recognized person to an Immich album |
| `bloomin8_optimize` | Filters the source album by orientation, optimizes for the Spectra 6 e-ink display, writes to `destination_path/<portrait\|landscape>/` |
| BLOOMIN8 refresh | Manual button + automatic detection (prolonged silence) via the Home Assistant API, native notification |
| YAML editor | Reads/writes the `bloomin8_pull` integration's config file, with an explicit "restart HA" button |
| Gallery | Thumbnails of the images sent to the frame, manual rotation and deletion, saved in place |

### Installation

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**, add:
   `https://github.com/kyzer-android/ha-bloomin8-bridge`
2. Install **BLOOMIN8 Immich Bridge** from the list.
3. Fill in the **Configuration** tab (field-by-field detail below).
4. **Start**, then enable **Show in sidebar** to open the embedded panel.

### Configuration — field by field

#### Immich

| Field | Expected |
|---|---|
| `server` | Full URL of the Immich instance, with the port. E.g. `http://192.168.1.205:2283` |
| `api_key` | Immich API key. Create one in Immich: avatar (top right) → Account settings → "API Keys" tab → "New API Key". Permissions to check: `asset.read`, `album.read`, `albumAsset.create` (adding to albums, required for `person_to_album`) — or "Select all" to skip hunting for each one. Copy it immediately: Immich never shows it again afterwards. |

#### Person → Album

| Field | Expected |
|---|---|
| `enabled` | Enables the scheduled run. |
| `schedule` | Cron expression. E.g. `*/30 * * * *` = every 30 minutes. |
| `links[].description` | Free-text label to tell rows apart (e.g. "My son") — not used by the script. |
| `links[].person_id` | The person's UUID in Immich. Explore by people → click the person → the UUID is in the URL after `/people/` (e.g. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`). |
| `links[].album_id` | UUID of the target album. Open the album → the UUID is in the URL after `/albums/` (e.g. `98765432-1abc-4def-9012-345678abcdef`). |

#### BLOOMIN8 optimization

| Field | Expected |
|---|---|
| `enabled` | Enables the scheduled run. |
| `schedule` | Cron expression. E.g. `0 4 * * *` = every day at 4am. |
| `album_id` | UUID of the source Immich album (same method as `links[].album_id` above). |
| `orientation` | `portrait` or `landscape` — determines the destination subfolder (`portrait/` or `landscape/`) and must match the orientation set on the `bloomin8_pull` side. |
| `destination_path` | Folder under `/media` watched by `bloomin8_pull`. E.g. `/media/bloomin8` (`portrait/`/`landscape/` subfolders are created automatically). |
| `resolution_width` / `resolution_height` | Target size in pixels. E.g. `1600` × `1200`. |
| `color_gamma` | Gamma correction before dithering. `1.0` = neutral. E.g. `0.85` to lighten slightly. |
| `color_saturation` | Saturation multiplier. `1.0` = neutral. E.g. `1.15` for more vivid colors (useful since e-ink mutes them). |
| `color_lift` / `color_lift_threshold` | Lifts dark tones below the brightness threshold (0-255) to avoid crushed blacks. E.g. `lift=13`, `threshold=90`. |

#### BLOOMIN8 frame

| Field | Expected |
|---|---|
| `ip` | Frame address **without** `http://` in front. E.g. `192.168.1.136` (the same one used in `bloomin8_pull`). |
| `token` | The same `access_token` configured on the `bloomin8_pull` side (`custom_yaml/bloomin8.yaml`). |

#### Refresh & HA integration

| Field | Expected |
|---|---|
| `ha_url` | Home Assistant URL. E.g. `http://homeassistant.local:8123` |
| `ha_yaml_path` | Path relative to `/config`. E.g. `custom_yaml/bloomin8.yaml` — leave empty to skip the built-in YAML editor. |
| `ha_device_id` | The **key** (not the `name:`) under `devices:` in the `bloomin8_pull` YAML file — the frame's serial number. E.g. `CB29695B3322ADA29D9578BD1A7B59F2`. |
| `auto_relance_enabled` | Automatically triggers a refresh after the frame has been silent for a while. |
| `auto_relance_after_hours` | Hours without a successful pull before an auto-refresh. E.g. `12`. |
| `notify_service` | **Full** HA service name, including the `notify.` prefix. Correct: `notify.mobile_app_sm_g991b`. Wrong: `mobile_app_sm_g991b` (won't work). Find it under Developer Tools → Actions, searching for "notify". Leave empty to disable notifications. |

> ⚠️ Before clicking "Refresh now", the frame must already be **manually woken up** (screen on) — the command schedules its next contact with Home Assistant, it does not physically wake the device.

### Requirements

- Home Assistant OS or Supervised (add-on support)
- An [Immich](https://immich.app) instance reachable from Home Assistant
- The `bloomin8_pull` integration installed and configured to use the refresh button and YAML editor

### Security

No IP, token, or API key is hardcoded — everything goes through the add-on's options, encrypted by Supervisor. The add-on never modifies `configuration.yaml` directly, only a separate file included via `!include`.

### License

MIT — free to use, no warranty.
