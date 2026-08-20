"""harness-second-opinion — cross-model review via any OpenAI-compatible API.

Gives Claude a genuinely independent second set of eyes: adversarial code
review, counter-positions for debates, and plain second opinions. The remote
model sees only what is explicitly passed in — no ambient context leaks.
"""
import httpx

from mcp.server.mcpserver import MCPServer

import harness_env as env

mcp = MCPServer("harness-second-opinion")


def _chat(system: str, user: str) -> dict:
    key = env.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set — add it to ~/claude-setup/harness.env")
    model = env.get("SECOND_OPINION_MODEL", "gpt-5.6-sol")
    base = env.get("SECOND_OPINION_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    effort = env.get("SECOND_OPINION_REASONING_EFFORT")
    if effort:
        body["reasoning_effort"] = effort
    r = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=body,
        timeout=300,
    )
    if r.status_code >= 400:
        try:
            err = r.json().get("error", {})
            detail = err.get("message", r.text[:300])
        except Exception:
            detail = r.text[:300]
        hint = {
            401: "the key in ~/claude-setup/harness.env is invalid, revoked, or for a different provider",
            404: f"model '{model}' is not available to this account — set SECOND_OPINION_MODEL to one it can use",
            429: "rate limit or exhausted quota on this account",
        }.get(r.status_code, "")
        raise RuntimeError(
            f"second-opinion API error {r.status_code}: {detail}" + (f" — {hint}" if hint else "")
        )
    data = r.json()
    return {"model": model, "answer": data["choices"][0]["message"]["content"]}


@mcp.tool()
def second_opinion(question: str, context: str = "") -> dict:
    """Ask the external model for an independent opinion on a question.
    Include ALL relevant context explicitly — the model sees nothing else."""
    system = (
        "You are an independent senior expert consulted for a second opinion. "
        "Be direct and specific. If you disagree with an implied assumption, say so. "
        "Answer in the language of the question."
    )
    user = f"{question}\n\n## Context\n{context}" if context else question
    return _chat(system, user)


@mcp.tool()
def review(content: str, focus: str = "", context: str = "") -> dict:
    """Adversarial review of code/diff/plan/design by the external model.
    focus: optional area to stress (security, correctness, architecture, gas, ...).
    Returns numbered findings with severity; no praise, no fluff."""
    system = (
        "You are a ruthless senior reviewer doing an independent audit. "
        "Report ONLY problems as a numbered list. For each: "
        "[SEVERITY: critical|high|medium|low] — claim — exact location/quote — "
        "concrete failure scenario. No compliments, no summaries of what the code does. "
        "If you find nothing significant, say exactly that. "
        "Respond in the language the request was written in."
    )
    parts = ["## Material under review", content]
    if focus:
        parts += ["## Focus", focus]
    if context:
        parts += ["## Context", context]
    return _chat(system, "\n\n".join(parts))


@mcp.tool()
def counter_position(question: str, position: str, context: str = "") -> dict:
    """Get the strongest possible counter-argument to a stated position.
    Used for structured debates: the external model must argue AGAINST."""
    system = (
        "You are a formidable opponent in a structured technical debate. "
        "Attack the given position with the strongest counter-arguments you can build: "
        "hidden assumptions, failure modes, better alternatives, real-world evidence. "
        "Steelman first in one line, then attack point by point. "
        "If after honest analysis you conclude the position is actually correct, "
        "concede explicitly and state why. Answer in the language of the question."
    )
    parts = [f"## Question\n{question}", f"## Position to attack\n{position}"]
    if context:
        parts.append(f"## Context\n{context}")
    return _chat(system, "\n\n".join(parts))


if __name__ == "__main__":
    mcp.run()
