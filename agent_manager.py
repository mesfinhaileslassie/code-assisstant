import ollama
import os
import fitz  
import os
class AgentManager:
    def __init__(self, model="deepseek-coder"):
        self.model = model
        self.memory = [
            {"role": "system", "content": "You are a professional AI Coding Assistant. When the user provides file content, analyze it carefully."}
        ]

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
                yield f"❌ Could not find file: {file_path}"
                return

        self.memory.append({"role": "user", "content": user_input})

        try:
            stream = ollama.chat(model=self.model, messages=self.memory, stream=True)
            full_response = ""
            for chunk in stream:
                content = chunk['message']['content']
                full_response += content
                yield content
            self.memory.append({"role": "assistant", "content": full_response})
        except Exception as e:
            yield f"\n[Error]: {e}"

if __name__ == "__main__":
    manager = AgentManager()
    print("--- 🤖 File-Aware AI Assistant ---")
    print("Commands: 'read [filename]' | 'clear' | 'exit'")
    
    while True:
        query = input("\n> You: ").strip()
        if query.lower() == "exit": break
        
        for chunk in manager.chat(query):
            print(chunk, end="", flush=True)
        print("\n" + "-"*30)