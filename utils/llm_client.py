
import os
from ollama import chat
from google import genai
from google.genai import types

# Local model configuration
OLLAMA_MODEL = "qwen3:1.7b"

# Cloud model configuration
GEMINI_MODEL = "gemini-3.6-flash"


def get_secret(name):
    """
    Read a configuration value from environment variables
    or Streamlit Cloud secrets.
    """
    value = os.getenv(name)

    if value:
        return value

    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def generate_llm_response(system_prompt, user_prompt):
    """
    Generate a response using either:
    - Ollama locally
    - Gemini API in the cloud

    Select the provider using LLM_PROVIDER.
    """

    provider = get_secret("LLM_PROVIDER") or "ollama"
    provider = provider.lower()

    if provider == "ollama":

        response = chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            stream=False
        )

        return response.message.content.strip()

    elif provider == "gemini":

        api_key = get_secret("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30000)
            )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
                max_output_tokens=2048
            )
        )

        if not response.text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        return response.text.strip()

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}"
        )
