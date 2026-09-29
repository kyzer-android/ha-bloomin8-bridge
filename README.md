# BLOOMIN8 Immich Bridge — add-on Home Assistant

Génère un album Immich par reconnaissance de personne, optimise les photos
pour un cadre e-ink BLOOMIN8 (dithering Spectra 6, orientation stricte), et
gère la relance du pull + une galerie de rotation manuelle — le tout depuis
un panneau intégré à Home Assistant (Ingress), sans conteneur ni dashboard
séparé.

## Installation

1. **Paramètres → Add-ons → Add-on store → ⋮ → Dépôts**, ajoute :
   `https://github.com/mathieu/ha-bloomin8-bridge`
2. Installe **BLOOMIN8 Immich Bridge** dans la liste.
3. Onglet **Configuration** : renseigne Immich (serveur + clé API), le ou
   les liens personne→album, l'album source de BLOOMIN8, l'orientation,
   le dossier de destination (sous `/media`, partagé en NFS avec le point
   de montage BLOOMIN8 côté HAOS), l'IP/token du cadre, et le chemin du
   fichier YAML de l'intégration `bloomin8_pull` si tu veux l'éditer depuis
   l'add-on.
4. **Démarrer**, puis active **Afficher dans la barre latérale** pour
   ouvrir le panneau intégré (Ingress).

## Ce que fait l'add-on

| Fonction | Détail |
|---|---|
| `person_to_album` | Ajoute automatiquement les photos d'une personne reconnue à un album Immich |
| `bloomin8_optimize` | Filtre l'album source par orientation, optimise pour l'écran Spectra 6, dépose dans `destination_path/<portrait\|landscape>/` |
| Relance BLOOMIN8 | Bouton manuel + détection auto (12h de silence) via l'API Home Assistant, notification native |
| Éditeur YAML | Lit/écrit le fichier `bloomin8_pull` (détection auto avec/sans wrapper), bandeau + bouton "redémarrer HA" explicite |
| Galerie | Miniatures des images envoyées au cadre, rotation manuelle 90°/-90° avec sauvegarde en place |

## Ce qui n'est PAS dans cet add-on

La correction d'orientation automatique par reconnaissance de visage
(`orientation_fix`) n'est pas incluse — c'est un projet à part, indépendant
de BLOOMIN8. Si tu l'utilises déjà ailleurs (conteneur `immich-scripts`),
garde-le tel quel à côté de cet add-on.

## Sécurité

Aucune IP, token ou clé API n'est en dur dans le code — tout passe par les
options de l'add-on (chiffrées par Supervisor). L'add-on ne modifie jamais
`configuration.yaml` directement, uniquement un fichier séparé que tu
inclus toi-même via `!include`.
