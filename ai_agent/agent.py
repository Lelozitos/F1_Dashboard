"""Claude tool-use agent for F1 data analysis. Requires ANTHROPIC_API_KEY (or an
`ant auth login` profile) in the environment - never hardcode a key here."""
from __future__ import annotations

import datetime

import anthropic

from tools import ALL_TOOLS

MODEL = "claude-opus-5"

SYSTEM_PROMPT = f"""You are an F1 data analyst assistant. Today's date is {datetime.date.today().isoformat()}.

Use the available tools to fetch real FastF1, Ergast and OpenF1 data before answering any question about \
drivers, teams, sessions, standings, lap times, or pit stops. Never guess numbers - always look them up.

Session identifiers are "FP1", "FP2", "FP3", "Q", "S" (sprint) and "R" (race). Data only goes back to 2018. \
Pit stop data comes from OpenF1 and is occasionally incomplete - say so if a pit stop query returns nothing.

When a tool returns an error, tell the user what went wrong instead of making up data. Keep answers concise \
and cite the specific round/session/driver the numbers came from."""


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def run_turn(client: anthropic.Anthropic, messages: list[dict]):
    """Run one user turn to completion.

    Returns (final_text, updated_messages, tool_calls) where updated_messages is
    the full conversation history (including tool_use/tool_result blocks) to pass
    back in on the next turn, and tool_calls lists the tool names invoked in order.
    """
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive", "display": "summarized"},
        tools=ALL_TOOLS,
        messages=messages,
    )

    updated = list(messages)
    tool_calls = []
    last = None

    for message in runner:
        last = message
        updated.append({"role": "assistant", "content": message.content})
        for block in message.content:
            if block.type == "tool_use":
                tool_calls.append(block.name)
        tool_response = runner.generate_tool_call_response()
        if tool_response is not None:
            updated.append(tool_response)

    final_text = ""
    if last is not None:
        final_text = "".join(b.text for b in last.content if b.type == "text")

    return final_text, updated, tool_calls
