import os
import json
from typing import Literal
from . import prompt_store


def get_phase_prompts(phase: int) -> list[str]:
    cfg = prompt_store.get_config()
    return cfg.get("phase_question_banks", {}).get(str(phase), [])


def get_phase_opening_message(phase: int) -> str:
    cfg = prompt_store.get_config()
    prompts = get_phase_prompts(phase)
    opening_msgs = cfg.get("phase_opening_messages", {})

    if not prompts:
        return opening_msgs.get("fallback", "Hey! I'm really glad you're here. Feel free to share whatever's on your mind.")

    template = opening_msgs.get(str(phase), "")
    if not template:
        return opening_msgs.get("fallback", "Hey! I'm really glad you're here. Feel free to share whatever's on your mind.")

    return template.replace("{first_question}", prompts[0])


def _get_cross_phase_bridge_instruction(next_prompt: str) -> str:
    cfg = prompt_store.get_config()
    bridge_map = cfg.get("bridge_instructions", {})
    normalized = (next_prompt or "").strip().lower()
    return bridge_map.get(normalized, "")


def build_phase_guided_messages(
    *,
    context: str,
    user_message: str,
    condition: str,
    phase: int,
    prompts_answered: int,
    total_prompts: int,
    next_prompt: str,
) -> list[dict]:
    cfg = prompt_store.get_config()
    system_template = cfg.get("guided_system_prompt", "")
    system_prompt = system_template.replace("{condition}", condition)

    bridge_instruction = _get_cross_phase_bridge_instruction(next_prompt)
    progress_prompt = (
        f"[Internal — never quote or show this block to the user] "
        f"Progress: {prompts_answered}/{total_prompts} topics covered. "
        f"Next topic to weave into your reply: {next_prompt}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if context.strip():
        messages.append(
            {
                "role": "system",
                "content": f"Context from previous conversations:\n{context}",
            }
        )
        if bridge_instruction:
            messages.append({"role": "system", "content": bridge_instruction})
    messages.append({"role": "system", "content": progress_prompt})
    messages.append(
        {
            "role": "system",
            "content": (
                "Scope: The only new substantive topic you may introduce is the single line "
                "quoted in the internal block above. Do not preview, reference, or allude to "
                "any other upcoming interview topics that are not in that line."
            ),
        }
    )
    messages.append({"role": "user", "content": user_message})
    return messages


def build_phase_completion_messages(*, context: str, user_message: str, phase: int) -> list[dict]:
    cfg = prompt_store.get_config()
    system_template = cfg.get("phase_completion_prompt", "")
    system_prompt = system_template.replace("{phase}", str(phase))

    messages = [{"role": "system", "content": system_prompt}]
    if context.strip():
        messages.append(
            {
                "role": "system",
                "content": f"Context from previous conversations:\n{context}",
            }
        )
    messages.append({"role": "user", "content": user_message})
    return messages


def build_messages(context: str, user_message: str) -> list[dict]:
    cfg = prompt_store.get_config()
    tone = (os.getenv("CHAT_TONE") or "extroverted").strip().lower()
    if tone == "neutral":
        system_prompt = cfg.get("free_chat_prompt_neutral", "You are a friendly AI companion.")
    else:
        system_prompt = cfg.get("free_chat_prompt_extroverted", "You are a warm AI companion.")

    messages = [{"role": "system", "content": system_prompt}]

    if context.strip():
        messages.append({
            "role": "system",
            "content": f"Context from previous conversations:\n{context}"
        })

    messages.append({"role": "user", "content": user_message})
    return messages


def user_requests_skip_topic(user_message: str) -> bool:
    """
    True if the participant clearly wants to skip the current topic / not answer.
    Checked before generic short-answer follow-ups so 'skip' is not treated as vague.
    """
    s = (user_message or "").strip().lower()
    if not s:
        return False
    if s in {
        "skip",
        "pass",
        "next",
        "next question",
        "skip this",
        "skip this question",
        "skip question",
        "n/a",
        "na",
        "no comment",
        "no answer",
    }:
        return True
    if "next question" in s or "move on" in s or "skip this" in s:
        return True
    if "don't want to answer" in s or "dont want to answer" in s:
        return True
    if "rather not" in s and ("answer" in s or "say" in s or "share" in s):
        return True
    return False


def user_message_suggests_ambiguous_skip(user_message: str) -> bool:
    """
    True when the participant may want to skip/move on, but did not say so clearly
    enough for user_requests_skip_topic. Used to ask a one-time skip vs continue check.
    Not triggered for very short generic replies (those get normal nudges instead).
    """
    if user_requests_skip_topic(user_message):
        return False
    s = (user_message or "").strip().lower()
    if not s or len(s) < 8:
        return False
    hints = (
        "rather not",
        "prefer not to",
        "uncomfortable",
        "something else",
        "different question",
        "another question",
        "another topic",
        "different topic",
        "not interested in this",
        "not interested in that",
        "don't want to get into",
        "dont want to get into",
        "don't want to talk about",
        "dont want to talk about",
        "can we skip",
        "can we move",
        "change the subject",
        "talk about something else",
        "don't know if i want",
        "dont know if i want",
        "not sure i want to answer",
        "hard to answer this",
        "don't feel comfortable",
        "dont feel comfortable",
        "pass on this",
        "leave this one",
    )
    return any(h in s for h in hints)


def get_skip_confirmation_prompt_text() -> str:
    cfg = prompt_store.get_config()
    default = (
        "I'm not totally sure I understood — were you hoping to move on to the **next "
        "question**, or would you like to **stay on this one** and share more when you're "
        "ready? Either is fine. You can say **next** to skip, or **keep going** to stay."
    )
    return str(cfg.get("skip_confirmation_prompt") or default).strip() or default


def classify_skip_confirmation_reply(user_message: str) -> Literal["advance", "continue", "unclear"]:
    """
    After we asked skip vs continue, interpret the participant's reply.
    """
    if user_requests_skip_topic(user_message):
        return "advance"
    s = (user_message or "").strip().lower()
    if not s:
        return "unclear"
    # Bare affirmatives are ambiguous (we offered both skip and stay); fall through to normal handling.
    if s in {"no", "nah", "nope", "n"}:
        return "continue"
    if "go ahead" in s or "the next one" in s or "next question" in s or "skip it" in s:
        return "advance"
    if "don't skip" in s or "dont skip" in s or "not skip" in s:
        return "continue"
    if (
        "keep going" in s
        or "stay on" in s
        or "stay here" in s
        or "this question" in s
        or "this topic" in s
        or "same question" in s
        or "want to continue" in s
        or "rather stay" in s
    ):
        return "continue"
    if s == "next" or s.startswith("next ") or s.endswith(" next"):
        return "advance"
    if s in {"keep", "stay", "continue"}:
        return "continue"
    return "unclear"


def _is_generic_or_too_short(user_message: str, *, min_words: int) -> bool:
    msg = (user_message or "").strip()
    if not msg:
        return True
    words = [w for w in msg.split() if w.strip()]
    if len(words) < min_words:
        return True
    generic = {
        "idk",
        "i dont know",
        "i don't know",
        "not sure",
        "n/a",
        "na",
        "ok",
        "okay",
        "fine",
        "good",
    }
    normalized = " ".join(words).lower()
    return normalized in generic


async def assess_effort_relevance(
    last_assistant_prompt: str | None,
    user_message: str,
) -> dict:
    from .genai_client import call_genai

    cfg = prompt_store.get_config()
    user_template = cfg.get("effort_assessment_user_template", "")
    prompt = user_template.replace(
        "{last_assistant_prompt}", json.dumps((last_assistant_prompt or "").strip()[:800])
    ).replace(
        "{user_response}", json.dumps((user_message or "").strip()[:800])
    )

    system_content = cfg.get("effort_assessment_system", "You output strict JSON only.")
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt},
    ]

    try:
        raw = await call_genai(messages, stream=False, temperature=0.0, max_tokens=180)
    except Exception:
        return {
            "relevance_score": 2,
            "effort_score": 2,
            "needs_followup": False,
            "followup_question": "",
            "timeout_fallback": True,
        }
    raw = (raw or "").strip()

    try:
        data = json.loads(raw)
    except Exception:
        return {
            "relevance_score": 2,
            "effort_score": 2,
            "needs_followup": False,
            "followup_question": "",
            "parse_error": True,
            "raw_preview": raw[:200],
        }

    def _clamp_int(v: object, lo: int, hi: int, default: int) -> int:
        try:
            iv = int(v)  # type: ignore[arg-type]
        except Exception:
            return default
        return max(lo, min(hi, iv))

    relevance = _clamp_int(data.get("relevance_score"), 1, 3, 2)
    effort = _clamp_int(data.get("effort_score"), 1, 3, 2)
    needs_followup = bool(data.get("needs_followup"))
    followup = str(data.get("followup_question") or "")
    followup = followup.strip()
    if not needs_followup:
        followup = ""
    else:
        if len(followup) > 220:
            followup = followup[:220].rstrip()

    return {
        "relevance_score": relevance,
        "effort_score": effort,
        "needs_followup": needs_followup,
        "followup_question": followup,
    }


