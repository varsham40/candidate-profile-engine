import json

from models.config import ProjectionConfig


def load_projection_config(path):
    with open(path, "r") as f:
        data = json.load(f)

    return ProjectionConfig(**data)
