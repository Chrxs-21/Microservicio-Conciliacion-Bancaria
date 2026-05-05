"""
app.py
======
API REST del microservicio de conciliación bancaria.

Endpoints:
  GET  /health        → Health check del servicio.
  POST /reconciliar   → Recibe los archivos (o usa los del disco) y
                        retorna el resultado de la conciliación en JSON.

Stack: Flask + pandas
Ejecutar localmente:
  python src/app.py
  (o con flask run si se configura FLASK_APP=src/app.py)
"""

from flask import Flask, request, jsonify

from file_processing import load_bank, load_book
from reconciliation import reconcile, DEFAULT_TOL_CONCILIADO, DEFAULT_TOL_POSIBLE, DEFAULT_DIAS_VENTANA

app = Flask(__name__)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """
    Health check del servicio.

    Respuesta exitosa (200):
        { "ok": true, "service": "reconciliation" }
    """
    pass  # TODO: Sprint 3


# ---------------------------------------------------------------------------
# POST /reconciliar
# ---------------------------------------------------------------------------

@app.route("/reconciliar", methods=["POST"])
def reconciliar():
    """
    Ejecuta la conciliación bancaria.

    Parámetros opcionales (query string o form data):
        tolerancia_conciliacion : float  (default: 1.00)
        tolerancia_posible      : float  (default: 5.00)
        dias_ventana            : int    (default: 3)

    Archivos opcionales (multipart/form-data):
        banco  : CSV de movimientos del banco
        libro  : CSV del libro contable

    Si no se envían archivos, se usan los de la carpeta datos/.

    Respuesta exitosa (200):
        {
            "ok": true,
            "resumen": { ... },
            "detalles": [ ... ]
        }

    Respuesta de error (400 / 500):
        { "ok": false, "error": "descripción del error" }
    """
    pass  # TODO: Sprint 3


# ---------------------------------------------------------------------------
# Manejo de errores globales
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "Endpoint no encontrado"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)