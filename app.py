# app.py

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from agents.agent_manager import AgentManager
import traceback
import os
import json
import subprocess
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
CORS(app)

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'py', 'js', 'java', 'c', 'cpp', 'md'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Function to get available Ollama models
def get_available_models():
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        models.append(model_name)
            return models
        return []
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

# Auto-detect best available model - prioritize deepseek-coder for speed
available_models = get_available_models()
print(f"📋 Available Ollama models: {available_models}")

# Choose the fastest model for code generation
# Prioritize deepseek-coder (smaller/faster) over codellama (larger/slower)
preferred_models = ['deepseek-coder', 'phi', 'tinyllama', 'mistral', 'codellama', 'llama2']
selected_model = None

for model in preferred_models:
    for available in available_models:
        if model in available.lower():
            selected_model = available
            break
    if selected_model:
        break

if not selected_model and available_models:
    selected_model = available_models[0]  # Use first available model

print(f"✅ Selected model: {selected_model} (faster for code generation)")

# Initialize the agent manager with the detected model
try:
    if selected_model:
        agent_manager = AgentManager(model=selected_model)
    else:
        # Default to deepseek-coder
        agent_manager = AgentManager(model="deepseek-coder:latest")
    print("✅ AgentManager initialized successfully")
    print(f"✅ Available agents: {list(agent_manager.agents.keys())}")
except Exception as e:
    print(f"❌ Error initializing AgentManager: {e}")
    traceback.print_exc()
    agent_manager = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models', methods=['GET'])
def get_models():
    """Return available models to the frontend"""
    return jsonify({
        'available_models': available_models,
        'selected_model': selected_model
    })

@app.route('/api/generate', methods=['POST'])
def generate():
    """Non-streaming version for compatibility"""
    data = request.json
    task = data.get('task', '')
    
    if not task:
        return jsonify({'error': 'No task provided'}), 400
    
    if agent_manager is None:
        return jsonify({'error': 'AgentManager not initialized. Make sure Ollama is running and you have a model installed.'}), 500
    
    try:
        print(f"\n--- Processing task: {task[:50]}... ---")
        
        # Use the generate agent's sync method
        agent = agent_manager.agents.get("generate")
        if not agent:
            return jsonify({'error': 'Generate agent not found'}), 500
        
        # Start timing
        start_time = time.time()
        result = agent.run_sync(task)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Task completed in {elapsed_time:.2f} seconds")
        return jsonify({'result': result, 'time': elapsed_time})
            
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-file', methods=['POST'])
def analyze_file():
    """File analysis endpoint"""
    if agent_manager is None:
        return jsonify({'error': 'AgentManager not initialized'}), 500
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    question = request.form.get('question', 'Summarize this file in 2-3 sentences')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Save file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Read file content
            start_time = time.time()
            file_content = agent_manager._read_local_file(filepath)
            
            if file_content and not file_content.startswith("Error"):
                # Truncate very large files for speed
                content_length = len(file_content)
                if content_length > 3000:  # Reduced from 5000 for speed
                    file_content = file_content[:3000] + f"\n... [File truncated from {content_length} characters for performance]"
                
                # Create analysis prompt - make it more focused for speed
                prompt = f"""Quick analysis of this file:

Question: {question}

File content preview:
{file_content[:1500]}

Provide a concise answer (2-3 paragraphs max)."""

                agent = agent_manager.agents.get("generate")
                if not agent:
                    return jsonify({'error': 'Generate agent not found'}), 500
                
                result = agent.run_sync(prompt)
                elapsed_time = time.time() - start_time
                
                # Clean up
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                return jsonify({'result': result, 'time': elapsed_time})
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': file_content or 'Could not read file'}), 400
                
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"❌ Error analyzing file: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': f'File type not allowed. Allowed types: {ALLOWED_EXTENSIONS}'}), 400

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    # Check if Ollama is responsive
    ollama_status = "unknown"
    try:
        subprocess.run(['ollama', 'list'], capture_output=True, timeout=2)
        ollama_status = "running"
    except:
        ollama_status = "not responding"
    
    status = {
        'status': 'ok',
        'agent_manager': agent_manager is not None,
        'selected_model': selected_model,
        'available_models': available_models,
        'ollama_status': ollama_status
    }
    return jsonify(status)

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)