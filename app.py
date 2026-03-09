# app.py

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from agents.agent_manager import AgentManager
import traceback
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'py', 'js', 'java', 'c', 'cpp', 'md'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the agent manager
try:
    agent_manager = AgentManager(model="deepseek-coder")
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

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    task = data.get('task', '')
    
    if not task:
        return jsonify({'error': 'No task provided'}), 400
    
    if agent_manager is None:
        return jsonify({'error': 'AgentManager not initialized'}), 500
    
    try:
        print(f"\n--- Processing task: {task[:50]}... ---")
        
        # Use the generate agent
        result = agent_manager.handle_request("generate", task)
        
        print(f"✅ Task completed successfully")
        return jsonify({'result': result})
            
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-file', methods=['POST'])
def analyze_file():
    if agent_manager is None:
        return jsonify({'error': 'AgentManager not initialized'}), 500
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    question = request.form.get('question', 'Analyze this file and explain what it does')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Save file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Read file content using agent_manager's method
            file_content = agent_manager._read_local_file(filepath)
            
            if file_content and not file_content.startswith("Error"):
                # Create analysis prompt
                prompt = f"""Please analyze this file and answer the following question:
                
Question: {question}

File content:
{file_content}

Provide a detailed analysis."""
                
                # Use generate agent for analysis
                result = agent_manager.handle_request("generate", prompt)
                
                # Clean up - remove the temporary file
                os.remove(filepath)
                
                return jsonify({'result': result})
            else:
                os.remove(filepath)
                return jsonify({'error': file_content or 'Could not read file'}), 400
                
        except Exception as e:
            # Clean up if file exists
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"❌ Error analyzing file: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': f'File type not allowed. Allowed types: {ALLOWED_EXTENSIONS}'}), 400

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)