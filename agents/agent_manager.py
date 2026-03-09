# agents/agent_manager.py

import ollama
import os
import fitz  
from agents.code_generator import CodeGeneratorAgent, DebuggingAgent

class AgentManager:
    def __init__(self, model="deepseek-coder"):
        self.model = model
        self.memory = [
            {"role": "system", "content": "You are a professional AI Coding Assistant. When the user provides file content, analyze it carefully."}
        ]
        
        # Initialize the specialized agents
        self.agents = {
            "generate": CodeGeneratorAgent(model),
            "debug": DebuggingAgent(model),
        }

    def _read_local_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                return None

            # Check if it's a PDF
            if file_path.lower().endswith(".pdf"):
                text = ""
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text += page.get_text()
                return text if text.strip() else "The PDF appears to be empty or contains only images."

            # Otherwise, treat as standard text/code       
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            return "Error: This file isn't UTF-8. It might be a binary or image file."
        except Exception as e:
            return f"Error reading file: {e}"

    def handle_request(self, task_type: str, content: str) -> str:
        """
        Route the request to the correct agent.
        For the web interface, we need to collect the stream into a single string.
        """
        agent = self.agents.get(task_type)
        if not agent:
            return f"Error: Unknown task type '{task_type}'."
        
        # Run the agent and collect all chunks into a single string
        result = ""
        for chunk in agent.run(content):
            result += chunk
        
        return result

    def chat(self, user_input: str):
        # --- NEW: File Detection Logic ---
        # If you type: "read path/to/file.py", it loads it into context
        if user_input.lower().startswith("read "):
            file_path = user_input[5:].strip()
            content = self._read_local_file(file_path)     

            if content:
                user_input = f"I am providing the contents of {file_path}. Please acknowledge and wait for my instructions.\n\nCODE:\n{content}"
                print(f"📖 Loaded {file_path} into memory...")
            else:
                yield f"Error: Could not read file {file_path}"
                return

        # Add to memory
        self.memory.append({"role": "user", "content": user_input})

        # Get response from Ollama
        stream = ollama.chat(model=self.model, messages=self.memory, stream=True)
        
        response_chunks = []
        for chunk in stream:
            content = chunk['message']['content']
            response_chunks.append(content)
            yield content
        
        # Add the full response to memory
        full_response = "".join(response_chunks)
        self.memory.append({"role": "assistant", "content": full_response})