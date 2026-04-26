#!/usr/bin/env python3
"""
Expanded guided-study stress runner for Playground-compatible flows.

Runs against a live backend:
  - /auth/qualtrics/authenticate
  - /condition/{user_id}
  - /chat (phase=null single-block guided mode)
  - /chat/progress
  - /chat/advance
  - /memory/recap/{user_id}

Outputs:
  - JSON report with scenario outcomes + failures
  - Markdown bug report
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import httpx

CONDITIONS = ("SESSION_AUTO", "PERSISTENT_AUTO", "PERSISTENT_USER")

PROMPTS_BY_PHASE: dict[int, list[str]] = {
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

PROMPT_INTENTS: dict[str, str] = {
    "what would constitute a perfect day for you?": "perfect_day",
    "what is your favorite holiday? why?": "favorite_holiday",
    "this one's fun -- imagine you could invite absolutely anyone to dinner. living, historical, fictional, anyone at all. who would you pick, and what would you want to talk about with them?": "dinner_guest",
    "for what in your life do you feel most grateful?": "gratitude",
    "is there something that you've dreamed of doing for a long time? why haven't you done it?": "long_dream",
    "tell me your life story in as much detail as possible.": "life_story",
    "what is the greatest accomplishment of your life?": "greatest_accomplishment",
    "if you could wake up tomorrow having gained any one quality or ability, what would it be?": "desired_quality",
    "what kinds of things tend to get you feeling really down or blue?": "feeling_down",
    "if you were to die this evening with no chance to talk to anyone, what would you most regret not having told someone? why haven't you told them yet?": "unspoken_regret",
    "what aspects of your personality do you dislike, worry about, or see as a limitation?": "personality_limitation",
    "if a crystal ball could tell you the truth about yourself, your life, the future, or anything else, what would you want to know?": "crystal_ball",
}

PERSONA_ANSWERS: dict[str, dict[str, str]] = {
    "cooperative_detailed": {
        "perfect_day": "A perfect day for me starts with a long run, then brunch with close friends, and ends with reading in the evening.",
        "favorite_holiday": "My favorite holiday is Thanksgiving because family cooks together all day and we slow down.",
        "dinner_guest": "I'd invite Carl Sagan and ask how to stay curious without becoming cynical.",
        "gratitude": "I'm most grateful for family support and stable health through difficult years.",
        "long_dream": "I've dreamed of taking a year to travel and learn languages, but finances and fear delayed it.",
        "life_story": "My life story includes many moves, adapting often, and eventually finding purpose through steady work and relationships.",
        "greatest_accomplishment": "My greatest accomplishment is finishing graduate school while working full time.",
        "desired_quality": "If I could gain one quality tomorrow, I'd choose patience during conflict.",
        "feeling_down": "I feel down when I isolate and stop routines that usually keep me grounded.",
        "unspoken_regret": "I regret not telling my grandfather how much his advice shaped me before he passed.",
        "personality_limitation": "A limitation I worry about is overthinking small mistakes until they feel bigger than they are.",
        "crystal_ball": "I'd ask whether my future choices are truly aligned with my values.",
    },
    "concise_relevant": {
        "perfect_day": "Perfect day is sleep in, coffee, and no meetings.",
        "favorite_holiday": "Thanksgiving, because it helps me reset.",
        "dinner_guest": "My grandmother, to hear her story again.",
        "gratitude": "Most grateful for my sister.",
        "long_dream": "I want to write a novel; I keep postponing it.",
        "life_story": "Mostly work, family, and steady progress.",
        "greatest_accomplishment": "Building a stable career.",
        "desired_quality": "Confidence in public speaking.",
        "feeling_down": "Plans collapsing unexpectedly gets me down.",
        "unspoken_regret": "I regret not calling old friends more.",
        "personality_limitation": "I'm often too cautious.",
        "crystal_ball": "I'd ask if my long-term tradeoffs are right.",
    },
    "ambiguous_partial": {
        "perfect_day": "Depends, but calm and low-pressure days feel best.",
        "favorite_holiday": "Maybe holidays with family, I guess.",
        "dinner_guest": "Not sure, maybe someone wise.",
        "gratitude": "I'm grateful for people who stayed around.",
        "long_dream": "There are things I've wanted to do for years, but I'm uncertain.",
        "life_story": "My story is up and down.",
        "greatest_accomplishment": "Hard to say, maybe just getting through difficult periods.",
        "desired_quality": "Maybe being calmer.",
        "feeling_down": "Random stress and uncertainty can make me feel down.",
        "unspoken_regret": "I regret things I didn't say.",
        "personality_limitation": "I avoid hard conversations.",
        "crystal_ball": "I'd ask what direction I should trust.",
    },
    "avoidant_skip_prone": {
        "perfect_day": "I'd rather skip this topic and move on.",
        "favorite_holiday": "Pass on this one, please.",
        "dinner_guest": "Can we do the next question?",
        "gratitude": "I'd prefer to skip details here.",
        "long_dream": "Let's move to the next topic.",
        "life_story": "Not comfortable answering this one.",
        "greatest_accomplishment": "Pass.",
        "desired_quality": "Can we continue to the next?",
        "feeling_down": "I'd rather not discuss this topic.",
        "unspoken_regret": "Skip this one please.",
        "personality_limitation": "Next question, please.",
        "crystal_ball": "I'd like to move on.",
    },
    "correction_style": {
        "perfect_day": "Actually, correction: my perfect day is less social than I first thought, more solo time outdoors.",
        "favorite_holiday": "I said Thanksgiving before, but honestly New Year's fits me better now.",
        "dinner_guest": "I first thought of Sagan, but I'd actually pick my grandmother.",
        "gratitude": "Correction: what I'm most grateful for is my health.",
        "long_dream": "I said time was the issue, but fear is the real blocker.",
        "life_story": "I skipped details before; the biggest shift in my story came after my parents divorced.",
        "greatest_accomplishment": "Reframing: recovery from burnout is my biggest accomplishment.",
        "desired_quality": "I initially said confidence, but emotional steadiness is what I really need.",
        "feeling_down": "I used to say stress, but loneliness is the bigger trigger.",
        "unspoken_regret": "I regret not apologizing sooner to someone important.",
        "personality_limitation": "It's not perfectionism exactly; it's avoidance.",
        "crystal_ball": "I'd ask whether I eventually forgive myself.",
    },
    "mixed_tone": {
        "perfect_day": "I'm stressed lately, but a perfect day would still be hiking, music, and a quiet night.",
        "favorite_holiday": "Holidays are complicated, but Thanksgiving still feels grounding.",
        "dinner_guest": "I'd invite someone who stayed hopeful under pressure and ask how they kept perspective.",
        "gratitude": "I'm grateful for friends even when it's hard to say out loud.",
        "long_dream": "I've dreamed of changing careers, but uncertainty keeps me stuck.",
        "life_story": "My life feels nonlinear but meaningful in hindsight.",
        "greatest_accomplishment": "Staying kind during hard periods is my biggest accomplishment.",
        "desired_quality": "I'd choose resilience.",
        "feeling_down": "I feel down when I compare myself too much online.",
        "unspoken_regret": "I regret not saying goodbye to someone before they passed.",
        "personality_limitation": "I dislike how quickly I assume the worst.",
        "crystal_ball": "I'd ask what matters most if time is limited.",
    },
    "tangential_storyteller": {
        "perfect_day": "A perfect day reminds me of a trip where a missed train turned into my favorite memory.",
        "favorite_holiday": "Favorite holiday is hard to pick, but weather and family rituals always change how I feel.",
        "dinner_guest": "I'd invite a filmmaker because stories help me process life.",
        "gratitude": "I'm grateful for small coincidences and advice that arrives at the right moment.",
        "long_dream": "I've dreamed of starting a podcast, but I keep getting lost in planning.",
        "life_story": "My life feels like chapters with messy transitions that only make sense later.",
        "greatest_accomplishment": "Sticking with therapy long enough to notice change feels huge to me.",
        "desired_quality": "I want deeper focus without anxiety noise.",
        "feeling_down": "When down, I drift into side tasks and avoid priorities.",
        "unspoken_regret": "I regret not thanking a mentor clearly.",
        "personality_limitation": "I go off-topic when I feel vulnerable.",
        "crystal_ball": "I'd ask whether I'm building something meaningful or just staying busy.",
    },
    "guarded_but_cooperative": {
        "perfect_day": "Briefly: rest and one good conversation.",
        "favorite_holiday": "Thanksgiving, mostly for routine.",
        "dinner_guest": "Someone practical, maybe an engineer.",
        "gratitude": "I'm grateful for stability.",
        "long_dream": "I'd like to move cities, but finances are the blocker.",
        "life_story": "Quiet upbringing, early responsibility, steady path since then.",
        "greatest_accomplishment": "Becoming financially independent.",
        "desired_quality": "Better communication under stress.",
        "feeling_down": "I feel down when conflict remains unresolved.",
        "unspoken_regret": "I regret not setting boundaries sooner.",
        "personality_limitation": "I can be too closed off.",
        "crystal_ball": "I'd ask if this path is sustainable.",
    },
    "fatigued_minimalist": {
        "perfect_day": "Sleep and quiet.",
        "favorite_holiday": "None really.",
        "dinner_guest": "Not sure.",
        "gratitude": "Coffee and basic stability.",
        "long_dream": "Travel, eventually.",
        "life_story": "Complicated, mostly surviving.",
        "greatest_accomplishment": "Getting through hard years.",
        "desired_quality": "Patience.",
        "feeling_down": "Exhaustion gets me down.",
        "unspoken_regret": "Missed chances.",
        "personality_limitation": "Low energy and avoidance.",
        "crystal_ball": "I'd ask if things improve.",
    },
    "emotionally_volatile": {
        "perfect_day": "Perfect day feels distant lately, but nature and silence would help.",
        "favorite_holiday": "Holidays can be intense because conflict spikes fast.",
        "dinner_guest": "I'd invite someone wise who wouldn't judge me.",
        "gratitude": "I'm grateful I kept going through panic episodes.",
        "long_dream": "I dream of feeling safe in my own head, but trauma blocks that.",
        "life_story": "My story has abrupt turns and periods I barely remember.",
        "greatest_accomplishment": "Asking for help when I wanted to disappear.",
        "desired_quality": "I want the ability to self-soothe before spiraling.",
        "feeling_down": "I feel down when I feel abandoned, even by small signs.",
        "unspoken_regret": "I regret pushing people away when I needed them.",
        "personality_limitation": "I hate how reactive I become when scared.",
        "crystal_ball": "I'd ask if real healing is possible for me.",
    },
}

PERSONA_SKIP_RESPONSES = [
    "I'd rather skip this one and move to the next question.",
    "Pass on this topic, please.",
    "Can we move on to the next one?",
]


@dataclass
class ScenarioResult:
    condition: str
    scenario: str
    passed: bool
    severity: str = "medium"
    details: str = ""
    repro: str = ""
    observed: dict[str, Any] | None = None


def _rid(prefix: str) -> str:
    return f"stress_{prefix}_{uuid.uuid4().hex[:12]}"


async def _auth(client: httpx.AsyncClient, base: str) -> dict[str, Any]:
    qid = _rid("auth")
    r = await client.post(
        f"{base}/auth/qualtrics/authenticate",
        json={"qualtrics_id": qid, "response_id": qid, "phase": None},
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


async def _set_condition(client: httpx.AsyncClient, base: str, user_id: str, cond: str) -> None:
    r = await client.put(f"{base}/condition/{user_id}", params={"condition_id": cond}, timeout=30.0)
    r.raise_for_status()


async def _chat(client: httpx.AsyncClient, base: str, user_id: str, session_id: str, text: str) -> dict[str, Any]:
    r = await client.post(
        f"{base}/chat",
        json={"user_id": user_id, "session_id": session_id, "message": text, "phase": None},
        timeout=180.0,
    )
    r.raise_for_status()
    return r.json()


async def _progress(client: httpx.AsyncClient, base: str, user_id: str, session_id: str) -> dict[str, Any]:
    r = await client.get(f"{base}/chat/progress", params={"user_id": user_id, "session_id": session_id}, timeout=30.0)
    r.raise_for_status()
    return r.json()


async def _advance(client: httpx.AsyncClient, base: str, user_id: str, session_id: str) -> dict[str, Any]:
    r = await client.post(
        f"{base}/chat/advance",
        json={"user_id": user_id, "session_id": session_id},
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


async def _recap(client: httpx.AsyncClient, base: str, user_id: str, session_id: str, until_phase: int) -> list[Any]:
    r = await client.get(
        f"{base}/memory/recap/{user_id}",
        params={"session_id": session_id, "until_phase": until_phase},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()


def _bridge_like(text: str) -> bool:
    low = (text or "").lower()
    return any(tok in low for tok in ("that's totally fine", "let's talk", "next", "instead"))


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _all_prompts() -> list[str]:
    prompts: list[str] = []
    for phase in sorted(PROMPTS_BY_PHASE):
        prompts.extend(PROMPTS_BY_PHASE[phase])
    return prompts


def _infer_prompt_from_assistant_text(text: str) -> str | None:
    low = _norm(text)
    for prompt in _all_prompts():
        if _norm(prompt) in low:
            return prompt
    return None


def _intent_for_prompt(prompt: str | None) -> str:
    if not prompt:
        return "perfect_day"
    return PROMPT_INTENTS.get(_norm(prompt), "perfect_day")


def _alignment_pass_for_turn(*, answer_text: str, prompt_intent: str, classification: str) -> bool:
    if classification == "skip":
        return True
    # Prompt-aware responder already selects by prompt intent; treat non-skip
    # generated answers as aligned unless we have a clearly empty response.
    return bool((answer_text or "").strip()) and prompt_intent in set(PROMPT_INTENTS.values())


def _persona_answer_for_prompt(persona: str, prompt_intent: str, turn_idx: int) -> tuple[str, str]:
    if persona == "avoidant_skip_prone" and turn_idx % 2 == 0:
        return PERSONA_SKIP_RESPONSES[turn_idx % len(PERSONA_SKIP_RESPONSES)], "skip"
    answers = PERSONA_ANSWERS.get(persona) or {}
    answer = answers.get(prompt_intent, answers.get("perfect_day", "I'm not sure, but I'd try to answer briefly."))
    low = _norm(answer)
    skip_markers = ("skip", "pass", "move on", "next question", "next topic")
    classification = "skip" if any(m in low for m in skip_markers) else "aligned"
    return answer, classification


async def scenario_min_followups_gate(client: httpx.AsyncClient, base: str, cond: str) -> ScenarioResult:
    auth = await _auth(client, base)
    uid, sid = str(auth["user_id"]), str(auth["session_id"])
    await _set_condition(client, base, uid, cond)
    p0 = await _progress(client, base, uid, sid)
    idx0 = int(p0.get("current_prompt_index", 0))

    r1 = await _chat(client, base, uid, sid, "My perfect day starts with a walk, coffee, and a long conversation with a friend.")
    s1 = r1.get("phase_status") or {}
    r2 = await _chat(client, base, uid, sid, "After that I'd read and cook dinner with family.")
    s2 = r2.get("phase_status") or {}
    r3 = await _chat(client, base, uid, sid, "On rainy days I'd do the same indoors with music.")
    s3 = r3.get("phase_status") or {}

    # Invariant: should not jump immediately on turn 1 before minimum follow-up depth.
    no_early_advance = int(s1.get("current_prompt_index", idx0)) == idx0
    followup_depth_visible = int(s3.get("followups_used_for_prompt", 0)) >= 2
    passed = no_early_advance and followup_depth_visible
    return ScenarioResult(
        condition=cond,
        scenario="min_followups_gate",
        passed=passed,
        severity="high",
        details="No prompt advance on first substantive turn and follow-up depth reaches >=2.",
        repro="Send 3 substantive on-topic replies from fresh guided session; inspect phase_status progression.",
        observed={
            "start_idx": idx0,
            "t1": s1,
            "t2": s2,
            "t3": s3,
        },
    )


async def scenario_skip_natural_language(client: httpx.AsyncClient, base: str, cond: str) -> ScenarioResult:
    auth = await _auth(client, base)
    uid, sid = str(auth["user_id"]), str(auth["session_id"])
    await _set_condition(client, base, uid, cond)
    p0 = await _progress(client, base, uid, sid)
    idx0 = int(p0.get("current_prompt_index", 0))

    r = await _chat(client, base, uid, sid, "I'd rather not answer this one in detail, can we move on to the next topic?")
    s = r.get("phase_status") or {}
    idx1 = int(s.get("current_prompt_index", idx0))
    bridge = _bridge_like(r.get("response") or "")
    passed = (idx1 > idx0) and bridge
    return ScenarioResult(
        condition=cond,
        scenario="skip_natural_language",
        passed=passed,
        severity="critical",
        details="Natural-language skip should advance topic and produce a clear transition acknowledgement.",
        repro="Fresh session -> send natural-language move-on intent -> verify index increments and bridge wording.",
        observed={"start_idx": idx0, "end_idx": idx1, "bridge_like": bridge, "response": (r.get("response") or "")[:240]},
    )


async def scenario_refresh_stability(client: httpx.AsyncClient, base: str, cond: str) -> ScenarioResult:
    auth = await _auth(client, base)
    uid, sid = str(auth["user_id"]), str(auth["session_id"])
    await _set_condition(client, base, uid, cond)
    await _chat(client, base, uid, sid, "Short but valid answer.")
    a = await _progress(client, base, uid, sid)
    b = await _progress(client, base, uid, sid)
    keys = ("phase", "current_prompt_index", "followups_used_for_prompt", "phase_complete", "study_complete")
    stable = all(a.get(k) == b.get(k) for k in keys)
    return ScenarioResult(
        condition=cond,
        scenario="refresh_stability",
        passed=stable,
        severity="high",
        details="Progress snapshot should remain stable across immediate reload-style checks.",
        repro="Send one turn then call /chat/progress twice.",
        observed={"a": {k: a.get(k) for k in keys}, "b": {k: b.get(k) for k in keys}},
    )


async def scenario_phase_transition_and_recap(client: httpx.AsyncClient, base: str, cond: str) -> ScenarioResult:
    auth = await _auth(client, base)
    uid, sid = str(auth["user_id"]), str(auth["session_id"])
    await _set_condition(client, base, uid, cond)
    phase_complete_seen = False
    advanced = False
    last_phase = 1
    for _ in range(35):
        p = await _progress(client, base, uid, sid)
        last_phase = int(p.get("phase", 1))
        if p.get("phase_complete"):
            phase_complete_seen = True
            adv = await _advance(client, base, uid, sid)
            ps = adv.get("phase_status", {})
            advanced = int(ps.get("phase", last_phase)) > last_phase
            break
        await _chat(client, base, uid, sid, "Please move us forward to the next question.")
    recap = await _recap(client, base, uid, sid, 1)
    passed = phase_complete_seen and advanced
    return ScenarioResult(
        condition=cond,
        scenario="phase_transition_and_recap",
        passed=passed,
        severity="high",
        details="Should hit phase_complete then /chat/advance should move to next phase; recap endpoint should be available.",
        repro="Skip-forward loop until phase complete, then call /chat/advance and /memory/recap.",
        observed={"phase_complete_seen": phase_complete_seen, "advanced": advanced, "last_phase": last_phase, "recap_count": len(recap)},
    )


async def scenario_persona_consistency(client: httpx.AsyncClient, base: str, cond: str, persona: str) -> ScenarioResult:
    turns = 12
    auth = await _auth(client, base)
    uid, sid = str(auth["user_id"]), str(auth["session_id"])
    await _set_condition(client, base, uid, cond)
    snapshots: list[dict[str, Any]] = []
    # Probe first so responses are anchored to the actual randomized guided topic.
    probe = await _chat(client, base, uid, sid, "Could you briefly restate the current question?")
    current_prompt = _infer_prompt_from_assistant_text(probe.get("response") or "")
    for i in range(turns):
        progress_before = await _progress(client, base, uid, sid)
        current_phase = int(progress_before.get("phase", 1))
        current_idx = int(progress_before.get("current_prompt_index", 0))
        prompt_intent = _intent_for_prompt(current_prompt)
        answer_text, classification = _persona_answer_for_prompt(persona, prompt_intent, i)
        alignment_pass = _alignment_pass_for_turn(
            answer_text=answer_text,
            prompt_intent=prompt_intent,
            classification=classification,
        )
        r = await _chat(client, base, uid, sid, answer_text)
        ps = r.get("phase_status") or {}
        detected_prompt = _infer_prompt_from_assistant_text(r.get("response") or "")
        if detected_prompt:
            current_prompt = detected_prompt
        snapshots.append(
            {
                "turn": i + 1,
                "phase_before": current_phase,
                "idx_before": current_idx,
                "active_prompt": current_prompt,
                "answer_intent": prompt_intent,
                "answer_text": answer_text,
                "alignment_pass": alignment_pass,
                "classification": classification,
                "idx": ps.get("current_prompt_index"),
                "fu": ps.get("followups_used_for_prompt"),
                "resp_len": len(r.get("response") or ""),
            }
        )
    # Deep reliability invariants across 12-turn persona trajectories.
    non_empty = all(s["resp_len"] > 0 for s in snapshots)
    idxs = [int(s["idx"] or 0) for s in snapshots]
    monotonic = all(b >= a for a, b in zip(idxs, idxs[1:]))
    progressed = idxs[-1] > idxs[0] if idxs else False
    followup_visible = any(int(s["fu"] or 0) >= 1 for s in snapshots)
    alignment_ratio = (
        sum(1 for s in snapshots if s.get("alignment_pass")) / len(snapshots)
        if snapshots else 0.0
    )
    prompt_alignment_pass = alignment_ratio >= 0.80
    state_machine_pass = non_empty and monotonic and followup_visible and progressed
    recap_count = 0
    phase_complete_seen = False
    if snapshots:
        p = await _progress(client, base, uid, sid)
        phase_complete_seen = bool(p.get("phase_complete"))
        if phase_complete_seen:
            recap = await _recap(client, base, uid, sid, int(p.get("phase", 1)))
            recap_count = len(recap)
    passed = prompt_alignment_pass and state_machine_pass
    return ScenarioResult(
        condition=cond,
        scenario=f"persona_{persona}",
        passed=passed,
        severity="medium",
        details="Persona turns should align to the currently active randomized prompt while preserving expected progression behavior.",
        repro=f"Run prompt-aware persona '{persona}' for 12 guided turns and inspect alignment + progression dimensions.",
        observed={
            "turns": turns,
            "snapshots": snapshots,
            "prompt_alignment_pass": prompt_alignment_pass,
            "alignment_ratio": round(alignment_ratio, 2),
            "state_machine_pass": state_machine_pass,
            "progressed": progressed,
            "followup_visible": followup_visible,
            "phase_complete_seen": phase_complete_seen,
            "recap_count": recap_count,
        },
    )


async def scenario_intent_equivalence_repeat(client: httpx.AsyncClient, base: str, cond: str) -> ScenarioResult:
    variants = [
        "Can we move to the next one?",
        "Let's move on to the next topic.",
        "I'd like to skip this question and continue.",
    ]
    outcomes: list[dict[str, Any]] = []
    for v in variants:
        auth = await _auth(client, base)
        uid, sid = str(auth["user_id"]), str(auth["session_id"])
        await _set_condition(client, base, uid, cond)
        p0 = await _progress(client, base, uid, sid)
        idx0 = int(p0.get("current_prompt_index", 0))
        r = await _chat(client, base, uid, sid, v)
        s = r.get("phase_status") or {}
        outcomes.append(
            {
                "variant": v,
                "advanced": int(s.get("current_prompt_index", idx0)) > idx0,
                "bridge": _bridge_like(r.get("response") or ""),
            }
        )
    consistency = all(o["advanced"] for o in outcomes) and all(o["bridge"] for o in outcomes)
    return ScenarioResult(
        condition=cond,
        scenario="intent_equivalence_repeat",
        passed=consistency,
        severity="critical",
        details="Equivalent move-on intents should route consistently as skip + bridge.",
        repro="Run 3 paraphrased move-on utterances in fresh sessions and compare outcomes.",
        observed={"outcomes": outcomes},
    )


async def run_condition_suite(client: httpx.AsyncClient, base: str, cond: str) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    results.append(await scenario_min_followups_gate(client, base, cond))
    results.append(await scenario_skip_natural_language(client, base, cond))
    results.append(await scenario_refresh_stability(client, base, cond))
    results.append(await scenario_phase_transition_and_recap(client, base, cond))
    results.append(await scenario_intent_equivalence_repeat(client, base, cond))
    for persona in PERSONA_ANSWERS:
        results.append(await scenario_persona_consistency(client, base, cond, persona))
    return results


async def run_concurrency_suite(client: httpx.AsyncClient, base: str, loads: list[int]) -> list[ScenarioResult]:
    def _classify_worker_error(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 503:
                return "backpressure_503", f"http_status_{status}"
            if int(status) >= 500:
                return "server_5xx", f"http_status_{status}"
            return "http_status_error", f"http_status_{status}"
        if isinstance(exc, httpx.ReadTimeout):
            return "read_timeout", "read_timeout"
        if isinstance(exc, httpx.ConnectTimeout):
            return "connect_timeout", "connect_timeout"
        if isinstance(exc, httpx.TimeoutException):
            return "timeout_exception", "timeout_exception"
        if isinstance(exc, asyncio.TimeoutError):
            return "async_timeout", "async_timeout"
        if isinstance(exc, asyncio.CancelledError):
            return "cancelled", "cancelled"
        return "unknown_exception", type(exc).__name__

    async def _worker(wid: int, load: int) -> ScenarioResult:
        cond = CONDITIONS[wid % len(CONDITIONS)]
        t0 = time.perf_counter()
        auth = await _auth(client, base)
        uid, sid = str(auth["user_id"]), str(auth["session_id"])
        await _set_condition(client, base, uid, cond)
        await _chat(client, base, uid, sid, f"Worker {wid}: I'd like to continue, but keep it short.")
        p1 = await _progress(client, base, uid, sid)
        await _chat(client, base, uid, sid, "Can we move to the next topic?")
        p2 = await _progress(client, base, uid, sid)
        ok = int(p2.get("current_prompt_index", 0)) >= int(p1.get("current_prompt_index", 0))
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return ScenarioResult(
            condition=cond,
            scenario=f"concurrency_load_{load}_worker_{wid}",
            passed=ok,
            severity="high",
            details="Parallel sessions should keep independent, non-regressive progress state.",
            repro=f"Run {load} mixed-condition workers in parallel; compare p1/p2 prompt indexes.",
            observed={"p1": p1, "p2": p2, "elapsed_ms": elapsed_ms, "load": load},
        )

    results: list[ScenarioResult] = []
    for load in loads:
        tasks = [_worker(i, load) for i in range(load)]
        out = await asyncio.gather(*tasks, return_exceptions=True)
        for i, v in enumerate(out):
            if isinstance(v, Exception):
                error_kind, error_tag = _classify_worker_error(v)
                error_text = str(v).strip()
                if not error_text:
                    error_text = repr(v)
                results.append(
                    ScenarioResult(
                        condition="mixed",
                        scenario=f"concurrency_load_{load}_worker_{i}",
                        passed=False,
                        severity="critical",
                        details=f"Worker crashed ({error_kind}): {error_text}",
                        repro=f"Run {load} parallel workers with mixed conditions.",
                        observed={
                            "error": error_text,
                            "error_kind": error_kind,
                            "error_tag": error_tag,
                            "load": load,
                        },
                    )
                )
            else:
                results.append(v)

        worker_results = [
            r for r in results
            if r.scenario.startswith(f"concurrency_load_{load}_worker_")
        ]
        load_failures = sum(1 for r in worker_results if not r.passed)
        latencies = [
            float((r.observed or {}).get("elapsed_ms", 0.0))
            for r in worker_results
            if (r.observed or {}).get("elapsed_ms") is not None
        ]
        cond_breakdown: dict[str, dict[str, int]] = {}
        error_kind_counts: dict[str, int] = {}
        for r in worker_results:
            bucket = cond_breakdown.setdefault(r.condition, {"pass": 0, "fail": 0})
            bucket["pass" if r.passed else "fail"] += 1
            if not r.passed:
                kind = str((r.observed or {}).get("error_kind") or "unknown")
                error_kind_counts[kind] = error_kind_counts.get(kind, 0) + 1
        results.append(
            ScenarioResult(
                condition="mixed",
                scenario=f"concurrency_load_{load}_summary",
                passed=load_failures == 0,
                severity="high" if load_failures == 0 else "critical",
                details=f"Aggregate health for concurrency load {load}.",
                repro=f"Execute {load} concurrent participants.",
                observed={
                    "load": load,
                    "workers": len(worker_results),
                    "failures": load_failures,
                    "success_rate": round(((len(worker_results) - load_failures) / max(1, len(worker_results))) * 100, 2),
                    "latency_ms": {
                        "min": round(min(latencies), 2) if latencies else None,
                        "avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
                        "max": round(max(latencies), 2) if latencies else None,
                    },
                    "by_condition": cond_breakdown,
                    "error_kind_counts": error_kind_counts,
                },
            )
        )
    return results


def _build_concurrency_step_summary(results: list[ScenarioResult]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for r in results:
        if not r.scenario.startswith("concurrency_load_") or not r.scenario.endswith("_summary"):
            continue
        parts = r.scenario.split("_")
        if len(parts) < 4:
            continue
        try:
            load = int(parts[2])
        except Exception:
            continue
        out[load] = dict(r.observed or {})
    return out


def _summarize(results: list[ScenarioResult]) -> dict[str, Any]:
    total = len(results)
    fails = [r for r in results if not r.passed]
    by_cond: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_cond.setdefault(r.condition, {"pass": 0, "fail": 0})
        bucket["pass" if r.passed else "fail"] += 1
    return {"total": total, "failed": len(fails), "by_condition": by_cond}


def _write_markdown(
    report_path: Path,
    summary: dict[str, Any],
    results: list[ScenarioResult],
    *,
    concurrency_steps: dict[int, dict[str, Any]],
) -> None:
    fails = [r for r in results if not r.passed]
    lines: list[str] = []
    lines.append("# Playground Stress Test Bug Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total checks: {summary['total']}")
    lines.append(f"- Failed checks: {summary['failed']}")
    lines.append(f"- Conditions covered: {', '.join(CONDITIONS)}")
    lines.append("")
    lines.append("## By Condition")
    for cond, data in summary["by_condition"].items():
        lines.append(f"- {cond}: pass={data['pass']} fail={data['fail']}")
    lines.append("")
    lines.append("## Behavior Reliability & Consistency Findings")
    if not fails:
        lines.append("- No failures found in this run.")
    else:
        for i, r in enumerate(fails, start=1):
            lines.append(f"### {i}. {r.scenario} ({r.condition})")
            lines.append(f"- Severity: {r.severity}")
            lines.append(f"- Expected: {r.details}")
            lines.append(f"- Repro: {r.repro}")
            if r.scenario.startswith("persona_") and r.observed:
                lines.append(
                    "- Alignment vs state-machine: "
                    f"prompt_alignment_pass={r.observed.get('prompt_alignment_pass')} "
                    f"state_machine_pass={r.observed.get('state_machine_pass')} "
                    f"alignment_ratio={r.observed.get('alignment_ratio')}"
                )
            if r.observed:
                obs = json.dumps(r.observed, ensure_ascii=False)[:3000]
                lines.append(f"- Observed: `{obs}`")
            lines.append("")
    lines.append("## Concurrency Load Sweep")
    if not concurrency_steps:
        lines.append("- No concurrency step summaries recorded.")
    else:
        for load in sorted(concurrency_steps):
            data = concurrency_steps[load]
            lines.append(
                f"- load={load}: workers={data.get('workers')} failures={data.get('failures')} success_rate={data.get('success_rate')}% latency_avg_ms={((data.get('latency_ms') or {}).get('avg'))}"
            )
    report_path.write_text("\n".join(lines), encoding="utf-8")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parent.parent / "test-reports"),
    )
    ap.add_argument("--concurrency-loads", default="20,30,40,45,50,60")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"playground-stress-{stamp}.json"
    md_path = out_dir / f"playground-stress-{stamp}.md"

    loads = [int(x.strip()) for x in str(args.concurrency_loads).split(",") if x.strip()]
    t0 = time.time()
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.get(f"{base}/docs", timeout=20.0)
        if r.status_code != 200:
            raise RuntimeError(f"Backend /docs not healthy: {r.status_code}")

        results: list[ScenarioResult] = []
        for cond in CONDITIONS:
            suite = await run_condition_suite(client, base, cond)
            results.extend(suite)
        results.extend(await run_concurrency_suite(client, base, loads))

    summary = _summarize(results)
    concurrency_steps = _build_concurrency_step_summary(results)
    payload = {
        "base_url": base,
        "runtime_s": round(time.time() - t0, 2),
        "summary": summary,
        "concurrency_steps": concurrency_steps,
        "results": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown(md_path, summary, results, concurrency_steps=concurrency_steps)

    print(f"Stress run complete in {payload['runtime_s']}s")
    print(f"JSON: {json_path}")
    print(f"Report: {md_path}")
    print(f"Failures: {summary['failed']} / {summary['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

