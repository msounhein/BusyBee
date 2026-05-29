"""
Unified LLM client for GLM-5.1 (Z.AI).

All LLM calls go through this module. Handles:
- API connection (auth, URL, timeout)
- Thinking/reasoning budget
- Response parsing (thinking tag extraction)
- Tool call extraction from content (ACTION blocks, XML)
"""
import json
import re
import requests
from config import Config


# Defaults — override per-call via kwargs
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_OUTPUT_TOKENS = 131072     # GLM-5.1 maximum output token limit
THINKING_BUDGET_TOKENS = 16384         # tokens for reasoning scratchpad


def _get_llm_config():
    """Retrieve LLM config from database, falling back to environment variables."""
    import os
    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        profile = db.query(models.Profile).filter(models.Profile.id == 1).first()
        if profile and profile.llm_provider:
            provider = profile.llm_provider
            api_key = profile.llm_api_key
            model = profile.llm_model
            api_url = profile.llm_api_url
            
            # Use defaults from Config if database values are empty
            if not api_key:
                api_key = Config.ZAI_API_KEY if provider == 'zai' else os.getenv('OPENAI_API_KEY', '')
            if not model:
                model = 'glm-5.1' if provider == 'zai' else 'gpt-4o-mini'
            if not api_url:
                if provider == 'zai':
                    api_url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
                elif provider == 'openai':
                    api_url = "https://api.openai.com/v1/chat/completions"
                elif provider == 'openrouter':
                    api_url = "https://openrouter.ai/api/v1/chat/completions"
                else:
                    api_url = ""
            return provider, api_key, model, api_url
    except Exception as e:
        print(f"[llm_client] Error loading LLM config from DB: {e}")
    finally:
        db.close()

    # Fallback to Config
    provider = os.getenv('LLM_PROVIDER', 'zai')
    api_key = Config.ZAI_API_KEY
    model = Config.MINIMAX_MODEL
    api_url = Config.MINIMAX_API_URL
    return provider, api_key, model, api_url


def call_llm(
    messages,
    *,
    tools=None,
    tool_choice=None,
    temperature=DEFAULT_TEMPERATURE,
    max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
    thinking_budget=THINKING_BUDGET_TOKENS,
    timeout=180,
    strip_thinking=True,
):
    """
    Make a chat completion request to the configured LLM provider.
    """
    provider, api_key, model, api_url = _get_llm_config()

    payload = {
        "model": model,
        "messages": messages,
    }

    # Only send temperature if it's supported (some o1 models don't support it, but for safety we send it)
    payload["temperature"] = temperature

    # Set token limits
    if "o1" in model.lower() or "o3" in model.lower():
        payload["max_completion_tokens"] = max_tokens
    else:
        payload["max_tokens"] = max_tokens

    # Only enable Z.AI's custom thinking parameter if provider is Z.AI
    if provider == 'zai' and thinking_budget and thinking_budget > 0:
        payload["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget,
        }

    if tools:
        payload["tools"] = tools
    if tool_choice:
        payload["tool_choice"] = tool_choice

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == 'openrouter':
        headers["HTTP-Referer"] = "https://github.com/msounhein/job-tracker"
        headers["X-Title"] = "BusyBee Job Tracker"

    # Retry on transient errors (429 rate limit, 500/502/503 server errors)
    import time
    last_error = None
    for attempt in range(3):
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if response.status_code in (400, 429, 500, 502, 503):
            last_error = f"LLM API error {response.status_code} ({provider}): {response.text[:200]}"
            wait = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait)
            continue
        response.raise_for_status()
        break
    else:
        # All retries exhausted
        raise Exception(last_error or f"LLM API failed after 3 attempts ({provider})")

    result = response.json()
    message = result["choices"][0]["message"]
    raw_content = message.get("content", "") or ""

    # Extract thinking before stripping
    thinking = _extract_thinking(raw_content)

    # Fallback: check reasoning_content parameter (OpenAI / DeepSeek spec)
    reasoning_content = message.get("reasoning_content", None)
    if reasoning_content and not thinking:
        thinking = reasoning_content

    # Strip thinking tags from the display content
    content = strip_thinking_tags(raw_content) if strip_thinking else raw_content

    # Native tool calls
    native_tool_calls = message.get("tool_calls", []) or []

    # Fallback: parse tool calls from content text (ACTION blocks, XML)
    from llm_helpers import parse_tool_calls_from_content
    content, parsed_tools = parse_tool_calls_from_content(content)

    return {
        "content": content.strip(),
        "tool_calls": native_tool_calls,
        "parsed_tool_calls": parsed_tools,
        "thinking": thinking,
        "reasoning_content": reasoning_content,
        "raw_message": message,
        "finish_reason": result["choices"][0].get("finish_reason", ""),
        "usage": result.get("usage", {}),
    }


def _extract_thinking(text):
    """Extract the raw thinking/reasoning content from <think> tags."""
    matches = re.findall(r"<think>(.*?)</think>", text, re.DOTALL)
    return "\n".join(matches)


def strip_thinking_tags(text):
    """Remove <think>...</think> tags from model output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
