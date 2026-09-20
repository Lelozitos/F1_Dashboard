"""Gemini tool-use agent for F1 data analysis. Requires GEMINI_API_KEY (free key
at aistudio.google.com) in the environment - never hardcode a key here."""
from __future__ import annotations

import datetime
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import ALL_TOOLS

# Loads ai_agent/.env if present (GEMINI_API_KEY=...). Real env vars set
# outside still take precedence - load_dotenv() never overwrites an existing var.
load_dotenv()

# gemini-flash-lite-latest is the cheapest current Gemini model, with the highest
# free-tier quota - good default for testing. "gemini-flash-latest" resolves to a
# pricier full flash model, avoid it for casual testing.
# Override with: set GEMINI_MODEL=gemini-2.5-pro (or any other Gemini model)
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

SYSTEM_PROMPT = f"""You are an F1 data analyst assistant. Today's date is {datetime.date.today().isoformat()}.

Use the available tools to fetch real FastF1, Ergast and OpenF1 data before answering any question about \
drivers, teams, sessions, standings, lap times, or pit stops. Never guess numbers - always look them up.

Session identifiers are "FP1", "FP2", "FP3", "Q", "S" (sprint) and "R" (race). Data only goes back to 2018. \
Pit stop data comes from OpenF1 and is occasionally incomplete - say so if a pit stop query returns nothing.

When a tool returns an error, tell the user what went wrong instead of making up data. Keep answers concise \
and cite the specific round/session/driver the numbers came from."""


def get_client() -> genai.Client:
    return genai.Client()


def new_chat(client: genai.Client):
    """Start a fresh chat session with tools wired in.

    Gemini's automatic function calling runs the whole tool loop internally
    (call model -> run tool -> feed result back -> repeat) - unlike Claude's
    tool runner, there's no manual history mirroring to do here.
    """
    return client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
        ),
    )


def run_turn(chat, user_message: str) -> tuple[str, list[str]]:
    """Send one message on an existing chat session.

    Returns (final_text, tool_calls) - tool_calls lists, in order, the names
    of every tool Gemini invoked while answering this turn.
    """
    history_before = len(chat.get_history())
    response = chat.send_message(user_message)

    tool_calls = []
    for turn in chat.get_history()[history_before:]:
        for part in turn.parts:
            if part.function_call is not None:
                tool_calls.append(part.function_call.name)

    return response.text or "", tool_calls
