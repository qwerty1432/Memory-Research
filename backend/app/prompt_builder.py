import os
import json

PHASE_PROMPT_BANKS: dict[int, list[str]] = {
    1: [
        "What would constitute a perfect day for you?",
        "What is your favorite holiday? Why?",
        "Given the choice of anyone in the world, whom would you want as a dinner guest? What would you hope to learn from them?",
        "Given the choice of anyone in the world, whom would you want as a dinner guest? What would you hope to learn from them?",
    ],
    2: [
        "Is there something that you've dreamed of doing for a long time? Why haven't you done it?",
        "Tell me your life story in as much detail as possible.",
        "What is the greatest accomplishment of your life?",
        "If you could wake up tomorrow having gained any one quality or ability, what would it be?",
    ],
    3: [
        "What it takes to get you feeling real depressed and blue.",
        "If you were to die this evening... what would you most regret not having told someone? Why haven't you told them yet?",
        "The aspects of your personality that you dislike, worry about, or regard as a handicap to you.",
        "Is there something that you've dreamed of doing for a long time? Why haven't you done it?",
    ],
}


def get_phase_prompts(phase: int) -> list[str]:
    return PHASE_PROMPT_BANKS.get(phase, [])


def get_phase_opening_message(phase: int) -> str:
    prompts = get_phase_prompts(phase)
    if not prompts:
        return "Welcome. You can start by sharing whatever is on your mind."
    if phase == 1:
        return (
            "Hi! I'm your AI research companion.\n"
            "We’ll go through a short set of questions in 3 phases—one at a time.\n"
            "If you can’t answer fully, share what you can; I’ll ask a follow-up until your answer is clear.\n\n"
            f"Phase 1: Question 1 of {len(prompts)}: {prompts[0]}"
        )
    return (
        f"Moving to Phase {phase}. I’ll ask the next short set of questions—one at a time.\n\n"
        f"Question 1 of {len(prompts)}: {prompts[0]}"
    )


