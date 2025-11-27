from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Servicio activo: QSK78 Knowledge Base"

@app.route('/qsk78_parameters.json')
def serve_json():
    return send_from_directory(os.path.dirname(__file__), 'qsk78_parameters.json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
