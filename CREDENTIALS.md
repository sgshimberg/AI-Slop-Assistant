# Credentials Checklist (Phase 0)

Copy `.env.example` to `.env` and fill in as you complete each step below. `.env` is
git-ignored — never commit it.

## Twilio (WhatsApp)
1. Sign up at twilio.com (free trial gives credit).
2. Console → Account → find **Account SID** and **Auth Token** → put in `.env`.
3. Console → Messaging → Try it out → **Send a WhatsApp message** → follow the sandbox
   join instructions (send the given join code to the sandbox number from your phone).
4. `TWILIO_WHATSAPP_FROM` = the sandbox number shown, prefixed `whatsapp:` (default
   `whatsapp:+14155238886`). `MY_WHATSAPP_NUMBER` = your phone in `whatsapp:+1XXXXXXXXXX` form.
5. Sandbox is free but requires re-joining periodically and only messages verified
   testers — fine for Phase 0–early phases. A paid WhatsApp sender is a later step
   once we're ready for unattended production use.
6. **Content Template (required for any message you send first, e.g. the 4AM digest):**
   WhatsApp only allows freeform text within the 24h session window opened when the
   recipient messages you. A message you initiate outside that window — like a
   proactive daily digest — must reference a pre-approved template instead.
   - Console → Messaging → Content Template Builder → create a new template
     (type "Text"), write the body (use `{{1}}`, `{{2}}`, ... for variables you'll
     fill in per-send), and submit.
   - Sandbox templates are usable immediately, no WhatsApp/Meta review needed. A
     template on a real production WhatsApp sender (later phase) requires Meta
     approval, which can take hours.
   - Copy the resulting Content SID (`HX...`) into `TWILIO_CONTENT_SID`. If your
     template has variables, set `TWILIO_CONTENT_VARIABLES` to a JSON string like
     `{"1":"some value","2":"other value"}`.
   - Leave both blank to send plain freeform text instead — only works if you (the
     recipient) messaged the sandbox within the last 24 hours.

## Google Cloud (Calendar + Tasks)
1. console.cloud.google.com → create a new project.
2. APIs & Services → Library → enable **Google Calendar API** and **Google Tasks API**.
3. APIs & Services → Credentials → Create Credentials → OAuth client ID → Application
   type **Desktop app**.
4. Configure the OAuth consent screen as **Testing**, add your own Google account as a
   test user (avoids needing Google's app-review process).
5. Download the client JSON, save it as `credentials.json` in the repo root (path
   matches `GOOGLE_CLIENT_SECRET_FILE` in `.env.example`).
6. First script run opens a browser for one-time consent; it caches a refresh token to
   `token.json` automatically. Delete `token.json` to force re-consent.

## Moodle
1. Log in to NC State's Moodle → Preferences → **Security keys** (a.k.a. "Manage
   tokens"). If you see an option to create a web service token, generate one and put
   it in `MOODLE_TOKEN`.
2. **If that option isn't available** (common for student accounts — institutions
   often restrict it): use the built-in calendar export instead. Moodle → Calendar →
   gear icon → **Export calendar** → choose "Events I am supplying" scope covering the
   relevant calendars, "This calendar" or similar → **Get calendar URL** → copy that
   webcal/ICS link into `MOODLE_ICS_URL`.
3. `MOODLE_BASE_URL` = your Moodle site's base URL (only needed if using the token path).
4. Note: the ICS fallback covers calendar/due dates only, not grades. If Phase 2 needs
   grades and the token path is unavailable, we'll revisit (likely manual entry or
   asking an instructor/IT for API access).

## Weather
1. Sign up free at openweathermap.org/api → generate an API key (may take a few
   minutes to activate).
2. Put it in `OPENWEATHER_API_KEY`. `WEATHER_CITY` defaults to `Raleigh,US`.

## Anthropic (Claude)
1. console.anthropic.com → API Keys → create a key.
2. Put it in `ANTHROPIC_API_KEY`.

## Once all six are filled in
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.integrations.whatsapp
python -m src.integrations.google_calendar
python -m src.integrations.google_tasks
python -m src.integrations.moodle
python -m src.integrations.weather
python -m src.integrations.llm
```
Phase 0 is done when all six run and return real data (see PROJECT.md verification).
