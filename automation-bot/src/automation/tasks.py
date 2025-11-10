thonfrom __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from .utils.logger import get_logger
from .utils.proxy_manager import ProxyManager

@dataclass
class ModerationRuleSet:
    banned_words: List[str] = field(default_factory=list)
    warn_threshold: int = 1
    ban_threshold: int = 3

    @classmethod
    def from_settings(cls, settings: dict) -> "ModerationRuleSet":
        moderation_cfg = settings.get("moderation", {})
        return cls(
            banned_words=[w.lower() for w in moderation_cfg.get("banned_words", [])],
            warn_threshold=int(moderation_cfg.get("warn_threshold", 1)),
            ban_threshold=int(moderation_cfg.get("ban_threshold", 3)),
        )

class ModerationEngine:
    def __init__(self, rules: ModerationRuleSet, logger=None):
        self.rules = rules
        self.logger = logger or get_logger()
        self._user_infractions: Dict[str, int] = {}

    def evaluate_message(self, user_id: str, message: str) -> Tuple[str, str | None]:
        """
        Returns (action, reason)
        action one of: "allow", "warn", "delete", "ban"
        """
        lowered = message.lower()
        matched_words = [w for w in self.rules.banned_words if w in lowered]

        if not matched_words:
            self.logger.debug("Message from %s allowed: %s", user_id, message)
            return "allow", None

        count = self._user_infractions.get(user_id, 0) + 1
        self._user_infractions[user_id] = count

        reason = f"Detected banned words: {', '.join(matched_words)} (infractions={count})"

        if count >= self.rules.ban_threshold:
            action = "ban"
        elif count >= self.rules.warn_threshold:
            action = "warn"
        else:
            action = "delete"

        self.logger.info(
            "Moderation action=%s for user=%s; reason=%s; msg=%s",
            action,
            user_id,
            reason,
            message,
        )
        return action, reason

class ModerationTaskRunner:
    def __init__(
        self,
        settings: dict,
        credentials: dict,
        proxy_manager: ProxyManager,
        output_dir: Path,
        logger=None,
    ):
        self.settings = settings
        self.credentials = credentials
        self.proxy_manager = proxy_manager
        self.output_dir = output_dir
        self.logger = logger or get_logger()
        self.engine = ModerationEngine(
            rules=ModerationRuleSet.from_settings(settings),
            logger=self.logger,
        )

    def _simulate_fetch_messages(self) -> List[dict]:
        """
        In a real implementation, this would connect to a device/emulator or Discord API.
        Here we simulate incoming messages for demonstration and testing.
        """
        sample_users = ["u-001", "u-002", "u-003", "u-004"]
        clean_messages = [
            "Hey everyone, hope you're doing well!",
            "Can someone help me with this bug?",
            "Great job on shipping the new feature.",
            "Let's keep this channel clean and productive.",
        ]
        offensive_templates = [
            "You are such a {word}",
            "This server is {word}",
            "{word} message here",
        ]

        banned_words = self.engine.rules.banned_words or ["spam", "idiot", "trash"]
        messages: List[dict] = []

        for _ in range(random.randint(6, 12)):
            user_id = random.choice(sample_users)

            if random.random() < 0.3:
                word = random.choice(banned_words)
                template = random.choice(offensive_templates)
                msg = template.format(word=word)
            else:
                msg = random.choice(clean_messages)

            messages.append(
                {
                    "user_id": user_id,
                    "message": msg,
                    "timestamp": time.time(),
                    "channel": "general",
                }
            )

        self.logger.debug("Simulated %d incoming messages", len(messages))
        return messages

    def _append_results_json(self, records: List[dict]):
        results_path = self.output_dir / "results.json"
        existing: List[dict] = []

        if results_path.exists():
            try:
                existing = json.loads(results_path.read_text(encoding="utf-8") or "[]")
                if not isinstance(existing, list):
                    existing = []
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse existing results.json, overwriting.")

        existing.extend(records)
        results_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        self.logger.debug("Wrote %d records to %s", len(records), results_path)

    def _append_report_csv(self, records: List[dict]):
        report_path = self.output_dir / "report.csv"
        is_new = not report_path.exists()
        with report_path.open("a", encoding="utf-8", newline="") as f:
            if is_new:
                f.write("timestamp,user_id,action,reason,message,channel,proxy\n")
            for rec in records:
                line = (
                    f"{rec['timestamp']},"
                    f"{rec['user_id']},"
                    f"{rec['action']},"
                    f"\"{(rec['reason'] or '').replace('\"', '\"\"')}\","
                    f"\"{rec['message'].replace('\"', '\"\"')}\","
                    f"{rec['channel']},"
                    f"{rec.get('proxy','')}\n"
                )
                f.write(line)
        self.logger.debug("Appended %d records to %s", len(records), report_path)

    def run_moderation_cycle(self):
        """
        Executes a single moderation sweep:
        - Fetches incoming messages (simulated)
        - Evaluates each message against moderation rules
        - Logs decisions
        - Writes structured outputs to JSON and CSV
        """
        self.logger.info("Starting moderation cycle")
        proxy = self.proxy_manager.get_next_proxy()
        if proxy:
            self.logger.info("Using proxy %s", proxy)
        else:
            self.logger.info("Running without proxy")

        messages = self._simulate_fetch_messages()
        output_records: List[dict] = []

        for msg in messages:
            action, reason = self.engine.evaluate_message(msg["user_id"], msg["message"])
            record = {
                "timestamp": msg["timestamp"],
                "user_id": msg["user_id"],
                "message": msg["message"],
                "channel": msg["channel"],
                "action": action,
                "reason": reason,
                "proxy": proxy or "",
            }
            output_records.append(record)

        if output_records:
            self._append_results_json(output_records)
            self._append_report_csv(output_records)

        self.logger.info(
            "Completed moderation cycle; processed=%d",
            len(output_records),
        )