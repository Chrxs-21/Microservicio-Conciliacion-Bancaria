"""
app.py
======
API REST del microservicio de conciliacion bancaria.

Endpoints:
  GET  /health        -> Health check del servicio.
  POST /reconciliar   -> Ejecuta la conciliacion y retorna JSON con
                         resumen y detalles de todos los registros.

Parametros opcionales de POST /reconciliar (query string o form data):
  tolerancia_conciliacion : float  (default: 1.00)
  tolerancia_posible      : float  (default: 5.00)
  dias_ventana            : int    (default: 3)

Archivos opcionales (multipart/form-data):
  banco : CSV de movimientos del banco
  libro : CSV del libro contable
  Si no se envian, se usan los archivos de la carpeta datos/.

Ejecutar localmente:
  python src/app.py
  El servidor queda disponible en http://localhost:5000
"""

import os
import tempfile

from flask import Flask, request, jsonify

from file_processing import load_bank, load_book
from reconciliation import reconcile, generate_report
from config import (
    BANK_FILE,
    BOOK_FILE,
    DEFAULT_TOL_CONCILIADO,
    DEFAULT_TOL_POSIBLE,
    DEFAULT_DIAS_VENTANA,
)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    """
    Health check del servicio.

    Permite verificar que la API esta corriendo correctamente.
    Util para monitoreo y para confirmar que el servidor levanto bien.

    Respuesta exitosa (200):
        { "ok": true, "service": "reconciliation" }
    """
    return jsonify({'ok': True, 'service': 'reconciliation'}), 200


# ---------------------------------------------------------------------------
# POST /reconciliar
# ---------------------------------------------------------------------------

@app.route('/reconciliar', methods=['POST'])
def reconciliar():
    """
    Ejecuta la conciliacion bancaria completa.

    Parametros opcionales (query string):
        tolerancia_conciliacion : float  (default: 1.00)
        tolerancia_posible      : float  (default: 5.00)
        dias_ventana            : int    (default: 3)

    Archivos opcionales (multipart/form-data):
        banco : CSV de movimientos del banco
        libro : CSV del libro contable
        Si no se envian, se usan los de la carpeta datos/.

    Respuesta exitosa (200):
        {
            "ok": true,
            "resumen": { ... },
            "detalles": [ ... ]
        }

    Respuesta de error (400):
        { "ok": false, "error": "descripcion del error" }

    Respuesta de error (500):
        { "ok": false, "error": "descripcion del error" }
    """
    # -- Leer y validar parametros --
    try:
        tol_conciliado = float(
            request.args.get('tolerancia_conciliacion', DEFAULT_TOL_CONCILIADO)
        )
        tol_posible = float(
            request.args.get('tolerancia_posible', DEFAULT_TOL_POSIBLE)
        )
        dias_ventana = int(
            request.args.get('dias_ventana', DEFAULT_DIAS_VENTANA)
        )
    except ValueError:
        return jsonify({
            'ok'   : False,
            'error': 'Parametros invalidos. tolerancia_conciliacion y '
                     'tolerancia_posible deben ser numeros. '
                     'dias_ventana debe ser un entero.'
        }), 400

    if tol_conciliado < 0 or tol_posible < 0 or dias_ventana < 0:
        return jsonify({
            'ok'   : False,
            'error': 'Los parametros no pueden ser negativos.'
        }), 400

    if tol_conciliado > tol_posible:
        return jsonify({
            'ok'   : False,
            'error': 'tolerancia_conciliacion no puede ser mayor que tolerancia_posible.'
        }), 400

    # -- Cargar archivos --
    # Si el usuario envia archivos por multipart/form-data los usamos.
    # Si no, usamos los archivos por defecto de la carpeta datos/.
    try:
        archivo_banco = request.files.get('banco')
        archivo_libro = request.files.get('libro')

        tmp_files = []

        if archivo_banco:
            tmp_banco = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv', mode='wb'
            )
            archivo_banco.save(tmp_banco.name)
            tmp_banco.close()
            path_banco = tmp_banco.name
            tmp_files.append(path_banco)
        else:
            path_banco = BANK_FILE

        if archivo_libro:
            tmp_libro = tempfile.NamedTemporaryFile(
                delete=False, suffix='.csv', mode='wb'
            )
            archivo_libro.save(tmp_libro.name)
            tmp_libro.close()
            path_libro = tmp_libro.name
            tmp_files.append(path_libro)
        else:
            path_libro = BOOK_FILE

        df_banco = load_bank(path_banco)
        df_libro = load_book(path_libro)

    except FileNotFoundError as e:
        return jsonify({
            'ok'   : False,
            'error': f'Archivo no encontrado: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'ok'   : False,
            'error': f'Error al cargar los archivos: {str(e)}'
        }), 500
    finally:
        # Limpiar archivos temporales si se subieron archivos
        for tmp in tmp_files:
            if os.path.exists(tmp):
                os.remove(tmp)

    # -- Ejecutar conciliacion --
    try:
        resultado = reconcile(
            df_banco,
            df_libro,
            tol_conciliado=tol_conciliado,
            tol_posible=tol_posible,
            dias_ventana=dias_ventana,
        )
    except Exception as e:
        return jsonify({
            'ok'   : False,
            'error': f'Error durante la conciliacion: {str(e)}'
        }), 500

    # -- Generar reporte Excel (Criterio 5 bonus) --
    # Usamos los DataFrames actualizados que retorna reconcile(),
    # no los originales, ya que reconcile() trabaja sobre copias.
    try:
        generate_report(resultado['df_banco'], resultado['df_libro'])
    except Exception:
        # El reporte es bonus -- si falla no interrumpe la respuesta principal
        pass

    return jsonify({
        'ok'      : True,
        'resumen' : resultado['resumen'],
        'detalles': resultado['detalles'],
    }), 200


# ---------------------------------------------------------------------------
# Manejo de errores globales
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({'ok': False, 'error': 'Endpoint no encontrado'}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'ok': False, 'error': 'Metodo HTTP no permitido'}), 405


@app.errorhandler(500)
def server_error(e):
    return jsonify({'ok': False, 'error': 'Error interno del servidor'}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)