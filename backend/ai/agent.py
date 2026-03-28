"""AI agent — tool-use loop with streaming support."""
import json
from sqlalchemy.orm import Session
from backend.ai import provider, tools


SYSTEM_PROMPT = """You are ClawFin, an AI financial assistant for a Canadian user. You have access to their personal financial data including bank transactions, investment holdings, and account balances.

Rules:
- Always use the available tools to look up real data before answering. Never guess or hallucinate numbers.
- Format currency as CAD unless the data is in another currency.
- Be concise and data-driven. Show numbers, not prose.
- When showing spending breakdowns, include both absolute amounts and percentages.
- For investment questions, reference actual holdings and their performance.
- You can run simulations when asked "what if" questions.
- Never provide financial advice. Present data and let the user decide.
- Use Canadian financial terminology (TFSA, RRSP, FHSA, etc.).
"""


async def run_agent(user_message: str, db: Session, conversation_history: list[dict] | None = None) -> str:
    """
    Run the agent loop: send message → LLM calls tools → execute → return final response.
    Non-streaming version for simple responses.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # Agent loop (max 5 iterations to prevent infinite loops)
    for _ in range(5):
        response = await provider.chat_completion(
            messages=messages,
            tools=tools.TOOL_DEFINITIONS,
            temperature=0.3,
        )

        # If LLM returned text content (no tool calls), we're done
        if response.get("content") and not response.get("tool_calls"):
            return response["content"]

        # If LLM wants to call tools
        if response.get("tool_calls"):
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": response["tool_calls"],
            })

            # Execute each tool call
            for tool_call in response["tool_calls"]:
                fn_name = tool_call["function"]["name"]
                fn_args = json.loads(tool_call["function"]["arguments"])

                result = tools.execute_tool(fn_name, fn_args, db)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })

            # Continue loop — LLM will process tool results
            continue

        # No content and no tool calls — shouldn't happen
        return "I couldn't process that request. Please try again."

    return "I ran out of steps processing your request. Please try a simpler question."


async def run_agent_stream(user_message: str, db: Session, conversation_history: list[dict] | None = None):
    """
    Streaming agent. For the initial response, if tools are needed,
    runs the full tool loop first, then streams the final response.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # First pass: check if tools are needed (non-streaming)
    response = await provider.chat_completion(
        messages=messages,
        tools=tools.TOOL_DEFINITIONS,
        temperature=0.3,
    )

    # No tool calls — stream the response directly
    if not response.get("tool_calls"):
        if response.get("content"):
            yield response["content"]
        return

    # Execute tool calls
    messages.append({
        "role": "assistant",
        "content": response.get("content"),
        "tool_calls": response["tool_calls"],
    })

    for tool_call in response["tool_calls"]:
        fn_name = tool_call["function"]["name"]
        fn_args = json.loads(tool_call["function"]["arguments"])
        result = tools.execute_tool(fn_name, fn_args, db)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": result,
        })

    # Stream the final response (after tool results)
    async for chunk in provider.chat_completion_stream(
        messages=messages,
        temperature=0.3,
    ):
        yield chunk
