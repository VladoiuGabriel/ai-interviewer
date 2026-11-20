# AI Interviewer

A small terminal app inspired by [Anthropic Interviewer](https://www.anthropic.com/news/anthropic-interviewer).
It runs a short, adaptive AI interview on a topic you choose, then summarizes your answers
(themes, sentiment, key points, quotes, keywords) and saves everything as JSON.

## Setup

You need a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cp .env.example .env    # then add your API key
```

### Run locally (Python 3.10+)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python cli.py
```

### Run with Docker

```bash
docker compose build
docker compose run --rm interviewer
```

Interviews are saved to `transcripts/`. Sample output is in `examples/`.

## How it works

1. **Plan:** the AI drafts a goal and a few themes for the topic.
2. **Interview:** 3–5 questions, generated one at a time, each following up on your previous answers.
3. **Summary:** the AI summarizes the transcript. Quotes are then verified in code and sentiment
   is cross-checked locally with VADER.

## Project structure

```
core/
  llm.py         # Gemini API wrapper (the only provider-specific code)
  prompts.py     # all prompts
  interview.py   # interview flow, independent of the UI
  analysis.py    # quote verification, VADER sentiment, stats
  storage.py     # JSON persistence
cli.py           # terminal UI
```

## Notes

- The model is set via `GEMINI_MODEL` in `.env`.
- The Gemini free tier has a daily request limit per model. One 5-question interview uses 7 requests.
- VADER sentiment only works for English.
