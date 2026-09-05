import json
import os

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(ROOT, "config.yaml")) as f:
        return yaml.safe_load(f)


def load_seen(config):
    path = os.path.join(ROOT, config["state"]["seen_file"])
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_seen(config, seen_set):
    path = os.path.join(ROOT, config["state"]["seen_file"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(seen_set), f, indent=2)


def append_log(config, items):
    path = os.path.join(ROOT, config["state"]["log_file"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
