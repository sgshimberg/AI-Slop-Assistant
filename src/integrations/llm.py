"""Ask Claude a question using the currently selected model.

Run:  python -m src.integrations.llm
Requires ANTHROPIC_API_KEY in .env. Model is runtime-selectable — see src/model_state.py,
or send "/model <alias>" to the WhatsApp bot (src/bot.py).
"""

from anthropic import Anthropic

from src import config, model_state


def ask_claude(prompt: str, model: str | None = None) -> str:
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model or model_state.get_model(),
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


if __name__ == "__main__":
    active_model = model_state.get_model()
    reply = ask_claude("Reply with a short one-sentence confirmation that this connection works.")
    print(f"[{active_model}] {reply}")
