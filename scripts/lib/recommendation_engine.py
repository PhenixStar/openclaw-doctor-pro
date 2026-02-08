"""Recommendation engine for ClawHub skills."""
from __future__ import annotations

from dataclasses import dataclass

from .clawhub_client import ClawHubClient, SkillInfo
from .config_analyzer import ConfigAnalyzer


@dataclass
class Recommendation:
    """Skill recommendation with score and reason."""
    skill: SkillInfo
    score: float
    reasons: list[str]


class RecommendationEngine:
    """Smart skill recommendation system."""

    # Channel-skill affinity mapping
    CHANNEL_SKILLS = {
        "whatsapp": ["whatsapp-media", "whatsapp-status", "qr-code-gen"],
        "telegram": ["telegram-inline", "telegram-webhooks", "image-gen"],
        "discord": ["discord-voice", "discord-slash", "game-stats"],
        "slack": ["slack-workflows", "slack-apps", "jira-integration"],
        "signal": ["signal-groups", "privacy-tools"],
        "teams": ["teams-meetings", "sharepoint-integration"],
    }

    # Use case keywords
    USE_CASE_KEYWORDS = {
        "calendar": ["calendar", "schedule", "meeting", "event", "reminder"],
        "image": ["image", "photo", "picture", "vision", "ocr", "generation"],
        "code": ["code", "github", "gitlab", "deploy", "ci/cd"],
        "automation": ["workflow", "automation", "task", "schedule"],
        "analytics": ["analytics", "metrics", "stats", "dashboard"],
    }

    def __init__(self):
        """Initialize recommendation engine."""
        self.client = ClawHubClient()
        self.analyzer = ConfigAnalyzer()

    def recommend(
        self,
        channel: str | None = None,
        use_case: str | None = None,
        top: int = 10
    ) -> list[Recommendation]:
        """
        Generate skill recommendations.

        Args:
            channel: Filter by channel name
            use_case: Use case keyword
            top: Maximum results

        Returns:
            List of ranked recommendations
        """
        # Build search query
        query_parts = []
        if channel:
            query_parts.append(channel)
        if use_case:
            query_parts.append(use_case)

        query = " ".join(query_parts) if query_parts else ""

        # Search skills
        skills = self.client.search(query, limit=top * 2)

        # Score and filter
        recommendations = []
        for skill in skills:
            score, reasons = self._score_skill(skill, channel, use_case)
            if score > 0:
                recommendations.append(Recommendation(
                    skill=skill,
                    score=score,
                    reasons=reasons
                ))

        # Sort by score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top]

    def _score_skill(
        self,
        skill: SkillInfo,
        channel: str | None,
        use_case: str | None
    ) -> tuple[float, list[str]]:
        """
        Score skill relevance.

        Args:
            skill: Skill to score
            channel: Channel filter
            use_case: Use case filter

        Returns:
            Tuple of (score, reasons list)
        """
        score = 0.0
        reasons = []

        # Base score from verification and downloads
        if skill.verified:
            score += 2.0
            reasons.append("Verified skill")

        if skill.downloads > 1000:
            score += 1.0
            reasons.append("Popular (1000+ downloads)")
        elif skill.downloads > 100:
            score += 0.5

        # Channel affinity
        if channel:
            channel_lower = channel.lower()
            if channel_lower in self.CHANNEL_SKILLS:
                if any(s in skill.slug for s in self.CHANNEL_SKILLS[channel_lower]):
                    score += 3.0
                    reasons.append(f"Optimized for {channel}")

            if channel_lower in skill.name.lower() or channel_lower in skill.description.lower():
                score += 2.0
                reasons.append(f"Matches {channel} channel")

        # Use case matching
        if use_case:
            use_case_lower = use_case.lower()
            keywords = self.USE_CASE_KEYWORDS.get(use_case_lower, [use_case_lower])

            desc_lower = skill.description.lower()
            matches = sum(1 for kw in keywords if kw in desc_lower)

            if matches > 0:
                score += matches * 1.5
                reasons.append(f"Matches '{use_case}' use case")

        # Tag matching
        if skill.tags:
            if channel and channel.lower() in [t.lower() for t in skill.tags]:
                score += 1.0

            if use_case and use_case.lower() in [t.lower() for t in skill.tags]:
                score += 1.0

        return score, reasons

    def suggest_for_config(self) -> list[Recommendation]:
        """
        Auto-detect channels from config and recommend skills.

        Returns:
            Recommended skills for enabled channels
        """
        enabled_channels = self.analyzer.detect_channels()
        if not enabled_channels:
            return []

        all_recommendations = []
        seen_slugs = set()

        for channel in enabled_channels:
            recs = self.recommend(channel=channel, top=5)
            for rec in recs:
                if rec.skill.slug not in seen_slugs:
                    all_recommendations.append(rec)
                    seen_slugs.add(rec.skill.slug)

        # Re-sort by score
        all_recommendations.sort(key=lambda r: r.score, reverse=True)
        return all_recommendations[:10]

    def check_updates(self) -> list[tuple[SkillInfo, SkillInfo]]:
        """
        Check installed skills for updates.

        Returns:
            List of (installed_skill, latest_skill) tuples needing update
        """
        installed = self.client.list_installed()
        updates_available = []

        for installed_skill in installed:
            latest = self.client.get_skill_info(installed_skill.slug)
            if latest and latest.version != installed_skill.version:
                updates_available.append((installed_skill, latest))

        return updates_available
