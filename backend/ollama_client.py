import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def query_llm(prompt, model="codellama"):

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)

    if response.status_code == 200:
        return response.json()["response"]

    return "LLM Error"