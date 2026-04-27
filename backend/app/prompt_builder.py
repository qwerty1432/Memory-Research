import os
import json
import re
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


def get_phase_opening_message_for_question(phase: int, first_question: str | None) -> str:
    """Return opening message, injecting an explicit first question when provided."""
    cfg = prompt_store.get_config()
    opening_msgs = cfg.get("phase_opening_messages", {})
    template = opening_msgs.get(str(phase), "")
    fallback = opening_msgs.get(
        "fallback", "Hey! I'm really glad you're here. Feel free to share whatever's on your mind."
    )
    if not template:
        return fallback
    question = (first_question or "").strip()
    if not question:
        return get_phase_opening_message(phase)
    return template.replace("{first_question}", question)


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
    current_prompt: str,
    followups_used_for_prompt: int = 0,
    min_followups_before_advance: int = 2,
    transition_prompt: str | None = None,
) -> list[dict]:
    cfg = prompt_store.get_config()
    system_template = cfg.get("guided_system_prompt", "")
    system_prompt = system_template.replace("{condition}", condition)

    transition_allowed = followups_used_for_prompt >= min_followups_before_advance
    target_prompt = (transition_prompt or current_prompt).strip()
    bridge_instruction = _get_cross_phase_bridge_instruction(target_prompt)
    if transition_allowed:
        progress_prompt = (
            f"[Internal — never quote or show this block to the user] "
            f"Progress: {prompts_answered}/{total_prompts} topics covered. "
            f"Topic to weave into your reply: {target_prompt}"
        )
    else:
        progress_prompt = (
            f"[Internal — never quote or show this block to the user] "
            f"Progress: {prompts_answered}/{total_prompts} topics covered. "
            f"Current topic to stay on: {current_prompt}"
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
    if not transition_allowed:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Do not move to a new scripted topic yet. Ask a clarifying follow-up on the current "
                    "topic and stay anchored to it."
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


def get_skip_confirmation_prompt_text() -> str:
    cfg = prompt_store.get_config()
    default = (
        "I'm not totally sure I understood — were you hoping to move on to the next "
        "question, or would you like to stay on this one and share more when you're "
        "ready? Either is fine. You can say next to skip, or keep going to stay."
    )
    return str(cfg.get("skip_confirmation_prompt") or default).strip() or default


def _clamp_score_int(v: object, lo: int, hi: int, default: int) -> int:
    try:
        iv = int(v)  # type: ignore[arg-type]
    except Exception:
        return default
    return max(lo, min(hi, iv))


def _normalize_assessment_outcome(raw: str) -> str:
    """Normalize model output to snake_case outcome id."""
    s = (raw or "").strip().lower().replace("-", "_")
    s = re.sub(r"\s+", "_", s)
    aliases = {
        "needs_follow_up": "needs_clarifying_followup",
        "need_clarifying_followup": "needs_clarifying_followup",
        "clarifying_followup": "needs_clarifying_followup",
        "skip_confirmation": "offer_skip_confirmation",
        "ambiguous_skip": "offer_skip_confirmation",
        "skip": "explicit_skip",
        "advance": "pending_advance",
        "stay": "pending_stay",
        "continue": "pending_stay",
    }
    return aliases.get(s, s)


def _normalize_text_for_match(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[\W_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _content_tokens(text: str) -> list[str]:
    t = _normalize_text_for_match(text)
    if not t:
        return []
    stop = {
        "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "i", "you", "your", "my", "it", "that", "this",
    }
    return [tok for tok in t.split() if len(tok) >= 3 and tok not in stop]


def _looks_generic_followup(text: str) -> bool:
    t = _normalize_text_for_match(text)
    if not t:
        return True
    generic_markers = (
        "tell me more",
        "say more",
        "share more",
        "anything else",
        "what stands out",
        "what comes to mind",
        "can you elaborate",
        "could you elaborate",
        "please elaborate",
        "provide more detail",
        "in what way",
        "could you clarify",
        "would you clarify",
    )
    return any(m in t for m in generic_markers)


def _includes_user_detail(followup_text: str, user_message: str) -> bool:
    fq = _normalize_text_for_match(followup_text)
    um = _normalize_text_for_match(user_message)
    if not fq or not um:
        return False
    # Strong check for very short user replies (e.g., "friends", "christmas").
    if len(um.split()) <= 2:
        return um in fq
    # Otherwise token overlap is enough for anchoring.
    user_tokens = set(_content_tokens(user_message))
    follow_tokens = set(_content_tokens(followup_text))
    return bool(user_tokens and (user_tokens & follow_tokens))


async def generate_anchored_followup_for_short_answer(
    *,
    current_required_prompt: str,
    user_message: str,
    last_assistant_prompt: str | None = None,
) -> str | None:
    """
    Generate one LLM follow-up for short valid answers.
    Must reference the user's exact detail; no deterministic template fallback.
    """
    from .genai_client import call_genai

    cfg = prompt_store.get_config()
    base_system = str(
        cfg.get("short_answer_followup_system")
        or (
            "You are a warm, curious conversation partner — not an interviewer. "
            "Respond in plain spoken language. You may give one short genuine reaction, "
            "then exactly one open question. Include the user's detail from their latest answer "
            "and stay on the current topic only."
        )
    ).strip()
    user_payload = (
        "Current topic:\n"
        f"{json.dumps((current_required_prompt or '').strip()[:1200])}\n\n"
        "Last assistant message:\n"
        f"{json.dumps((last_assistant_prompt or '').strip()[:1200])}\n\n"
        "User latest answer:\n"
        f"{json.dumps((user_message or '').strip()[:300])}\n\n"
        "Output rules:\n"
        "- Write only what the user sees.\n"
        "- Include their detail so it's obvious you're responding to what they said.\n"
        "- Optional: one brief warm reaction (one clause), then exactly one question — still only one question total.\n"
        "- Stay on this topic only; do not introduce any other scripted topic.\n"
        "- Sound human and natural; avoid stiff or form-like phrasing.\n"
        "- No bullets, numbering, or meta-commentary."
    )

    async def _ask(system_text: str, *, temperature: float = 0.35) -> str:
        out = await call_genai(
            [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_payload},
            ],
            stream=False,
            temperature=temperature,
            max_tokens=140,
        )
        return (out or "").strip()

    try:
        first = await _ask(base_system, temperature=0.35)
    except Exception:
        return None

    first = _normalize_guided_followup_question(first, current_required_prompt).strip()
    if (
        first
        and _includes_user_detail(first, user_message)
        and not _looks_generic_followup(first)
    ):
        return first[:220].rstrip()

    # One stricter LLM retry (still no deterministic fallback).
    strict_system = (
        base_system
        + "\nStrict requirement: your question must explicitly include the user's exact phrase "
        + json.dumps((user_message or "").strip()[:120])
        + "."
    )
    try:
        second = await _ask(strict_system, temperature=0.15)
    except Exception:
        return None
    second = _normalize_guided_followup_question(second, current_required_prompt).strip()
    if second and _includes_user_detail(second, user_message):
        return second[:220].rstrip()
    return None


def _followup_semantic_signature(text: str) -> str:
    """
    Build a coarse semantic signature for follow-up dedupe.
    Prevents re-asking near-identical prompts with slight wording changes.
    """
    t = _normalize_text_for_match(text)
    if not t:
        return ""
    stop = {
        "i", "m", "im", "you", "your", "to", "the", "a", "an", "and", "or", "but",
        "that", "this", "it", "is", "are", "was", "were", "be", "can", "could",
        "would", "should", "what", "which", "who", "why", "how", "one", "about",
        "share", "specific", "thing", "stands", "out", "curious", "detail", "first",
        "comes", "mind", "picture", "concrete", "example", "understand", "better",
    }
    tokens = [tok for tok in t.split() if tok not in stop and len(tok) > 2]
    if not tokens:
        return t
    # Keep ordered unique tokens to preserve broad intent while dampening style differences.
    seen: set[str] = set()
    uniq: list[str] = []
    for tok in tokens:
        if tok in seen:
            continue
        seen.add(tok)
        uniq.append(tok)
    return " ".join(uniq[:8])


def _strip_leading_echo_prefix(followup_question: str, current_required_prompt: str) -> str:
    """
    Remove lead-ins that restate the full current prompt, e.g.:
    - "Regarding <prompt>, ..."
    - "About <prompt>: ..."
    """
    fq = (followup_question or "").strip()
    prompt = (current_required_prompt or "").strip()
    if not fq or not prompt:
        return fq

    # Remove generic lead-in token first.
    fq = re.sub(
        r"^\s*(?:regarding|about|on|re|for|as for)\b[\s,:-]*",
        "",
        fq,
        flags=re.IGNORECASE,
    ).strip()

    # If the exact topic appears right at the beginning, strip it.
    exact_match = re.search(re.escape(prompt), fq, flags=re.IGNORECASE)
    if exact_match and exact_match.start() <= 3:
        fq = fq[exact_match.end() :].lstrip(" ,:.-")
        return fq.strip()

    prompt_norm = _normalize_text_for_match(prompt)
    if not prompt_norm:
        return fq

    patterns = [
        r"^\s*(?:regarding|about|on|re)\s+(.+?)(?:,\s*|:\s*|-\s*|\.\s+)",
        r"^\s*(?:for|as for)\s+(.+?)(?:,\s*|:\s*|-\s*|\.\s+)",
    ]
    for pattern in patterns:
        m = re.match(pattern, fq, flags=re.IGNORECASE)
        if not m:
            continue
        lead_topic = m.group(1).strip(" \"'`")
        lead_norm = _normalize_text_for_match(lead_topic)
        if lead_norm and (lead_norm in prompt_norm or prompt_norm in lead_norm):
            fq = fq[m.end() :].strip()
            break
    return fq


def _normalize_guided_followup_question(
    followup_question: str,
    current_required_prompt: str | None,
) -> str:
    """
    Reduce echoed topic restatements so follow-ups stay concise.
    """
    fq = (followup_question or "").strip()
    if not fq:
        return ""
    if not current_required_prompt:
        return fq

    topic = current_required_prompt.strip()
    if not topic:
        return fq

    fq = _strip_leading_echo_prefix(fq, topic)
    if not fq:
        return ""

    fq_norm = _normalize_text_for_match(fq)
    topic_norm = _normalize_text_for_match(topic)
    if not fq_norm or not topic_norm:
        return fq

    # If the follow-up is mostly the topic restatement with little/no new content, drop it.
    if topic_norm in fq_norm:
        extra = fq_norm.replace(topic_norm, "").strip()
        if len(extra) < 12:
            return ""
    return fq


def _fallback_unified_state(
    guided_mode: bool,
    pending_skip_confirmation: bool,
    *,
    reason: str,
) -> dict:
    o = "sufficient"
    if pending_skip_confirmation:
        o = "sufficient"
    elif not guided_mode:
        o = "sufficient"
    return {
        "relevance_score": 2,
        "effort_score": 2,
        "outcome": o,
        "followup_question": "",
        "assessment_fallback": True,
        "fallback_reason": reason,
    }


async def assess_guided_turn(
    last_assistant_prompt: str | None,
    user_message: str,
    *,
    guided_mode: bool,
    pending_skip_confirmation: bool,
    skip_confirmation_sent: bool,
    current_required_prompt: str | None,
    followups_used_for_prompt: int,
    max_followups: int = 3,
) -> dict:
    """
    Single LLM call: skip intent, ambiguous skip offer, sufficiency, and follow-up need.
    Used for guided Qualtrics/playground flow and (with guided_mode=False) for legacy free-chat assessments.
    """
    from .genai_client import call_genai

    cfg = prompt_store.get_config()
    user_template = str(cfg.get("guided_turn_assessment_user_template") or "").strip()
    system_content = str(
        cfg.get("guided_turn_assessment_system") or "You output strict JSON only."
    ).strip()
    if not user_template:
        return _fallback_unified_state(guided_mode, pending_skip_confirmation, reason="missing_template")

    at_cap = followups_used_for_prompt >= max_followups
    current_topic = (current_required_prompt or "").strip() or "(open conversation)"

    user_block = user_template.replace("{guided_interview_mode}", "yes" if guided_mode else "no")
    user_block = user_block.replace("{pending_skip_confirmation}", "yes" if pending_skip_confirmation else "no")
    user_block = user_block.replace(
        "{skip_confirmation_sent}", "yes" if skip_confirmation_sent else "no"
    )
    user_block = user_block.replace("{followups_used}", str(followups_used_for_prompt))
    user_block = user_block.replace("{max_followups}", str(max_followups))
    user_block = user_block.replace("{at_followup_cap}", "yes" if at_cap else "no")
    user_block = user_block.replace("{current_topic}", json.dumps(current_topic[:1200]))
    user_block = user_block.replace(
        "{last_assistant_prompt}",
        json.dumps((last_assistant_prompt or "").strip()[:1200]),
    )
    user_block = user_block.replace("{user_response}", json.dumps((user_message or "").strip()[:1200]))

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_block},
    ]

    try:
        raw_text = await call_genai(messages, stream=False, temperature=0.0, max_tokens=520)
    except Exception:
        return _fallback_unified_state(guided_mode, pending_skip_confirmation, reason="api_error")

    raw_text = (raw_text or "").strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text).strip()

    try:
        data = json.loads(raw_text)
    except Exception:
        return _fallback_unified_state(guided_mode, pending_skip_confirmation, reason="json_parse")

    outcome = _normalize_assessment_outcome(str(data.get("outcome") or ""))
    fq = str(data.get("followup_question") or "").strip()
    if len(fq) > 220:
        fq = fq[:220].rstrip()

    rel = _clamp_score_int(data.get("relevance_score"), 1, 3, 2)
    effort = _clamp_score_int(data.get("effort_score"), 1, 3, 2)

    if at_cap and outcome in ("needs_clarifying_followup", "offer_skip_confirmation"):
        outcome = "sufficient"
        fq = ""
    if skip_confirmation_sent and outcome == "offer_skip_confirmation":
        outcome = "sufficient"
        fq = ""

    if pending_skip_confirmation and outcome == "explicit_skip":
        outcome = "pending_advance"

    # Coerce invalid outcomes for mode
    if not guided_mode:
        if outcome not in ("sufficient", "needs_clarifying_followup"):
            outcome = "sufficient"
            fq = ""
    elif pending_skip_confirmation:
        if outcome not in (
            "pending_advance",
            "pending_stay",
            "sufficient",
            "needs_clarifying_followup",
        ):
            outcome = "sufficient"
            fq = ""
    else:
        if outcome not in (
            "explicit_skip",
            "sufficient",
            "needs_clarifying_followup",
            "offer_skip_confirmation",
        ):
            outcome = "sufficient"
            fq = ""

    if outcome != "needs_clarifying_followup":
        fq = ""
    return {
        "relevance_score": rel,
        "effort_score": effort,
        "outcome": outcome,
        "followup_question": fq,
        "unified_assessment": True,
    }