async def maybe_build_followup_override(
    last_assistant_prompt: str | None,
    user_message: str,
    *,
    current_required_prompt: str | None = None,
    followups_used_for_prompt: int = 0,
    used_followups_for_prompt: list[str] | None = None,
    skip_confirmation_sent: bool = False,
) -> tuple[str | None, dict | None]:
    """
    Evaluate sufficiency of user response and optionally return a follow-up question.

    Decision policy:
    - Very short/generic response + under cap: return a conversational follow-up
    - Very short/generic + at cap: return None (advance to next topic)
    - Substantive response: use LLM to assess; only follow up if truly evasive
    - Sufficient: return None (advance immediately)
    """
    cfg = prompt_store.get_config()
    max_followups = 3
    used_followups = [s.strip().lower() for s in (used_followups_for_prompt or []) if str(s).strip()]
    min_words = 5

    if user_requests_skip_topic(user_message):
        return None, {
            "relevance_score": 2,
            "effort_score": 2,
            "needs_followup": False,
            "followup_question": "",
            "user_skip": True,
        }

    if not skip_confirmation_sent and user_message_suggests_ambiguous_skip(user_message):
        followup_text = get_skip_confirmation_prompt_text()
        return followup_text, {
            "relevance_score": 2,
            "effort_score": 2,
            "needs_followup": True,
            "followup_question": followup_text,
            "rule_based": True,
            "skip_confirmation_issued": True,
        }

    if _is_generic_or_too_short(user_message, min_words=min_words):
        if followups_used_for_prompt < max_followups:
            if current_required_prompt:
                followup_variants = list(cfg.get("followup_variants_with_prompt", [
                    "No worries! Take your time with this one. What first comes to mind when you think about it?",
                    "I'm curious to hear your take -- even a quick thought would be great!",
                    "That's okay! Is there anything at all that stands out to you about this?",
                ]))
            else:
                followup_variants = list(cfg.get("followup_variants_without_prompt", [
                    "No rush! What's the first thing that comes to mind?",
                    "I'm curious to hear more -- even a quick thought!",
                    "That's okay! Anything at all stand out to you?",
                ]))
            ordered = [
                followup_variants[(followups_used_for_prompt + i) % len(followup_variants)]
                for i in range(len(followup_variants))
            ]
            followup_text = ""
            for cand in ordered:
                if cand.strip().lower() not in used_followups:
                    followup_text = cand
                    break
            if not followup_text:
                followup_text = ordered[0]
            return followup_text, {
                "relevance_score": 2,
                "effort_score": 1,
                "needs_followup": True,
                "followup_question": followup_text,
                "rule_based": True,
            }
        else:
            return None, {
                "relevance_score": 2,
                "effort_score": 1,
                "needs_followup": False,
                "followup_question": "",
                "rule_based": True,
                "followup_cap_reached": True,
            }

    if followups_used_for_prompt < max_followups:
        effort_result = await assess_effort_relevance(last_assistant_prompt, user_message)

        if effort_result.get("needs_followup", False):
            followup_question = effort_result.get("followup_question", "").strip()
            if followup_question:
                if current_required_prompt and current_required_prompt.lower() not in followup_question.lower():
                    followup_question = f"Regarding {current_required_prompt.lower()}, {followup_question}"

                normalized = followup_question.strip().lower()
                if normalized in used_followups:
                    if current_required_prompt:
                        fallbacks = [
                            f"I'm curious -- what's one specific thing that stands out to you about {current_required_prompt.lower()}?",
                            f"What's a concrete example that comes to mind?",
                            f"If you picture it vividly, what detail jumps out first?",
                        ]
                    else:
                        fallbacks = [
                            "What's one specific thing that stands out?",
                            "What's a concrete example that comes to mind?",
                            "If you picture it vividly, what jumps out first?",
                        ]
                    for fb in fallbacks:
                        if fb.strip().lower() not in used_followups:
                            followup_question = fb
                            effort_result["followup_question"] = followup_question
                            break
                return followup_question, effort_result

        return None, effort_result
    else:
        effort_result = await assess_effort_relevance(last_assistant_prompt, user_message)
        effort_result["needs_followup"] = False
        effort_result["followup_question"] = ""
        effort_result["followup_cap_reached"] = True
        return None, effort_result


async def extract_memories_from_conversation(
    user_message: str,
    existing_memories: list[str] = None
) -> list[str]:
    """
    Extract potential memory candidates from user message using LLM.

    CRITICAL: Only extracts from the user's message, NOT from assistant responses or inferences.
    """
    cfg = prompt_store.get_config()
    existing_context = ""
    if existing_memories:
        existing_context = "\n\nExisting memories (DO NOT extract these again):\n" + "\n".join(f"- {mem}" for mem in existing_memories[:20])

    user_template = cfg.get("memory_extraction_user_template", "")
    extraction_prompt = user_template.replace(
        "{user_message}", user_message
    ).replace(
        "{existing_context}", existing_context
    )

    system_content = cfg.get("memory_extraction_system",
        "You are a memory extraction assistant. Extract ONLY factual information that the user explicitly stated.")

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": extraction_prompt},
    ]

    from .genai_client import call_genai

    try:
        response = await call_genai(messages, stream=False, temperature=0.1, max_tokens=200)

        memories = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line.lower() != "none" and line.startswith("User"):
                memory_text = line
                if len(memory_text) > 200:
                    memory_text = memory_text[:200]
                memories.append(memory_text)

        return memories
    except Exception as e:
        print(f"Memory extraction error: {e}")
        return []
