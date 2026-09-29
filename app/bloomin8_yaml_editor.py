"""
Lecture/écriture du fichier YAML de l'intégration `bloomin8_pull`.

Règle de sécurité : on ne touche JAMAIS configuration.yaml directement —
uniquement un fichier séparé que l'utilisateur inclut lui-même via
`!include` (ou `!include_dir_merge_named`/`_named`). C'est la config de
son propre `bloomin8_pull:`, pas la nôtre.

Deux structures possibles selon comment l'utilisateur a mis en place son
`!include` (détectées automatiquement) :
  - "wrapped"   : le fichier a une clé `bloomin8_pull:` en tête
                  (cas d'un !include_dir_merge_named avec nom de package)
  - "unwrapped" : le fichier contient directement access_token/devices/...
                  sans wrapper (cas d'un simple
                  `bloomin8_pull: !include custom_yaml/bloomin8.yaml`)

`bloomin8_pull` n'a aucun rechargement à chaud (confirmé dans sa doc) :
toute écriture nécessite un redémarrage complet de HA pour être prise en
compte — jamais déclenché automatiquement par l'add-on, seulement proposé.
"""
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

CONFIG_ROOT = Path("/config")

yaml = YAML(typ="rt")
yaml.preserve_quotes = True
yaml.width = 4096


class UnknownTag:
    """Représente un scalaire avec un tag YAML personnalisé (!secret,
    !include...) qu'on ne comprend pas et qu'on ne doit surtout pas
    altérer — on le réécrit exactement tel quel."""

    def __init__(self, tag, value):
        self.tag = tag
        self.value = value

    def __repr__(self):
        return f"{self.tag} {self.value}"


def _construct_unknown(loader, tag_suffix, node):
    return UnknownTag(node.tag, loader.construct_scalar(node))


def _represent_unknown(dumper, data):
    return dumper.represent_scalar(data.tag, data.value)


yaml.constructor.add_multi_constructor("!", _construct_unknown)
yaml.representer.add_representer(UnknownTag, _represent_unknown)


class Bloomin8YamlError(Exception):
    """Erreur exploitable telle quelle pour l'interface (message clair,
    pas de traceback Python)."""


def _resolve_path(relative_path: str) -> Path:
    if not relative_path:
        raise Bloomin8YamlError("Aucun chemin de fichier YAML configuré (option relance.ha_yaml_path).")
    path = (CONFIG_ROOT / relative_path).resolve()
    if CONFIG_ROOT not in path.parents and path != CONFIG_ROOT:
        raise Bloomin8YamlError("Chemin en dehors de /config refusé.")
    return path


def _load(relative_path: str) -> tuple[Path, CommentedMap, str]:
    """Retourne (chemin résolu, contenu racine, mode 'wrapped'|'unwrapped')."""
    path = _resolve_path(relative_path)
    if not path.exists():
        raise Bloomin8YamlError(
            f"Le fichier {relative_path} n'existe pas dans /config. "
            f"Crée-le d'abord (voir la doc bloomin8_pull) avant de l'éditer ici."
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except Exception as e:  # yaml.YAMLError et dérivés
        raise Bloomin8YamlError(f"Impossible de parser {relative_path} : {e}") from e

    if data is None:
        data = CommentedMap()

    if not isinstance(data, dict):
        raise Bloomin8YamlError(
            f"{relative_path} n'a pas la structure attendue (dictionnaire YAML)."
        )

    if "bloomin8_pull" in data and isinstance(data["bloomin8_pull"], dict):
        return path, data, "wrapped"

    # Structure "unwrapped" : on s'attend à retrouver au moins une clé
    # connue de bloomin8_pull pour confirmer qu'on est au bon endroit.
    known_keys = {"access_token", "image_dir", "publish_dir", "devices"}
    if known_keys & set(data.keys()):
        return path, data, "unwrapped"

    raise Bloomin8YamlError(
        f"{relative_path} ne ressemble pas à une config bloomin8_pull reconnue "
        f"(ni clé 'bloomin8_pull:', ni clés attendues comme 'devices'/'image_dir')."
    )


def _container(data: CommentedMap, mode: str) -> CommentedMap:
    return data["bloomin8_pull"] if mode == "wrapped" else data


def read_devices(relative_path: str) -> dict:
    """Retourne {device_id: {name, orientation, wake_up_hours}} — valeurs
    brutes en str (y compris pour les tags inconnus, affichés tels quels)."""
    try:
        _, data, mode = _load(relative_path)
    except Bloomin8YamlError:
        return {}

    container = _container(data, mode)
    devices = container.get("devices") or {}
    result = {}
    for device_id, cfg in devices.items():
        if not isinstance(cfg, dict):
            continue
        result[str(device_id)] = {
            "name": str(cfg.get("name", "")),
            "orientation": str(cfg.get("orientation", "")),
            "wake_up_hours": str(cfg.get("wake_up_hours", "")),
        }
    return result


def update_device(relative_path: str, device_id: str, name: str, orientation: str, wake_up_hours: str) -> str:
    """Crée ou met à jour un device dans le fichier, en préservant tout le
    reste (commentaires, ordre, tags !secret/!include...). Retourne le
    chemin résolu (pour affichage)."""
    if orientation not in ("P", "L"):
        # bloomin8_pull attend une lettre unique (P=portrait, L=landscape)
        # dans son propre YAML — ne pas confondre avec l'orientation de
        # notre add-on (mot complet, pour le sous-dossier de destination).
        raise Bloomin8YamlError("Orientation invalide (attendu : P ou L).")
    if not device_id:
        raise Bloomin8YamlError("device_id manquant.")

    path, data, mode = _load(relative_path)
    container = _container(data, mode)

    if "devices" not in container or not isinstance(container.get("devices"), dict):
        container["devices"] = CommentedMap()

    devices = container["devices"]
    if device_id not in devices or not isinstance(devices[device_id], dict):
        devices[device_id] = CommentedMap()

    devices[device_id]["name"] = name
    devices[device_id]["orientation"] = orientation
    devices[device_id]["wake_up_hours"] = wake_up_hours

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return str(path)
