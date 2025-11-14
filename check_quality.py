import anthropic
import os
from datetime import datetime


def run_quality_check():
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    # System prompt completo
    system_prompt = """
    # Claude System Prompt — Gueno: Linear Weekly TODOs Quality Agent
    (⬇️ pega aquí tu prompt completo)
    """

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=8000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": "Run complete quality check on Weekly TODOs project. List all issues, scan all tasks, and post comments where needed."
            }
        ],
        tools=[
            # ⬇️ Aquí agregás tus MCP tools para Linear
            # ej.: {"type": "...", "name": "...", "description": "..."}
        ]
    )

    print(f"[{datetime.now()}] Quality check completed")
    print(f"Response: {message.content}")

    return message


if __name__ == "__main__":
    run_quality_check()
