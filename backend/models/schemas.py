from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BrowserEvaluationRequest(BaseModel):
    url: str
    title: str = ""
    page_text: str = ""
    source: str = "chrome"


class BrowserEvaluationResponse(BaseModel):
    decision: Literal["ALLOW", "BLOCK"]
    category: Literal["STUDY", "DISTRACTION"]
    reason: str
    matched_rule: str | None = None
    confidence: float = 0.0


class SessionStartRequest(BaseModel):
    duration_minutes: int = Field(ge=1, le=360)
    break_minutes: int = Field(default=15, ge=1, le=120)
    frozen_mode: bool = True
    strict_whitelist: bool = True


class PasswordUpdateRequest(BaseModel):
    current_password: str = ""
    new_password: str = Field(min_length=4, max_length=128)


class RuleItem(BaseModel):
    value: str
    rule_type: Literal["app", "site"]
    action: Literal["allow", "block"]


class RulesResponse(BaseModel):
    allowed_apps: list[str]
    blocked_apps: list[str]
    allowed_sites: list[str]
    blocked_sites: list[str]


class SessionStateResponse(BaseModel):
    is_active: bool
    is_break: bool
    frozen_mode: bool
    strict_whitelist: bool
    end_time: str | None
    seconds_remaining: int
    session_id: int | None


class SettingsPayload(BaseModel):
    require_admin: bool
    block_task_manager: bool
    start_with_windows: bool
    use_openai: bool
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"


class StatsResponse(BaseModel):
    daily_minutes: int
    weekly_minutes: int
    streak_days: int
    distraction_attempts_today: int
    sessions_completed_today: int
    recent_events: list[dict[str, Any]]
