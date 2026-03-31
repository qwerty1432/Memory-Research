import os
import json

PHASE_PROMPT_BANKS: dict[int, list[str]] = {
    1: [
        "What would constitute a perfect day for you?",
        "What is your favorite holiday? Why?",
        "This one's fun -- imagine you could invite absolutely anyone to dinner. Living, historical, fictional, anyone at all. Who would you pick, and what would you want to talk about with them?",
        "For what in your life do you feel most grateful?",
    ],
    2: [
        "Is there something that you've dreamed of doing for a long time? Why haven't you done it?",
        "Tell me your life story in as much detail as possible.",
        "What is the greatest accomplishment of your life?",
        "If you could wake up tomorrow having gained any one quality or ability, what would it be?",
    ],
    3: [
        "What kinds of things tend to get you feeling really down or blue?",
        "If you were to die this evening with no chance to talk to anyone, what would you most regret not having told someone? Why haven't you told them yet?",
        "What aspects of your personality do you dislike, worry about, or see as a limitation?",
        "If a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?",
    ],
}


def get_phase_prompts(phase: int) -> list[str]:
    return PHASE_PROMPT_BANKS.get(phase, [])


def get_phase_opening_message(phase: int) -> str:
    prompts = get_phase_prompts(phase)
    if not prompts:
        return "Hey! I'm really glad you're here. Feel free to share whatever's on your mind."
    if phase == 1:
        return (
            "Hey there! I'm really glad you're here. Think of me as your conversation "
            "partner -- I'm genuinely curious to learn about you.\n\n"
            "We're going to chat through a few topics together, and there's no right or "
            "wrong way to answer. Share as much or as little as you're comfortable with, "
            "and I'll probably ask some follow-up questions just because I find people's "
            "perspectives really interesting.\n\n"
            f"Let's start with something fun: {prompts[0]}"
        )
    if phase == 2:
        return (
            "Great, let's move into our next set of topics! These go a little deeper, "
            "and I'm really looking forward to hearing your thoughts.\n\n"
            f"Here's our first one: {prompts[0]}"
        )
    return (
        "Alright, we're heading into the last stretch! These topics are a bit more personal, "
        "so take your time and share whatever feels right.\n\n"
        f"Here's where we'll start: {prompts[0]}"
    )


