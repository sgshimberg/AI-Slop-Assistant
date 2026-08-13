"""Runtime-selectable Claude model, persisted across restarts.

Default is Haiku 4.5 (cheap, fast, plenty for digest synthesis and chat replies).
Change it via WhatsApp: send "/model <alias>" to the bot (see src/bot.py).
"""

import json
from pathlib import Path

DEFAULT_MODEL = "claude-haiku-4-5"

MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "fable": "claude-fable-5",
}

_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "model_state.json"


def get_model() -> str:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text()).get("model", DEFAULT_MODEL)
        except (json.JSONDecodeError, OSError):
            return DEFAULT_MODEL
    return DEFAULT_MODEL


def set_model(alias: str) -> str:
    """Set the active model by alias. Returns the resolved model ID.

    Raises ValueError if the alias isn't recognized.
    """
    resolved = MODEL_ALIASES.get(alias.strip().lower())
    if not resolved:
        choices = ", ".join(MODEL_ALIASES)
        raise ValueError(f"Unknown model '{alias}'. Choices: {choices}")
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps({"model": resolved}))
    return resolved
