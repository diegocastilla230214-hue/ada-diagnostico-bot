import json, re, os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Cargar la base de conocimiento (JSON generado desde tu documento QSK78)
with open("knowledge_qsk78.json", "r", encoding="utf-8") as f:
    data = json.load(f)

kb = data.get("knowledge", {})
synonyms = data.get("synonyms", {})

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

# Normalizar sinónimos para búsqueda
norm_syn = {normalize(k): v for k, v in synonyms.items()}

# Mapa de palabras clave por si la pregunta no menciona el código exacto
keyword_map = [
    ("refrigerante", "Coolant Temperature"),
    ("coolant", "Coolant Temperature"),
    ("compresor turbo", "Engine Turbocharger 1 Compressor Intake Temperature"),
    ("carter", "Crankcase Pressure"),
    ("cárter", "Crankcase Pressure"),
    ("filtro aire", "Engine Air Filter 1-6 Differential Pressure"),
    ("entrega combustible", "Fuel Delivery Pressure"),
    ("inyector", "Injector Metering"),
    ("filtro combustible", "Engine Fuel Filter (Suction Side) Differential Pressure (Advanced Resolution dp5)"),
    ("aceite motor", "Engine Oil Temperature"),
    ("diferencial aceite", "Oil Differential Pressure"),
    ("rifle oil", "Rifle Oil Pressure"),
    ("bomba de combustible aceite", "Fuel Pump Oil Pressure"),
]

def find_block(question: str):
    q = normalize(question)

    # 1) Buscar por mención directa del código del parámetro en el texto de la pregunta
    for code, blk in kb.items():
        if normalize(code) in q:
            return blk

    # 2) Buscar por sinónimos
    for syn, code in norm_syn.items():
        if syn in q and code in kb:
            return kb[code]

    # 3) Buscar por palabras clave
    for kw, code in keyword_map:
        if kw in q and code in kb:
            return kb[code]

    return None

def fmt_range(r: dict | None) -> str | None:
    if not r:
        return None
    # Se asume que el JSON tiene campos 'label' y 'value'
    label = r.get("label", "")
    value = r.get("value", "")
    # Devuelve "Etiqueta: valor"
    return f"{label}: {value}".strip(": ").strip()

def compose_answer(question: str, blk: dict) -> str:
    """
    Construye la respuesta en texto con:
      - Parámetro + unidad
      - Descripción
      - Rangos Normal / Observado / Crítico (según lo pida la pregunta; si no, todos)
    """
    ranges = blk.get("ranges", {})
    q = question.lower()

    lines: list[str] = []
    # Cabecera
    code = blk.get("code", "")
    unit = blk.get("unit", "")
    desc = blk.get("description", "")

    # Línea de parámetro y unidad
    if unit:
        lines.append(f"Parámetro: {code} ({unit})")
    else:
        lines.append(f"Parámetro: {code}")

    # Descripción
    if desc:
        lines.append(f"Descripción: {desc}")

    # Rangos solicitados explícitamente
    added_specific = False
    if "normal" in q:
        val = fmt_range(ranges.get("verde"))
        if val:
            lines.append(f"Rango normal: {val}")
            added_specific = True
    if "observado" in q or "amarillo" in q:
        val = fmt_range(ranges.get("amarillo"))
        if val:
            lines.append(f"Rango observado: {val}")
            added_specific = True
    if "critico" in q or "crítico" in q or "rojo" in q:
        val = fmt_range(ranges.get("rojo"))
        if val:
            lines.append(f"Rango crítico: {val}")
            added_specific = True

    # Si no pidió rango específico, devolvemos todos los disponibles
    if not added_specific:
        v_normal = fmt_range(ranges.get("verde"))
        v_obs = fmt_range(ranges.get("amarillo"))
        v_crit = fmt_range(ranges.get("rojo"))

        if v_normal:
            lines.append(f"Normal: {v_normal}")
        if v_obs:
            lines.append(f"Observado: {v_obs}")
        if v_crit:
            lines.append(f"Crítico: {v_crit}")

    # Unir respetando que ninguna línea quede vacía (evita errores de strings)
    return "\n".join([l for l in lines if l])

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

    def do_POST(self):
        if self.path != "/query":
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "not_found"}).encode('utf-8'))
            return

        # Leer payload
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = 0

        data_bytes = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(data_bytes.decode('utf-8'))
        except Exception:
            payload = {}

        question = str(payload.get("question", "")).strip()

        # Buscar bloque
        blk = find_block(question)
        if not blk:
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "answer": "No encontré un parámetro relacionado. Intenta mencionar el nombre (p.ej., 'Temperatura del refrigerante', 'Injector Metering', 'EGT').",
                "matched_parameter": None
            }, ensure_ascii=False).encode('utf-8'))
            return

        answer = compose_answer(question, blk)

        self._set_headers(200)
        self.wfile.write(json.dumps({
            "answer": answer,
            "matched_parameter": blk.get('code', '')
        }, ensure_ascii=False).encode('utf-8'))

def run():
    # Render asigna PORT por variable de entorno
    port = int(os.environ.get("PORT", 8000))
    httpd = HTTPServer(('0.0.0.0', port), Handler)
    print(f"KB server running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
