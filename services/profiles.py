"""Serviço responsável por carregar e persistir perfis de servidor em JSON."""
from __future__ import annotations

import json
from pathlib import Path

from models.profile import Profile

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PROFILES_FILE = CONFIG_DIR / "profiles.json"


class ProfileManager:
    """Gerencia CRUD de perfis de servidor, persistidos em config/profiles.json."""

    def __init__(self, file_path: Path = PROFILES_FILE):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._profiles: list[Profile] = []
        self.load()

    # ---------- Persistência ----------

    def load(self) -> list[Profile]:
        if not self.file_path.exists():
            self._profiles = []
            self.save()
            return self._profiles

        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._profiles = [Profile.from_dict(p) for p in data]
        return self._profiles

    def save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in self._profiles], f, indent=2, ensure_ascii=False)

    # ---------- CRUD ----------

    def list_profiles(self) -> list[Profile]:
        return list(self._profiles)

    def get(self, profile_id: str) -> Profile | None:
        return next((p for p in self._profiles if p.id == profile_id), None)

    def add(self, profile: Profile) -> None:
        self._profiles.append(profile)
        self.save()

    def update(self, profile: Profile) -> None:
        for i, p in enumerate(self._profiles):
            if p.id == profile.id:
                self._profiles[i] = profile
                break
        self.save()

    def remove(self, profile_id: str) -> None:
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        self.save()

    def export_to(self, destination: Path) -> None:
        """Exporta os perfis em formato JSON, incluindo todos os campos configurados."""
        with open(destination, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in self._profiles], f, indent=2, ensure_ascii=False)
