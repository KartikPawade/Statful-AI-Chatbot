# Stateful-AI-Chatbot

## Overview
This repository contains a **simple Stateful AI Chatbot** that can make LLM calls using:

- **Gemini** (Google)
- **Ollama** with **Llama3** model (local) using docker image

The chatbot is “stateful” because it **maintains conversation context** across messages using a memory strategy (see below).

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