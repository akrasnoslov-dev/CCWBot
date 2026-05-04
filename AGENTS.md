# CCWBot Codex Instructions

## Workflow

- Keep changes small and focused.
- Do not modify files outside the current task scope.
- Prefer creating a pull request instead of pushing directly to `main`.
- Show or summarise the diff before finalising changes.
- Do not make broad refactors unless the task explicitly asks for refactoring.
- Auto-review is okay, but do not auto-merge changes into `main` unless the user explicitly asks for it.

## Protected files

Do not modify these files unless the current task explicitly asks for it:

- `docker-compose.yml`
- `.env.example`
- `requirements.txt`
- `README.md`

If changing one of these files is necessary, keep the change minimal and explain why.

## Docker Compose rules

`docker-compose.yml` is known to work in the current local setup.

Do not reformat, restructure, rename services, change volume names, change ports, or change environment variables in `docker-compose.yml` unless the task explicitly says:

> Modify `docker-compose.yml`

A valid Docker Compose file for this project must keep services under the top-level `services:` key.

Never place `postgres:` at the top level.

Correct structure:

```yaml
services:
  postgres:
    image: postgres:16
    container_name: ccwbot-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ccwbot
      POSTGRES_USER: ccwbot
      POSTGRES_PASSWORD: ccwbot_password
    ports:
      - "5432:5432"
    volumes:
      - ccwbot_postgres_data:/var/lib/postgresql/data

volumes:
  ccwbot_postgres_data:
```

After any change to `docker-compose.yml`, run:

```bash
docker compose config
```

## Safety rules

- Never modify `.env`.
- Never commit secrets.
- Never commit `state.json`.
- Never commit `.venv`, `__pycache__`, `.pyc`, database volume files, `.db`, or `.sqlite` files.
- Do not rename `ai_agent_groq.py`.
- Keep PostgreSQL support optional unless the task explicitly changes this.

## Database rules

- Telegram IDs must use `BigInteger`, not `Integer`.
- PostgreSQL is the primary runtime store when `DATABASE_URL` is configured.
- `state.json` is fallback only when `DATABASE_URL` is not configured.
- Do not add Alembic migrations unless explicitly requested.
- Do not change existing database table names unless explicitly requested.
- If database schema changes are required, explain whether the local PostgreSQL volume needs to be recreated.

## Bot behaviour rules

- Keep automatic alerts BTC-only unless the task explicitly changes this.
- Keep supported manual price symbols unchanged unless explicitly requested:
  - `btc`
  - `eth`
  - `ton`
  - `usdt`
- Keep admin-only commands protected.
- Keep `TELEGRAM_ADMIN_USER_ID` for admin permissions.
- Keep `TELEGRAM_CHAT_ID` / alert chat configuration for alert delivery.
- Do not expose admin-only commands to normal users.
- Do not add direct financial advice such as “buy now” or “sell now”.
- Use cautious decision-support language and keep “Not financial advice.” where appropriate.

## AI / Groq rules

- Keep Groq as the current AI provider unless explicitly requested.
- Do not rename `ai_agent_groq.py`.
- Do not log API keys, secrets, or full environment variables.
- Keep AI outputs user-readable.
- Do not send internal prompt/debug data to Telegram messages.
- Related news links should use real title/source/link values from `news_service.py`, not AI-invented sources or URLs.

## Testing

Before finalising Python changes, run:

```bash
python -m py_compile main.py config.py database.py storage.py alert_rules.py price_service.py news_service.py ai_agent_groq.py
```

If this creates `__pycache__` or `.pyc` files, remove them before committing.

Before finalising Docker Compose changes, run:

```bash
docker compose config
```

## Final checklist before PR or commit

- Only intended files are changed.
- `.env` is not changed.
- `state.json` is not included.
- `.venv`, `__pycache__`, `.pyc`, database files, and generated files are not included.
- `docker-compose.yml` still contains top-level `services:`.
- The bot still starts locally.
- The change matches the requested task scope.
