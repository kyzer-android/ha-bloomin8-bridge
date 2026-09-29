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
| Galerie | Miniatures des images envoyées au cadre, rotation manuelle avec sauvegarde en place |

### Installation

1. **Paramètres → Modules complémentaires → Boutique des modules → ⋮ → Dépôts**, ajoute :
   `https://github.com/kyzer-android/ha-bloomin8-bridge`
2. Installe **BLOOMIN8 Immich Bridge** dans la liste.
3. Onglet **Configuration** : renseigne Immich (serveur + clé API), le ou les liens personne → album, l'album source BLOOMIN8, l'orientation, le dossier de destination, l'IP/token du cadre, et le chemin du fichier YAML de l'intégration `bloomin8_pull` si tu veux l'éditer depuis l'add-on.
4. **Démarrer**, puis active **Afficher dans la barre latérale** pour ouvrir le panneau intégré.

### Prérequis

- Home Assistant OS ou Supervised (add-on Supervisor)
- Une instance [Immich](https://immich.app) accessible depuis Home Assistant
- L'intégration `bloomin8_pull` installée et configurée si tu utilises la relance/l'éditeur YAML

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
| Gallery | Thumbnails of the images sent to the frame, manual rotation saved in place |

### Installation

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**, add:
   `https://github.com/kyzer-android/ha-bloomin8-bridge`
2. Install **BLOOMIN8 Immich Bridge** from the list.
3. **Configuration** tab: fill in Immich (server + API key), the person → album link(s), the BLOOMIN8 source album, orientation, the destination folder, the frame's IP/token, and the `bloomin8_pull` integration's YAML path if you want to edit it from the add-on.
4. **Start**, then enable **Show in sidebar** to open the embedded panel.

### Requirements

- Home Assistant OS or Supervised (add-on support)
- An [Immich](https://immich.app) instance reachable from Home Assistant
- The `bloomin8_pull` integration installed and configured if you use the refresh button/YAML editor

### Security

No IP, token, or API key is hardcoded — everything goes through the add-on's options, encrypted by Supervisor. The add-on never modifies `configuration.yaml` directly, only a separate file included via `!include`.

### License

MIT — free to use, no warranty.
