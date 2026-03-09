import ollama

class BaseAgent:
    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt

    def run(self, user_content: str):
        # We use ollama.chat to easily separate System vs User roles
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_content}
        ]
        
        stream = ollama.chat(model=self.model, messages=messages, stream=True)
        for chunk in stream:
            yield chunk['message']['content']

class CodeGeneratorAgent(BaseAgent):
    def __init__(self, model="deepseek-coder"):
        super().__init__(
            model=model,
            system_prompt="You are an expert Python developer. Output ONLY clean, functional code. No explanations, no markdown intro/outro, just code."
        )

class DebuggingAgent(BaseAgent):
    def __init__(self, model="deepseek-coder"):
        super().__init__(
            model=model,
            system_prompt="You are a Senior QA Engineer. Review the provided code for bugs, logic errors, or PEP8 violations. Return the FIXED version of the code only."
        )