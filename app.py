import os
import json
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Lista de archivos JSON que quieres combinar
JSON_FILES = [
    'qsk78_parameters.json',
    'Resumen_Rangos_Motor_QSK78_MCRS.json',
    'knowledge_qs.json'  # agrega más si tienes
]

def load_json_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

@app.route('/')
def index():
    return jsonify({
        'service': 'ada-diagnostico-bot-service',
        'endpoints': ['/manuales']
    })

@app.route('/manuales')
def manuales():
    combined = []
    for name in JSON_FILES:
        path = os.path.join(BASE_DIR, name)
        combined.extend(load_json_file(path))
    return jsonify(combined)

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
