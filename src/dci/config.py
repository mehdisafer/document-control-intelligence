"""Explicit, bounded configuration. No provider or credential auto-discovery."""

import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    home: Path = Path(".data")
    auth_file: Path | None = None
    profile: Literal["baseline", "local-linear", "local-llm"] = "baseline"
    model_path: Path | None = None
    llm_config_file: Path | None = None
    max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    max_pages: int = Field(default=20, ge=1, le=100)
    parser_seconds: int = Field(default=45, ge=1, le=180)
    parser_memory_mb: int = Field(default=768, ge=256, le=4096)
    max_case_documents: int = Field(default=64, ge=3, le=200)
    max_document_versions: int = Field(default=20, ge=1, le=100)
    max_case_bytes: int = Field(default=100 * 1024 * 1024, ge=1048576, le=1024 * 1024 * 1024)
    max_pending: int = Field(default=64, ge=1, le=1000)
    max_workers: int = Field(default=2, ge=1, le=8)
    max_attempts: int = Field(default=3, ge=1, le=5)
    lease_seconds: int = Field(default=240, ge=10, le=900)
    retry_seconds: int = Field(default=2, ge=0, le=60)
    retention_days: int = Field(default=90, ge=1, le=3650)
    batch_size: int = Field(default=4, ge=1, le=32)

    @model_validator(mode="after")
    def check_budgets(self):
        if self.lease_seconds <= self.parser_seconds + 10:
            raise ValueError("lease_seconds must exceed parser_seconds by more than 10 seconds")
        if self.profile == "local-linear" and self.model_path is None:
            raise ValueError("local-linear requires model_path")
        if self.profile == "local-llm" and self.llm_config_file is None:
            raise ValueError("local-llm requires llm_config_file")
        return self

    @classmethod
    def from_env(cls):
        file = os.environ.get("DCI_CONFIG")
        data = json.loads(Path(file).read_text()) if file else {}
        for variable, key in [("DCI_HOME", "home"), ("DCI_AUTH_FILE", "auth_file")]:
            if variable in os.environ:
                data[key] = os.environ[variable]
        return cls.model_validate(data)

    def processing_policy(self):
        from .parsing import runtime_version
        from . import __version__
        data = self.model_dump(mode="json", exclude={"home", "auth_file", "max_pending",
                                "max_workers", "batch_size", "retention_days"})
        data["application_version"] = __version__
        data["parser_runtime"] = runtime_version()
        # Bind model/config bytes. A queued job cannot silently switch model versions.
        for key in ("model_path", "llm_config_file"):
            path = getattr(self, key)
            data[key] = hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None
        if self.profile == "local-llm":
            # A queued document must not silently cross a Qwen prompt or
            # executable field-contract edit without a package version bump.
            # Store only source hashes and public identities, not raw secrets.
            from . import extraction, llm

            data["local_llm_request_identity"] = {
                "prompt_version": llm.PROMPT_VERSION,
                "prompt_sha256": hashlib.sha256(llm.PROMPT.encode("utf-8")).hexdigest(),
                "model_sha256": llm.MODEL_SHA256,
                "runtime_binary_sha256": llm.RUNTIME_BINARY_SHA256,
                "llm_source_sha256": hashlib.sha256(Path(llm.__file__).read_bytes()).hexdigest(),
                "extraction_source_sha256": hashlib.sha256(
                    Path(extraction.__file__).read_bytes()).hexdigest(),
            }
        return data

    def policy_digest(self):
        return hashlib.sha256(json.dumps(self.processing_policy(), sort_keys=True).encode()).hexdigest()
