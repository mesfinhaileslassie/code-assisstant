# tests/test_code_generator.py

from agents.code_generator import CodeGeneratorAgent

def test_code_generation():
    agent = CodeGeneratorAgent(model="deepseek-coder")
    task = "Create a Python function to compute Fibonacci numbers"
    print("=== Task ===")
    print(task)
    print("\n=== AI Generated Code ===")
    print(agent.run(task))

if __name__ == "__main__":
    test_code_generation()