from __future__ import annotations

import logging
from typing import Literal

from backend.core.constants import DISTRACTION_KEYWORDS, STUDY_KEYWORDS
from backend.services.database import DatabaseManager
from backend.services.policy import PolicyManager

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


class ClassificationResult(dict):
    pass


class StudyClassifier:
    def __init__(self, db: DatabaseManager, policy: PolicyManager) -> None:
        self.db = db
        self.policy = policy

    def classify(self, url: str, title: str = "", page_text: str = "") -> ClassificationResult:
        allowed, matched_domain = self.policy.is_domain_allowed(url)
        if matched_domain:
            return ClassificationResult(
                category="STUDY" if allowed else "DISTRACTION",
                reason=f"Matched {'allow' if allowed else 'block'} rule: {matched_domain}",
                confidence=1.0,
                source="rule",
                matched_rule=matched_domain,
            )

        text = f"{title} {url} {page_text}".lower()
        study_score = sum(1 for keyword in STUDY_KEYWORDS if keyword in text)
        distraction_score = sum(1 for keyword in DISTRACTION_KEYWORDS if keyword in text)

        if study_score > distraction_score and study_score > 0:
            return ClassificationResult(
                category="STUDY",
                reason="Keyword classifier identified study-oriented content",
                confidence=min(0.55 + study_score * 0.08, 0.95),
                source="keyword",
                matched_rule=None,
            )
        if distraction_score >= study_score and distraction_score > 0:
            return ClassificationResult(
                category="DISTRACTION",
                reason="Keyword classifier identified distracting content",
                confidence=min(0.55 + distraction_score * 0.08, 0.95),
                source="keyword",
                matched_rule=None,
            )

        if self.db.get_setting("use_openai", False):
            ai_result = self._classify_with_openai(url, title, page_text)
            if ai_result:
                return ai_result

        return ClassificationResult(
            category="DISTRACTION",
            reason="Unknown content defaults to blocked during focus mode",
            confidence=0.51,
            source="default",
            matched_rule=None,
        )

    def _classify_with_openai(
        self,
        url: str,
        title: str,
        page_text: str,
    ) -> ClassificationResult | None:
        api_key = self.db.get_setting("openai_api_key", "")
        model = self.db.get_setting("openai_model", "gpt-4.1-mini")
        if not api_key or OpenAI is None:
            return None
        try:
            client = OpenAI(api_key=api_key)
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Classify browser content for a study lock system. "
                            "Return only STUDY or DISTRACTION."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"URL: {url}\nTitle: {title}\nText: {page_text[:1200]}",
                    },
                ],
                max_output_tokens=5,
            )
            output = (response.output_text or "").strip().upper()
            category: Literal["STUDY", "DISTRACTION"] = (
                "STUDY" if "STUDY" in output else "DISTRACTION"
            )
            return ClassificationResult(
                category=category,
                reason=f"OpenAI classifier decision: {category}",
                confidence=0.8,
                source="openai",
                matched_rule=None,
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("OpenAI classification failed: %s", exc)
            self.db.log_event("openai_error", "OpenAI classification failed", {"error": str(exc)})
            return None
