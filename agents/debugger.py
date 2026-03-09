# agents/debugger.py
import ollama
class DebuggingAgent:
    def __init__(self, model="deepseek-coder"):
        self.model = model

    def run(self, code_to_check: str):
        prompt = f"Identify any potential bugs or PEP8 violations in this code. Output ONLY the fixed code:\n\n{code_to_check}"
        
        stream = ollama.generate(model=self.model, prompt=prompt, stream=True)
        for chunk in stream:
            yield chunk['response']