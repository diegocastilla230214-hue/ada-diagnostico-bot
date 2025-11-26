#!/usr/bin/env python3
import json, re
from http.server import HTTPServer, BaseHTTPRequestHandler

with open("knowledge_qsk78.json", "r", encoding="utf-8") as f:
    data = json.load(f)
kb = data["knowledge"]

# Build normalized lookup

def normalize(s):
    return re.sub(r"\s+", " ", s.strip().lower())

norm_kb = {normalize(k): v for k, v in kb.items()}

synonyms = data.get("synonyms", {})
norm_syn = {normalize(k): v for k, v in synonyms.items()}

keyword_map = [
    ("refrigerante", "Coolant Temperature"),
    ("coolant", "Coolant Temperature"),
    ("compresor turbo", "Engine Turbocharger 1 Compressor Intake Temperature"),
    ("carter", "Crankcase Pressure"),
    ("filtro aire", "Engine Air Filter 1-6 Differential Pressure"),
    ("entrega combustible", "Fuel Delivery Pressure"),
    ("inyector", "Injector Metering"),
    ("filtro combustible", "Engine Fuel Filter (Suction Side) Differential Pressure (Advanced Resolution dp5)"),
    ("aceite motor", "Engine Oil Temperature"),
    ("diferencial aceite", "Oil Differential Pressure"),
    ("rifle oil", "Rifle Oil Pressure"),
    ("bomba de combustible aceite", "Fuel Pump Oil Pressure"),
]


def find_block(question):
    q = normalize(question)
    # direct code
    for code in kb.keys():
        if normalize(code) in q:
            return kb[code]
    # synonyms
    for syn, code in norm_syn.items():
        if syn in q and code in kb:
            return kb[code]
    # keywords
    for kw, code in keyword_map:
        if kw in q and code in kb:
            return kb[code]
    return None


def fmt_range(r):
    if not r:
        return None
    return f"{r.get('label','')}: {r.get('value','')}"


def compose_answer(question, blk):
    ranges = blk.get("ranges", {})
    q = question.lower()
    lines = [
        f"Parámetro: {blk['code']} ({blk.get('unit','')})",
        f"Descripción: {blk.get('description','')}"
    ]
    if 'normal' in q:
        lines.append(f"Rango normal: {fmt_range(ranges.get('verde'))}")
    if 'observado' in q or 'amarillo' in q:
        lines.append(f"Rango observado: {fmt_range(ranges.get('amarillo'))}")
    if 'critico' in q or 'crítico' in q or 'rojo' in q:
        lines.append(f"Rango crítico: {fmt_range(ranges.get('rojo'))}")
    if len(lines) <= 2:
        lines.extend([
            f"Normal: {fmt_range(ranges.get('verde'))}",
            f"Observado: {fmt_range(ranges.get('amarillo'))}",
            f"Crítico: {fmt_range(ranges.get('rojo'))}",
        ])
    return "
".join([l for l in lines if l])


n_queries = 0

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

    def do_POST(self):
        global n_queries
        if self.path != "/query":
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "not_found"}).encode('utf-8'))
            return
        length = int(self.headers.get('Content-Length', '0'))
        data = self.rfile.read(length)
        try:
            payload = json.loads(data.decode('utf-8'))
        except Exception:
            payload = {}
        question = str(payload.get("question", "")).strip()
        blk = find_block(question)
        if not blk:
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "answer": "No encontré un parámetro relacionado. Intenta mencionar el nombre (p.ej., 'Temperatura del refrigerante', 'Injector Metering', 'EGT').",
                "matched_parameter": None
            }, ensure_ascii=False).encode('utf-8'))
            return
        answer = compose_answer(question, blk)
        n_queries += 1
        self._set_headers(200)
        self.wfile.write(json.dumps({
            "answer": answer,
            "matched_parameter": blk['code'],
            "queries_served": n_queries
        }, ensure_ascii=False).encode('utf-8'))


def run(host='0.0.0.0', port=8000):
    httpd = HTTPServer((host, port), Handler)
    print(f"KB server running on http://{host}:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
