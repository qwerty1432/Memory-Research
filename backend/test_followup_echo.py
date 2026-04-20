"""Regression tests for guided follow-up echo stripping."""
import unittest
from unittest.mock import patch

from app import prompt_builder


class FollowupEchoTests(unittest.IsolatedAsyncioTestCase):
    async def test_strips_regarding_prefix_with_full_topic(self):
        topic = (
            "This one's fun -- imagine you could invite absolutely anyone to dinner. "
            "Living, historical, fictional, anyone at all. Who would you pick, and what "
            "would you want to talk about with them?"
        )
        state = {
            "relevance_score": 2,
            "effort_score": 2,
            "outcome": "needs_clarifying_followup",
            "followup_question": (
                f"Regarding {topic.lower()}, that's an interesting choice! "
                "What specifically about Carl Sagan's views would you want to discuss?"
            ),
        }
        with patch("app.prompt_builder.assess_guided_turn", return_value=state):
            followup, result = await prompt_builder.maybe_build_followup_override(
                last_assistant_prompt="",
                user_message="carl sagan and his view on earth",
                current_required_prompt=topic,
                followups_used_for_prompt=0,
                used_followups_for_prompt=[],
                skip_confirmation_sent=False,
                pending_skip_confirmation=False,
            )
        self.assertIsNotNone(followup)
        self.assertIn("What specifically about Carl Sagan's views", followup)
        self.assertNotIn("Regarding", followup)
        self.assertNotIn("imagine you could invite absolutely anyone", followup.lower())
        self.assertEqual(result["followup_question"], followup)

    async def test_keeps_non_echo_followup(self):
        topic = "What would constitute a perfect day for you?"
        state = {
            "relevance_score": 2,
            "effort_score": 2,
            "outcome": "needs_clarifying_followup",
            "followup_question": "What part of that day feels most meaningful to you?",
        }
        with patch("app.prompt_builder.assess_guided_turn", return_value=state):
            followup, _ = await prompt_builder.maybe_build_followup_override(
                last_assistant_prompt="",
                user_message="good nutrition",
                current_required_prompt=topic,
                followups_used_for_prompt=0,
                used_followups_for_prompt=[],
                skip_confirmation_sent=False,
                pending_skip_confirmation=False,
            )
        self.assertEqual(followup, "What part of that day feels most meaningful to you?")

    async def test_echo_only_followup_falls_back(self):
        topic = "What is your favorite holiday? Why?"
        state = {
            "relevance_score": 1,
            "effort_score": 1,
            "outcome": "needs_clarifying_followup",
            "followup_question": f"Regarding {topic.lower()},",
        }
        with patch("app.prompt_builder.assess_guided_turn", return_value=state):
            followup, result = await prompt_builder.maybe_build_followup_override(
                last_assistant_prompt="",
                user_message="winter",
                current_required_prompt=topic,
                followups_used_for_prompt=0,
                used_followups_for_prompt=[],
                skip_confirmation_sent=False,
                pending_skip_confirmation=False,
            )
        self.assertEqual(followup, "What's one thing that first comes to mind for you?")
        self.assertEqual(result["followup_question"], followup)

    async def test_used_followup_dedupe_runs_after_normalization(self):
        topic = "What would constitute a perfect day for you?"
        state = {
            "relevance_score": 1,
            "effort_score": 1,
            "outcome": "needs_clarifying_followup",
            "followup_question": (
                f"Regarding {topic.lower()}, What's a concrete example that comes to mind?"
            ),
        }
        with patch("app.prompt_builder.assess_guided_turn", return_value=state):
            followup, _ = await prompt_builder.maybe_build_followup_override(
                last_assistant_prompt="",
                user_message="healthy and productive",
                current_required_prompt=topic,
                followups_used_for_prompt=1,
                used_followups_for_prompt=[
                    "what's a concrete example that comes to mind?",
                    "i'm curious -- what's one specific thing that stands out to you about what would constitute a perfect day for you??",
                ],
                skip_confirmation_sent=False,
                pending_skip_confirmation=False,
            )
        self.assertEqual(followup, "If you picture it vividly, what detail jumps out first?")


if __name__ == "__main__":
    unittest.main()
