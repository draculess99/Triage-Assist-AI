from flask import Flask, request, jsonify
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.agents.triage_system import evaluate_patient
import json

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
LOG_FILE = os.path.join(DATA_DIR, 'transactions.log')
MEMORY_FILE = os.path.join(DATA_DIR, 'memory.json')
METRICS_FILE = os.path.join(DATA_DIR, 'metrics.json')

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    session_id = data.get('session_id', 'default_session')
    notes = data.get('notes', '')
    engine_type = data.get('engine_type', 'Local Expert System (0 Tokens)')
    vitals = data.get('vitals', {})
    model_name = data.get('model_name', 'XGBoost')
    llm_model_name = data.get('llm_model_name', 'gemini-1.5-flash')
    dataset_name = data.get('dataset_name', 'UCI Cleveland Original')
    
    def generate():
        for chunk in evaluate_patient(session_id, notes, engine_type, vitals, model_name, llm_model_name, dataset_name):
            yield chunk
            
    return app.response_class(generate(), mimetype='application/x-ndjson')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    logs = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    return jsonify(logs)

@app.route('/api/memory', methods=['GET'])
def get_memory():
    if not os.path.exists(MEMORY_FILE):
        return jsonify({})
    with open(MEMORY_FILE, 'r') as f:
        return jsonify(json.load(f))

@app.route('/api/train', methods=['POST'])
def train():
    data = request.json
    dataset_name = data.get('dataset_name', 'UCI Cleveland Original')
    from backend.forecaster import train_models
    try:
        train_models(dataset_name)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/xai', methods=['POST'])
def get_xai():
    data = request.json
    model_name = data.get('model_name', 'XGBoost')
    dataset_name = data.get('dataset_name', 'UCI Cleveland Original')
    from backend.forecaster import get_xai_data
    try:
        xai_data = get_xai_data(model_name, dataset_name)
        return jsonify(xai_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    from backend.forecaster import METRICS_PATH, DATASET_FILE
    current_dataset = "UCI Cleveland Original"
    import os
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, 'r') as f:
            current_dataset = f.read().strip()
            
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, 'r') as f:
            return jsonify({
                "metrics": json.load(f),
                "dataset": current_dataset
            })
    return jsonify({"metrics": {}, "dataset": current_dataset})

if __name__ == '__main__':
    app.run(port=5000)