def _get_cross_phase_bridge_instruction(next_prompt: str) -> str:
    """
    Optional bridge instruction tying prior answers to the current required question.
    Applied only when allowed context exists.
    """
    normalized = (next_prompt or "").strip().lower()
    bridge_map = {
        "is there something that you've dreamed of doing for a long time? why haven't you done it?":
            "If relevant context exists, you may briefly connect this to the user's earlier 'perfect day' answer or earlier desired quality/ability before asking the required question.",
        "what it takes to get you feeling real depressed and blue.":
            "If relevant context exists, you may briefly connect this to whether their earlier 'perfect day' could help them cope, then ask the required question.",
        "tell me your life story in as much detail as possible.":
            "If relevant context exists, you may briefly connect this to the earlier favorite holiday as part of their life narrative, then ask the required question.",
        "if you were to die this evening... what would you most regret not having told someone? why haven't you told them yet?":
            "If relevant context exists, you may briefly reference important figures from the earlier life story, then ask the required question.",
        "what is the greatest accomplishment of your life?":
            "If relevant context exists, you may briefly connect this to the earlier dinner guest (for example as an inspiration), then ask the required question.",
        "the aspects of your personality that you dislike, worry about, or regard as a handicap to you.":
            "If relevant context exists, you may briefly connect this to challenges faced while achieving their greatest accomplishment, then ask the required question.",
        "if you could wake up tomorrow having gained any one quality or ability, what would it be?":
            "If relevant context exists, you may briefly connect this to whether their earlier dinner guest embodies that quality, then ask the required question.",
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
    """
    Build a guided-flexible interviewer response:
    - briefly acknowledge the user's latest response
    - ask exactly the next required phase prompt
    """
    system_prompt = (
        "You are a warm, extroverted research chat companion.\n"
        f"You are currently in Phase {phase} of a structured interview.\n"
        "Your response must do exactly two things:\n"
        "1) Briefly acknowledge or reflect the user's latest message in 1-2 sentences.\n"
        "2) Ask exactly the provided next required question, unchanged in meaning (as the only question in your response).\n"
        "Constraints:\n"
        "- Keep total response under 120 words.\n"
        "- Ask only one question.\n"
        "- Do not skip ahead or invent a different required question.\n"
        "- Keep the tone supportive and non-judgmental.\n"
        "- Add a short bridge/transition phrase between your acknowledgement and the required question (still without adding another question).\n"
        "- Only reference past answers if they appear in the provided context block.\n"
        "- Never invent prior memories or details.\n"
        "- Never say you will “come back later” or “revisit”; if more detail is needed, ask a follow-up immediately in the next assistant turn.\n"
        f"- Memory condition: {condition}.\n"
    )
    bridge_instruction = _get_cross_phase_bridge_instruction(next_prompt)
    progress_prompt = (
        f"Progress so far: {prompts_answered}/{total_prompts} required questions answered.\n"
        f"Next required question: {next_prompt}"
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
        "You are a warm, extroverted research chat companion.\n"
        f"Phase {phase} is complete (all required questions were answered).\n"
        "Respond by:\n"
        "1) Briefly acknowledging the user's last message.\n"
        "2) Thanking them and clearly saying they can click 'Finish Conversation' to return to the survey.\n"
        "Do not ask any new required interview question."
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
    """
    Build messages array for the GenAI API with context and user message.
    """
    tone = (os.getenv("CHAT_TONE") or "extroverted").strip().lower()
    if tone == "neutral":
        system_prompt = (
            "You are a friendly AI companion. Use the provided context to have a natural conversation."
        )
    else:
        # Extroverted, disclosure-supporting tone (keep ethically appropriate; avoid pressure).
        system_prompt = (
            "You are a warm, upbeat, extroverted AI companion.\n"
            "Goals:\n"
            "- Be conversational, encouraging, and curious.\n"
            "- Ask clear, open-ended follow-up questions when helpful.\n"
            "- If the user's answer is very short, vague, or off-topic, gently ask for a bit more detail or clarification before moving on.\n"
            "- Never pressure the user to disclose; respect boundaries and accept 'I’d rather not say'.\n"
            "- Do not claim to have personal experiences; you can share brief, general, anonymized-sounding examples only if asked.\n"
            "- Use the provided context if relevant, but do not invent facts.\n"
        )
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add context if available
    if context.strip():
        messages.append({
            "role": "system",
            "content": f"Context from previous conversations:\n{context}"
        })
    
    # Add user message
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
    """
    Assess effort and relevance of a user's response relative to the assistant's last prompt.
    Returns a small JSON-like dict used for logging and follow-up behavior.

    NOTE: Must be deterministic and cheap.
    """
    from .genai_client import call_genai

    prompt = f"""You are a strict evaluator for a research chatbot.

Given:
- Assistant_prompt: {json.dumps((last_assistant_prompt or "").strip()[:800])}
- User_response: {json.dumps((user_message or "").strip()[:800])}

Task:
Return STRICT JSON only (no markdown) with exactly these keys:
- relevance_score: integer 1-3 (1=off-topic, 2=somewhat relevant, 3=clearly relevant)
- effort_score: integer 1-3 (1=very low effort, 2=some detail, 3=thoughtful/detail)
- needs_followup: boolean (true if user should be asked to clarify or add detail before proceeding)
- followup_question: string (a single warm, specific follow-up question; empty string if needs_followup is false)

Rules:
- If there is no meaningful Assistant_prompt, set relevance_score=3 unless the response is empty/generic.
- needs_followup must be true unless the user response directly answers the assistant's required question (or explicitly indicates a clear reason they cannot answer).
- Do not say you will “come back later” or “revisit”; just ask the needed follow-up question now when needs_followup=true.
- Do not include any other keys.
"""

    messages = [
        {"role": "system", "content": "You output strict JSON only."},
        {"role": "user", "content": prompt},
    ]

    raw = await call_genai(messages, stream=False, temperature=0.0, max_tokens=180)
    raw = (raw or "").strip()

    try:
        data = json.loads(raw)
    except Exception:
        # Safe fallback
        return {
            "relevance_score": 2,
            "effort_score": 2,
            "needs_followup": False,
            "followup_question": "",
            "parse_error": True,
            "raw_preview": raw[:200],
        }

    # Normalize and validate
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
        # Ensure it's not absurdly long
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
    - If insufficient and followups_used < max_followups: return targeted follow-up question
    - If insufficient and followups_used == max_followups: return None (force advance to next prompt)
    - If sufficient: return None (advance immediately)
    
    Args:
        last_assistant_prompt: The assistant's last prompt/question
        user_message: The user's response
        current_required_prompt: The current required phase prompt (if in guided mode)
        followups_used_for_prompt: Number of follow-ups already asked for this prompt
    
    Returns:
        (followup_question, effort_result) or (None, None)
    """
    # Quick rule-based checks first (cheaper than LLM)
    max_followups = 4
    used_followups = [s.strip().lower() for s in (used_followups_for_prompt or []) if str(s).strip()]
    min_words = 10
    if _is_generic_or_too_short(user_message, min_words=min_words):
        # Very short/generic response - needs follow-up if we haven't hit the cap
        if followups_used_for_prompt < max_followups:
            # Generate a varied follow-up that references the current question
            if current_required_prompt:
                followup_variants = [
                    f"I appreciate your response. Could you tell me a bit more about {current_required_prompt.lower()}?",
                    f"That's helpful context. What else comes to mind when you think about {current_required_prompt.lower()}?",
                    f"Thanks for sharing. I'd love to hear more details about {current_required_prompt.lower()}.",
                ]
            else:
                followup_variants = [
                    "Could you share a bit more detail? I'd love to understand this better.",
                    "That's interesting. What else comes to mind?",
                    "Thanks for that. Can you tell me more?",
                ]
            # Vary based on followup count, avoid duplicates if possible
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
            # Hit the cap - acknowledge and move on
            return None, {
                "relevance_score": 2,
                "effort_score": 1,
                "needs_followup": False,
                "followup_question": "",
                "rule_based": True,
                "followup_cap_reached": True,
            }
    
    # For longer responses, use LLM to assess relevance/effort
    if followups_used_for_prompt < max_followups:
        effort_result = await assess_effort_relevance(last_assistant_prompt, user_message)
        
        if effort_result.get("needs_followup", False):
            followup_question = effort_result.get("followup_question", "").strip()
            if followup_question:
                # Enhance follow-up to reference current required prompt if available
                if current_required_prompt and current_required_prompt.lower() not in followup_question.lower():
                    # Try to incorporate the required prompt context
                    followup_question = f"Regarding {current_required_prompt.lower()}, {followup_question}"
                
                # Avoid repeating the same follow-up question for the same required prompt.
                normalized = followup_question.strip().lower()
                if normalized in used_followups:
                    # Fall back to a deterministic variant referencing the required prompt.
                    if current_required_prompt:
                        fallbacks = [
                            f"To make sure I understand, could you share one specific detail about {current_required_prompt.lower()}?",
                            f"What’s one concrete example that comes to mind for {current_required_prompt.lower()}?",
                            f"If you picture it more vividly, what stands out most about {current_required_prompt.lower()}?",
                        ]
                    else:
                        fallbacks = [
                            "Could you share one specific detail that comes to mind?",
                            "What’s one concrete example you could add?",
                            "If you think about it a bit more, what stands out most?",
                        ]
                    for fb in fallbacks:
                        if fb.strip().lower() not in used_followups:
                            followup_question = fb
                            effort_result["followup_question"] = followup_question
                            break
                return followup_question, effort_result
        
        # Sufficient response or no follow-up needed
        return None, effort_result
    else:
        # Hit follow-up cap - force advance even if response is still insufficient
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
    
    Args:
        user_message: The user's message to extract memories from
        existing_memories: List of existing memory texts to avoid duplicates
    
    Returns list of memory candidate strings like:
    - "User mentioned liking hiking"
    - "User is studying at Purdue"
    """
    # Build existing memories context
    existing_context = ""
    if existing_memories:
        existing_context = "\n\nExisting memories (DO NOT extract these again):\n" + "\n".join(f"- {mem}" for mem in existing_memories[:20])  # Limit to 20 most recent
    
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
        
        # Parse response into memory candidates
        memories = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line.lower() != "none" and line.startswith("User"):
                # Clean up the memory text
                memory_text = line
                if len(memory_text) > 200:
                    memory_text = memory_text[:200]
                memories.append(memory_text)
        
        return memories
    except Exception as e:
        # If extraction fails, return empty list
        print(f"Memory extraction error: {e}")
        return []

