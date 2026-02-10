# Stateful-AI-Chatbot

## Overview
This repository contains a **Stateful AI Chatbot** that makes LLM calls using:

- **Gemini** (Google)
- **Ollama** with **Llama** models (local), e.g. **Llama3**

The chatbot is “stateful” because it **maintains conversation context** for sessionacross messages using a configurable memory strategy (see below). Provider calls match a minimal FastAPI setup: **Gemini** via `client.models.generate_content(model=..., contents=prompt)` and **Ollama** via `client.chat(model=..., messages=[...])`. API keys and host/model settings are read from **`.env`** (see **Run Locally**).

## Persistence (Redis)
History is **not** kept in process memory. It is stored in **Redis** so it survives restarts and scales across instances.

- **Run Redis in WSL with Docker** (recommended):
  ```bash
  docker run -d --name redis -p 6379:6379 redis:alpine
  ```
- Set `REDIS_URL=redis://localhost:6379/0` in `.env`. From Windows, `localhost` reaches WSL’s forwarded port.

## Professional Request Flow
1. **Request**: User sends a message and a `session_id`.
2. **Fetch**: The API loads the last N messages (and any rolling summary) from Redis.
3. **Truncation**: If the history exceeds a token limit, a **summarization** pass runs first; the summary and a bounded recent window are kept.
4. **Call**: The managed history is sent to the LLM (Gemini or Ollama).
5. **Save**: The new user/assistant pair is written to Redis.

## Project Structure (Controller vs Service Layer)
- **Controller / Routes**: `app/api/routes.py` (FastAPI endpoints)
- **Service layer**: `app/services/chat_service.py` (provider switch, fetch → truncate → call → save)
- **Persistence**: `app/db/redis_store.py` (Redis chat repository: fetch/save/trim/summary)
- **LLM providers**: `app/services/llm/providers.py` (Gemini + Ollama client wrappers)
- **Memory strategies**: `app/services/memory/memory.py` (Rolling summary + Sliding window)

## Context / Memory Strategies

### Summarization (the “Rolling” Memory)
Instead of deleting old messages, you **compress** them into a smaller summary.

- **How it works**: Every time the history hits a limit, the app calls the LLM internally with a prompt like:  
  “**Summarize the key points of this chat so far.**”  
  Then it replaces older turns with that summary + keeps the most recent messages.
- **Best for**: Longer conversations where you want continuity without sending the full history every time.
- **Benefit**: Preserves key facts/goals while keeping token usage under control.

### Sliding Window (the “Short‑Term” Memory)
You only keep the last \(N\) messages.

- **How it works**: Maintain a list of messages. When message #11 comes in, delete message #1 (so you always keep only the last \(N\)).
- **Best for**: Casual chatbots or customer support where only the immediate context matters.
- **Risk**: **“Identity Crisis.”** If the user shared their name or a key preference in message #1, by message #12 the AI may “forget” it.

## API Endpoints
- **GET `/`**: Health check
- **GET `/ask`**: Ask the AI (Gemini or Ollama)  
  - Query params:
    - `prompt` (required)
    - `provider` (optional): `gemini` | `ollama`
    - `session_id` (optional): enables stateful context across calls
    - `memory` (optional): `rolling` | `window` | `none`
- **GET `/models`**: Lists Gemini models (requires Gemini credentials)

## Run Locally
1. Create a virtualenv and install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy `.env.example` to `.env` in the project root):
   - **`GOOGLE_API_KEY`** — required for Gemini (omit if you use only Ollama)
   - **`REDIS_URL`** — e.g. `redis://localhost:6379/0`; run Redis (e.g. in WSL with Docker; see **Persistence** above)
   - **`OLLAMA_HOST`** / **`OLLAMA_MODEL`** — default `http://localhost:11434` and `llama3`; ensure Ollama is running if using `provider=ollama`

3. Start the server:

```bash
uvicorn app.main:app --reload
```

## Example Requests
- Gemini (stateless):
  - `GET /ask?provider=gemini&prompt=Hello`
- Ollama (stateful rolling memory):
  - `GET /ask?provider=ollama&session_id=my-session&memory=rolling&prompt=Remember my name is Kartik`
