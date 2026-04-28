"""AI provider — direct httpx client for OpenAI-compatible APIs.

Supports Ollama, OpenAI, and Anthropic. Uses OpenAI function-calling
wire format as the canonical format. Translates to/from Anthropic format
when needed, so agent.py never has to care which backend it's talking to.
"""
import json
import httpx
from backend.config import settings


# ─── Provider-specific endpoint mapping ──────────────────────────────

PROVIDER_DEFAULTS = {
    "ollama": {
        "base_url": "http://localhost:11434",
        "chat_path": "/api/chat",
        "format": "ollama",
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "chat_path": "/v1/chat/completions",
        "format": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "chat_path": "/v1/messages",
        "format": "anthropic",
    },
}


def _get_provider_config(db=None) -> dict:
    """Resolve the active provider: AppConfig overrides env."""
    provider = settings.AI_PROVIDER.lower()
    base_url = settings.AI_BASE_URL
    model = settings.AI_MODEL
    api_key = settings.AI_API_KEY

    # AppConfig overrides (best-effort; fall back to env on any error)
    try:
        from backend.db.models import AppConfig
        if db is None:
            from backend.db.database import SessionLocal
            with SessionLocal() as scoped_db:
                override = _provider_overrides(scoped_db, AppConfig)
        else:
            override = _provider_overrides(db, AppConfig)
        if override.get("ai_provider_override"):
            provider = override["ai_provider_override"].lower()
        if override.get("ai_base_url_override"):
            base_url = override["ai_base_url_override"]
        if override.get("ai_model_override"):
            model = override["ai_model_override"]
        if override.get("ai_api_key_override"):
            api_key = override["ai_api_key_override"]
    except Exception:
        pass

    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["openai"])
    if not base_url:
        base_url = defaults["base_url"]
    return {
        "base_url": base_url,
        "chat_path": defaults["chat_path"],
        "format": defaults["format"],
        "model": model,
        "api_key": api_key,
        "provider": provider,
    }


def _provider_overrides(db, app_config_model) -> dict:
    from backend.security import decrypt_value

    overrides = {
        row.key: row.value
        for row in db.query(app_config_model).filter(
            app_config_model.key.in_([
                "ai_provider_override",
                "ai_base_url_override",
                "ai_model_override",
                "ai_api_key_override",
            ])
        ).all()
    }
    if overrides.get("ai_api_key_override"):
        overrides["ai_api_key_override"] = decrypt_value(overrides["ai_api_key_override"])
    return overrides


# ─── Chat completion (non-streaming) ────────────────────────────────

async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.3,
) -> dict:
    """
    Send a chat completion request. Returns a unified response dict:
    {
        "content": str | None,
        "tool_calls": [{"id": str, "function": {"name": str, "arguments": str}}] | None,
        "usage": {"prompt_tokens": int, "completion_tokens": int} | None,
    }
    """
    config = _get_provider_config()

    if config["format"] == "anthropic":
        return await _anthropic_completion(config, messages, tools, temperature)
    elif config["format"] == "ollama":
        return await _ollama_completion(config, messages, tools, temperature)
    else:
        return await _openai_completion(config, messages, tools, temperature)


async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.3,
):
    """Streaming chat completion. Yields content chunks as strings."""
    config = _get_provider_config()

    if config["format"] == "anthropic":
        async for chunk in _anthropic_stream(config, messages, tools, temperature):
            yield chunk
    elif config["format"] == "ollama":
        async for chunk in _ollama_stream(config, messages, tools, temperature):
            yield chunk
    else:
        async for chunk in _openai_stream(config, messages, tools, temperature):
            yield chunk


# ─── OpenAI format ───────────────────────────────────────────────────

async def _openai_completion(config, messages, tools, temperature):
    body = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        body["tools"] = tools

    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{config['base_url']}{config['chat_path']}",
            json=body,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data.get("choices", [{}])[0].get("message", {})
    return {
        "content": choice.get("content"),
        "tool_calls": choice.get("tool_calls"),
        "usage": data.get("usage"),
    }


async def _openai_stream(config, messages, tools, temperature):
    body = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if tools:
        body["tools"] = tools

    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{config['base_url']}{config['chat_path']}",
            json=body,
            headers=headers,
            timeout=120,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    chunk = json.loads(line[6:])
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content


# ─── Ollama format ───────────────────────────────────────────────────

async def _ollama_completion(config, messages, tools, temperature):
    body = {
        "model": config["model"],
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if not tools and _looks_like_json_task(messages):
        body["format"] = "json"
    if tools:
        body["tools"] = tools  # Ollama supports OpenAI tool format

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{config['base_url']}{config['chat_path']}",
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

    message = data.get("message", {})
    return {
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls"),
        "usage": None,
    }


async def _ollama_stream(config, messages, tools, temperature):
    body = {
        "model": config["model"],
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature},
    }

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{config['base_url']}{config['chat_path']}",
            json=body,
            timeout=120,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.strip():
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content


def _looks_like_json_task(messages: list[dict]) -> bool:
    text = "\n".join(str(m.get("content", "")) for m in messages[-2:]).lower()
    return "return json" in text or "json only" in text


# ─── Anthropic format (translation layer) ────────────────────────────

def _messages_to_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert OpenAI messages format to Anthropic format."""
    system = ""
    anthropic_msgs = []

    for msg in messages:
        if msg["role"] == "system":
            system = msg.get("content", "")
        else:
            role = "assistant" if msg["role"] == "assistant" else "user"
            anthropic_msgs.append({"role": role, "content": msg.get("content", "")})

    return system, anthropic_msgs


def _tools_to_anthropic(tools: list[dict]) -> list[dict]:
    """Convert OpenAI tools format to Anthropic format."""
    anthropic_tools = []
    for tool in tools:
        fn = tool.get("function", {})
        anthropic_tools.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {}),
        })
    return anthropic_tools


async def _anthropic_completion(config, messages, tools, temperature):
    system, anthropic_msgs = _messages_to_anthropic(messages)

    body = {
        "model": config["model"],
        "max_tokens": 4096,
        "messages": anthropic_msgs,
        "temperature": temperature,
    }
    if system:
        body["system"] = system
    if tools:
        body["tools"] = _tools_to_anthropic(tools)

    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{config['base_url']}{config['chat_path']}",
            json=body,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

    # Translate Anthropic response back to OpenAI format
    content = None
    tool_calls = None

    for block in data.get("content", []):
        if block["type"] == "text":
            content = block["text"]
        elif block["type"] == "tool_use":
            if tool_calls is None:
                tool_calls = []
            tool_calls.append({
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block["input"]),
                },
            })

    return {
        "content": content,
        "tool_calls": tool_calls,
        "usage": data.get("usage"),
    }


async def _anthropic_stream(config, messages, tools, temperature):
    system, anthropic_msgs = _messages_to_anthropic(messages)

    body = {
        "model": config["model"],
        "max_tokens": 4096,
        "messages": anthropic_msgs,
        "temperature": temperature,
        "stream": True,
    }
    if system:
        body["system"] = system

    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
    }

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{config['base_url']}{config['chat_path']}",
            json=body,
            headers=headers,
            timeout=120,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = json.loads(line[6:])
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")


# ─── Utility ─────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Check if an AI provider is configured and reachable."""
    return bool(settings.AI_PROVIDER and settings.AI_MODEL)
