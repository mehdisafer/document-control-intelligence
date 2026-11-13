"""Externally provisioned actor tokens. Authentication is distinct from identity input."""

import hashlib
import hmac
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    roles: list[Literal["reader", "operator", "approver", "publisher"]] = Field(min_length=1)
    token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Auth:
    def __init__(self, path: Path | None):
        if path is None or not path.is_file():
            raise ValueError("DCI_AUTH_FILE must point to an external actor-token configuration")
        raw = json.loads(path.read_text())
        if set(raw) != {"schema_version", "actors"} or raw["schema_version"] != "1.0":
            raise ValueError("Unsupported authentication configuration")
        self.actors = [Actor.model_validate(actor) for actor in raw["actors"]]
        if not self.actors or len({a.name for a in self.actors}) != len(self.actors):
            raise ValueError("Actor identities must be unique and nonempty")
        if len({a.token_sha256 for a in self.actors}) != len(self.actors):
            raise ValueError("Each actor requires a distinct token")

    def identify(self, token: str):
        if len(token) < 24 or len(token) > 256:
            return None
        fingerprint = hashlib.sha256(token.encode()).hexdigest()
        found = None
        for actor in self.actors:
            if hmac.compare_digest(fingerprint, actor.token_sha256):
                found = actor
        return found
