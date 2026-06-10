"""Remember the folder last used in a file dialog, across runs.

The locations are stored in a small JSON file in the user's config directory so
that every utility opens where the user last picked files, instead of always
starting at the executable's location.

Different tools can keep separate folders by passing a *key*: most utilities
share the default folder, while the extract / split / renumber tools each use
their own, since they typically work on a different set of files.
"""
import os
import json

_CONFIG_FILE = "bridge-robot-utilities.json"


def _config_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, _CONFIG_FILE)


def _load():
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_last_dir(default=".", key="default"):
    """Return the last used directory for *key*, or *default* if none/invalid."""
    dirs = _load().get("last_dirs")
    if isinstance(dirs, dict):
        last = dirs.get(key)
        if last and os.path.isdir(last):
            return last
    return default


def set_last_dir(path, key="default"):
    """Remember the directory of *path* (a file or directory) under *key*."""
    if not path:
        return
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    if not directory:
        return
    try:
        data = _load()
        dirs = data.get("last_dirs")
        if not isinstance(dirs, dict):
            dirs = {}
        dirs[key] = directory
        data["last_dirs"] = dirs
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
