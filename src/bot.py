"""WhatsApp inbound webhook: conversational chat + runtime model switching.

Run:  python -m src.bot
Then expose it publicly (e.g. `ngrok http 5000`) and set the Twilio sandbox's
"WHEN A MESSAGE COMES IN" webhook (Console > Messaging > Try it out > Send a
WhatsApp message) to <public-url>/whatsapp, method POST.

Commands (only honored from MY_WHATSAPP_NUMBER):
  /model            — show the active model
  /model <alias>    — switch model: haiku | sonnet | opus | fable
Anything else is sent to Claude using the active model and replied inline.
"""

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from src import config, model_state
from src.integrations.llm import ask_claude

app = Flask(__name__)


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    sender = request.form.get("From", "")
    body = request.form.get("Body", "").strip()
    resp = MessagingResponse()

    if sender != config.MY_WHATSAPP_NUMBER:
        return str(resp)

    if body.lower().startswith("/model"):
        parts = body.split(maxsplit=1)
        if len(parts) == 1:
            resp.message(f"Current model: {model_state.get_model()}")
        else:
            try:
                resolved = model_state.set_model(parts[1])
                resp.message(f"Switched to {resolved}")
            except ValueError as exc:
                resp.message(str(exc))
    elif body:
        reply = ask_claude(body)
        resp.message(reply)

    return str(resp)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