async def assess_effort_relevance(
    last_assistant_prompt: str | None,
    user_message: str,
) -> dict:
    """
    Legacy shape for callers expecting needs_followup + followup_question.
    Uses the same unified assessment in free-chat mode (one LLM call).
    """
    u = await assess_guided_turn(
        last_assistant_prompt,
        user_message,
        guided_mode=False,
        pending_skip_confirmation=False,
        skip_confirmation_sent=False,
        current_required_prompt=None,
        followups_used_for_prompt=0,
        max_followups=3,
    )
    need = u.get("outcome") == "needs_clarifying_followup"
    return {
        "relevance_score": u["relevance_score"],
        "effort_score": u["effort_score"],
        "needs_followup": need,
        "followup_question": u.get("followup_question") or "",
        "unified_assessment": True,
    }


async def maybe_build_followup_override(
    last_assistant_prompt: str | None,
    user_message: str,
    *,
    current_required_prompt: str | None = None,
    followups_used_for_prompt: int = 0,
    used_followups_for_prompt: list[str] | None = None,
    skip_confirmation_sent: bool = False,
    pending_skip_confirmation: bool = False,
) -> tuple[str | None, dict | None]:
    """
    Single LLM assessment (assess_guided_turn) decides skip vs sufficient vs follow-up vs skip-confirm offer.
    """
    max_followups = 3
    used_followups = [s.strip().lower() for s in (used_followups_for_prompt or []) if str(s).strip()]
    used_signatures = {
        _followup_semantic_signature(s)
        for s in used_followups
        if _followup_semantic_signature(s)
    }
    guided_mode = current_required_prompt is not None
    if not guided_mode:
        pending_skip_confirmation = False

    state = await assess_guided_turn(
        last_assistant_prompt,
        user_message,
        guided_mode=guided_mode,
        pending_skip_confirmation=pending_skip_confirmation,
        skip_confirmation_sent=skip_confirmation_sent,
        current_required_prompt=current_required_prompt,
        followups_used_for_prompt=followups_used_for_prompt,
        max_followups=max_followups,
    )

    outcome = str(state.get("outcome") or "sufficient")
    effort_result: dict = {
        "relevance_score": state["relevance_score"],
        "effort_score": state["effort_score"],
        "needs_followup": False,
        "followup_question": "",
        "unified_assessment": True,
        "assessment_outcome": outcome,
    }
    if state.get("assessment_fallback"):
        effort_result["assessment_fallback"] = True
        effort_result["fallback_reason"] = state.get("fallback_reason")

    # Pending skip-dialogue resolutions (same model call)
    if pending_skip_confirmation:
        if outcome == "pending_advance" or outcome == "explicit_skip":
            effort_result["user_skip"] = True
            return None, effort_result
        if outcome == "pending_stay":
            effort_result["resume_after_skip_prompt"] = True
            return None, effort_result
        # sufficient or needs_clarifying_followup: fall through to mapping below

    if guided_mode and outcome == "explicit_skip":
        effort_result["user_skip"] = True
        return None, effort_result

    if guided_mode and outcome == "offer_skip_confirmation":
        followup_text = get_skip_confirmation_prompt_text()
        effort_result["needs_followup"] = True
        effort_result["followup_question"] = followup_text
        effort_result["skip_confirmation_issued"] = True
        return followup_text, effort_result

    if outcome == "needs_clarifying_followup":
        followup_question = (state.get("followup_question") or "").strip()
        if guided_mode:
            followup_question = _normalize_guided_followup_question(
                followup_question, current_required_prompt
            )
        normalized = followup_question.strip().lower()
        followup_sig = _followup_semantic_signature(followup_question)
        if normalized in used_followups or (followup_sig and followup_sig in used_signatures):
            followup_question = ""
        effort_result["needs_followup"] = True
        effort_result["followup_question"] = followup_question
        return (followup_question if followup_question else None), effort_result

    # sufficient (and free-chat sufficient path)
    if followups_used_for_prompt >= max_followups and guided_mode:
        effort_result["followup_cap_reached"] = True
    return None, effort_result


