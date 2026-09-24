from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import SystemSetting


@dataclass(frozen=True)
class GenerationPolicy:
    per_user_limit: int
    global_limit: int
    window_seconds: int
    max_output_tokens: int


class RuntimeSettingsService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def maintenance_enabled(self) -> bool:
        setting = self.session.scalar(
            select(SystemSetting).where(SystemSetting.key == "maintenance_mode")
        )
        return bool(setting and setting.value is True)

    def generation_policy(self) -> GenerationPolicy:
        values = {
            "generation_rate_limit_per_user": self.settings.generation_rate_limit_per_user,
            "generation_rate_limit_global": self.settings.generation_rate_limit_global,
            "generation_rate_limit_window_seconds": self.settings.generation_rate_limit_window_seconds,
            "generation_max_output_tokens": self.settings.provider_max_output_tokens,
        }
        bounds = {
            "generation_rate_limit_per_user": (1, 1000),
            "generation_rate_limit_global": (1, 10000),
            "generation_rate_limit_window_seconds": (1, 3600),
            "generation_max_output_tokens": (1, 8192),
        }
        for key, default in values.items():
            setting = self.session.scalar(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            if setting is None or isinstance(setting.value, bool):
                continue
            if isinstance(setting.value, int) and bounds[key][0] <= setting.value <= bounds[key][1]:
                values[key] = setting.value
        return GenerationPolicy(
            per_user_limit=values["generation_rate_limit_per_user"],
            global_limit=values["generation_rate_limit_global"],
            window_seconds=values["generation_rate_limit_window_seconds"],
            max_output_tokens=values["generation_max_output_tokens"],
        )