def _get_cross_phase_bridge_instruction(next_prompt: str) -> str:
    normalized = (next_prompt or "").strip().lower()
    bridge_map = {
        "is there something that you've dreamed of doing for a long time? why haven't you done it?":
            "If relevant context exists, briefly connect this to the user's earlier 'perfect day' answer or desired quality/ability before asking the required question.",
        "what kinds of things tend to get you feeling really down or blue?":
            "If relevant context exists, briefly connect this to whether their earlier 'perfect day' could help them cope, then ask the required question.",
        "tell me your life story in as much detail as possible.":
            "If relevant context exists, briefly connect this to the earlier favorite holiday as part of their life narrative, then ask the required question.",
        "if you were to die this evening with no chance to talk to anyone, what would you most regret not having told someone? why haven't you told them yet?":
            "If relevant context exists, briefly reference important figures from the earlier life story, then ask the required question.",
        "what is the greatest accomplishment of your life?":
            "If relevant context exists, briefly connect this to the earlier dinner guest (for example as an inspiration), then ask the required question.",
        "what aspects of your personality do you dislike, worry about, or see as a limitation?":
            "If relevant context exists, briefly connect this to challenges faced while achieving their greatest accomplishment, then ask the required question.",
        "if you could wake up tomorrow having gained any one quality or ability, what would it be?":
            "If relevant context exists, briefly connect this to whether their earlier dinner guest embodies that quality, then ask the required question.",
        "if a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?":
            "If relevant context exists, briefly connect this to what they've shared about their personality or regrets, then ask the required question.",
        "for what in your life do you feel most grateful?":
            "If relevant context exists, briefly connect this to their perfect day or favorite holiday, then ask the required question.",
    }
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
    system_prompt = (
        "You are a genuinely curious, warm conversation partner -- not an interviewer or therapist.\n"
        "Your personality: friendly, empathetic, and naturally curious about people. "
        "You listen carefully and respond like a real friend would.\n\n"
        "After reading the user's message, respond naturally:\n"
        "- React to what they shared with genuine interest -- not just generic praise like 'that's great!'\n"
        "- Show you were really listening by referencing a specific detail from their answer.\n"
        "- Then smoothly transition into the next topic (provided below). "
        "Weave it in naturally, like you're continuing a conversation -- never say 'Next question:' or number the questions.\n\n"
        "Important constraints:\n"
        "- Keep your response conversational and under 150 words.\n"
        "- Only ask the one topic/question provided below -- don't add extra questions.\n"
        "- Reference their previous answers only if they appear in the provided context.\n"
        "- Never invent details about the user or claim to remember things not in the context.\n"
        "- Never promise to 'come back to' or 'revisit' a topic.\n"
        "- If their response was emotional or vulnerable, acknowledge that with warmth before moving on.\n"
        f"- Memory condition: {condition}.\n"
    )
    bridge_instruction = _get_cross_phase_bridge_instruction(next_prompt)
    progress_prompt = (
        f"[Internal -- do not mention this to the user] "
        f"Progress: {prompts_answered}/{total_prompts} topics covered.\n"
        f"Next topic to bring up naturally: {next_prompt}"
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
    messages.append({"role": "user", "content": user_message})
    return messages


def build_phase_completion_messages(*, context: str, user_message: str, phase: int) -> list[dict]:
    system_prompt = (
        "You are a warm, friendly conversation partner.\n"
        f"You've just finished chatting through all the topics in this set (phase {phase}).\n"
        "Respond by:\n"
        "1) Reacting genuinely to what they just shared.\n"
        "2) Thanking them warmly for the conversation and clearly letting them know "
        "they can click 'Finish Conversation' below to head back to the survey.\n"
        "Keep it brief and genuine -- no need for a long summary."
    )
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
    tone = (os.getenv("CHAT_TONE") or "extroverted").strip().lower()
    if tone == "neutral":
        system_prompt = (
            "You are a friendly AI companion. Use the provided context to have a natural conversation."
        )
    else:
        system_prompt = (
            "You are a warm, genuinely curious AI companion.\n"
            "Goals:\n"
            "- Be conversational, encouraging, and curious.\n"
            "- Ask clear, open-ended follow-up questions when helpful.\n"
            "- If the user's answer is very short or vague, gently ask for more detail before moving on.\n"
            "- Never pressure the user to disclose; respect boundaries and accept 'I'd rather not say'.\n"
            "- Do not claim to have personal experiences.\n"
            "- Use the provided context if relevant, but do not invent facts.\n"
        )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    if context.strip():
        messages.append({
            "role": "system",
            "content": f"Context from previous conversations:\n{context}"
        })

    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


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

    prompt = f"""You are evaluating a conversation for a research chatbot.

Given:
- Assistant_prompt: {json.dumps((last_assistant_prompt or "").strip()[:800])}
- User_response: {json.dumps((user_message or "").strip()[:800])}

Task:
Return STRICT JSON only (no markdown) with exactly these keys:
- relevance_score: integer 1-3 (1=off-topic, 2=somewhat relevant, 3=clearly relevant)
- effort_score: integer 1-3 (1=very low effort, 2=some detail, 3=thoughtful/detailed)
- needs_followup: boolean
- followup_question: string (a warm, curious follow-up; empty string if needs_followup is false)

Rules for needs_followup:
- Set to false if the user gave a substantive answer (even if brief -- a clear 2-3 sentence answer is sufficient).
- Set to false if the user explicitly declines to answer or says they'd rather not.
- Set to true ONLY if the response is clearly evasive, completely off-topic, or so vague it's impossible to understand what they mean.
- When in doubt, set to false. The goal is natural conversation, not interrogation.

Rules for followup_question (when needs_followup is true):
- Frame it as genuine curiosity, not assessment (e.g., "I'm curious -- what made you think of that?" not "Could you elaborate more?").
- Keep it specific to what they said, not generic.
- Never say you will "come back later" or "revisit".
- Do not include any other keys.
"""

    messages = [
        {"role": "system", "content": "You output strict JSON only."},
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
) -> tuple[str | None, dict | None]:
    """
    Evaluate sufficiency of user response and optionally return a follow-up question.

    Decision policy:
    - Very short/generic response + under cap: return a conversational follow-up
    - Very short/generic + at cap: return None (advance to next topic)
    - Substantive response: use LLM to assess; only follow up if truly evasive
    - Sufficient: return None (advance immediately)
    """
    max_followups = 3
    used_followups = [s.strip().lower() for s in (used_followups_for_prompt or []) if str(s).strip()]
    min_words = 5
    if _is_generic_or_too_short(user_message, min_words=min_words):
        if followups_used_for_prompt < max_followups:
            if current_required_prompt:
                followup_variants = [
                    f"No worries! Take your time with this one. What first comes to mind when you think about it?",
                    f"I'm curious to hear your take -- even a quick thought would be great!",
                    f"That's okay! Is there anything at all that stands out to you about this?",
                ]
            else:
                followup_variants = [
                    "No rush! What's the first thing that comes to mind?",
                    "I'm curious to hear more -- even a quick thought!",
                    "That's okay! Anything at all stand out to you?",
                ]
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
    existing_context = ""
    if existing_memories:
        existing_context = "\n\nExisting memories (DO NOT extract these again):\n" + "\n".join(f"- {mem}" for mem in existing_memories[:20])

    extraction_prompt = f"""You are a memory extraction assistant. Extract ONLY factual information that the USER explicitly stated in their message.

CRITICAL RULES:
1. Extract ONLY from the user's message below - ignore everything else
2. Do NOT extract information from assistant responses or anything the assistant inferred
3. Only extract if the information is NEW and explicitly stated by the user
4. Do NOT extract information that already exists in the existing memories list
5. Return "None" if no new information is present in the user's message
6. Extract only clear, factual statements about the user
7. Return each memory as a separate line, starting with "User" (e.g., "User mentioned liking hiking")

User's message:
{user_message}{existing_context}

Extract memories (one per line, or "None" if nothing new):"""

    messages = [
        {
            "role": "system",
            "content": "You are a memory extraction assistant. Extract ONLY factual information that the user explicitly stated. Do NOT extract from assistant responses or inferences."
        },
        {
            "role": "user",
            "content": extraction_prompt
        }
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
