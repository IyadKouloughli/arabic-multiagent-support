# -*- coding: utf-8 -*-
"""Multi-provider LLM interface supporting Gemini, OpenAI, Groq, and Ollama."""
import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.config import (
    LLM_PROVIDER,
    GOOGLE_API_KEY,
    OPENAI_API_KEY,
    GROQ_API_KEY,
    DEFAULT_MAIN_MODEL,
    TEMPERATURE
)


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Any = None
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMClient:
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = TEMPERATURE,
        model: Optional[str] = None
    ) -> LLMResponse:
        raise NotImplementedError


class GeminiClient(BaseLLMClient):
    """Google Gemini client via the official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        from google import genai
        key = api_key or GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", "")
        self.client = genai.Client(api_key=key) if key else genai.Client()
        self.default_model = default_model or DEFAULT_MAIN_MODEL

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = TEMPERATURE,
        model: Optional[str] = None
    ) -> LLMResponse:
        import time
        from google.genai import types
        chosen_model = model or self.default_model
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt if system_prompt else None
        )

        last_err = None
        for attempt in range(4):
            try:
                resp = self.client.models.generate_content(
                    model=chosen_model,
                    contents=prompt,
                    config=config
                )
                text = resp.text or ""
                return LLMResponse(
                    text=text,
                    raw_response=resp
                )
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    last_err = e
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise e
        raise last_err


class OpenAIClient(BaseLLMClient):
    """OpenAI or OpenAI-compatible client (e.g., Ollama, vLLM)."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, default_model: str = "gpt-4o-mini"):
        from openai import OpenAI
        key = api_key or OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "dummy")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.default_model = default_model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = TEMPERATURE,
        model: Optional[str] = None
    ) -> LLMResponse:
        chosen_model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature
        }

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        text = choice.message.content or ""

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_calls.append(ToolCall(name=fn_name, args=args))

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw_response=resp,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0
        )


class GroqClient(BaseLLMClient):
    """Groq client for low-latency models (Llama 3.3, Qwen)."""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        key = api_key or GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        self.client = Groq(api_key=key)
        self.default_model = default_model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = TEMPERATURE,
        model: Optional[str] = None
    ) -> LLMResponse:
        chosen_model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            temperature=temperature
        )
        choice = resp.choices[0]
        text = choice.message.content or ""

        return LLMResponse(
            text=text,
            raw_response=resp,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0
        )


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Factory to get the appropriate LLM client."""
    p = (provider or LLM_PROVIDER or "gemini").lower()
    if p == "gemini":
        return GeminiClient()
    elif p in ("openai", "ollama"):
        base_url = "http://localhost:11434/v1" if p == "ollama" else None
        return OpenAIClient(base_url=base_url)
    elif p == "groq":
        return GroqClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {p}")
