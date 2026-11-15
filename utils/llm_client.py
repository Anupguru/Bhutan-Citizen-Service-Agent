
from ollama import chat

MODEL_NAME = "qwen3:1.7b"


def generate_llm_response(system_prompt, user_prompt):

    response = chat(
        model=MODEL_NAME,
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
