from fastapi import APIRouter
from .. import prompt_store

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("")
def get_prompts():
    """Return the active prompt config."""
    return prompt_store.get_config()


@router.put("")
def update_prompts(patch: dict):
    """Deep-merge a partial update into the active config (in-memory only)."""
    new_cfg = prompt_store.update_config(patch)
    return {"status": "applied", "config": new_cfg}


@router.post("/save")
def save_prompts():
    """Persist the active config to disk (prompt_config.json)."""
    prompt_store.save_config()
    return {"status": "saved"}


@router.post("/reset")
def reset_prompts():
    """Discard in-memory overrides and revert to on-disk defaults."""
    cfg = prompt_store.reset_config()
    return {"status": "reset", "config": cfg}