def build_forced_followup_question(
    current_required_prompt: str | None,
    used_followups_for_prompt: list[str] | None = None,
) -> str:
    """Deterministic fallback follow-up when advancing is gated by minimum follow-ups."""
    used = {s.strip().lower() for s in (used_followups_for_prompt or []) if str(s).strip()}
    if current_required_prompt:
        candidates = [
            f"I'm curious -- what's one specific thing that stands out to you about {current_required_prompt.lower()}?",
            "Could you share one concrete example so I can understand that better?",
            "If you picture this clearly, what detail feels most important to you?",
        ]
    else:
        candidates = [
            "I'm curious -- what's one specific detail that stands out to you?",
            "Could you share one concrete example so I can understand that better?",
            "If you picture this clearly, what detail feels most important to you?",
        ]
    for candidate in candidates:
        if candidate.strip().lower() not in used:
            return candidate
    return "What's one thing that first comes to mind for you?"


def build_skip_transition_message(next_topic: str | None) -> str:
    cfg = prompt_store.get_config()
    template = str(
        cfg.get("skip_transition_template")
        or "That's totally fine -- let's talk about this instead: {next_topic}"
    ).strip()
    topic = (next_topic or "").strip()
    if not topic:
        return "That's totally fine. We can move forward whenever you're ready."
    return template.replace("{next_topic}", topic)


def has_natural_language_skip_intent(user_message: str) -> bool:
    """
    Lightweight semantic fallback for skip/move-on intent.
    Used only as a reconciliation layer when LLM assessment is inconsistent.
    """
    t = _normalize_text_for_match(user_message)
    if not t:
        return False

    phrase_hits = [
        "move on",
        "move to the next",
        "next topic",
        "next question",
        "next one",
        "skip this",
        "skip this question",
        "pass on this",
        "rather not answer",
        "dont want to answer",
        "do not want to answer",
        "can we continue",
        "go to the next",
        "continue to the next",
    ]
    if any(p in t for p in phrase_hits):
        return True

    tokens = set(t.split())
    # Conservative lexical fallback: require two-word evidence.
    if "pass" in tokens and ("question" in tokens or "topic" in tokens):
        return True
    if "skip" in tokens and ("question" in tokens or "topic" in tokens or "next" in tokens):
        return True
    return False


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
