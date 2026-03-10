# agents/code_generator.py

import ollama
import time

class BaseAgent:
    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt

    def run(self, user_content: str):
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_content}      
        ]

        try:
            stream = ollama.chat(model=self.model, messages=messages, stream=True)
            for chunk in stream:
                yield chunk['message']['content']
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def run_sync(self, user_content: str) -> str:
        """Non-streaming version for when we need the full response at once"""
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_content}      
        ]

        try:
            # Add timeout to prevent hanging
            response = ollama.chat(model=self.model, messages=messages, stream=False)
            return response['message']['content']
        except Exception as e:
            return f"Error generating response: {str(e)}"

class CodeGeneratorAgent(BaseAgent):
    def __init__(self, model="deepseek-coder:latest"):
        super().__init__(
            model=model,
            system_prompt="You are an expert developer. Output ONLY clean, functional code. No explanations, no markdown, just the code."
        )

class DebuggingAgent(BaseAgent):
    def __init__(self, model="deepseek-coder:latest"):
        super().__init__(
            model=model,
            system_prompt="You are a Senior QA Engineer. Review the code for bugs and return the FIXED version only."        
        )