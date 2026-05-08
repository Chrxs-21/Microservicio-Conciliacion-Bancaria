"""
config.py
=========
Configuracion centralizada del microservicio de conciliacion bancaria.

Todas las constantes configurables del proyecto viven aqui.
Ningun otro modulo debe hardcodear rutas, tolerancias ni prefijos de filtrado.

Uso:
    from config import BANK_FILE, DEFAULT_TOL_CONCILIADO
"""

import os

# Ruta base del proyecto (dos niveles arriba de este archivo: src/ -> raiz/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Rutas de archivos
# ---------------------------------------------------------------------------

BANK_FILE  = os.path.join(BASE_DIR, 'datos', 'movimientos_banco.csv')
BOOK_FILE  = os.path.join(BASE_DIR, 'datos', 'libro_contable.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs') + os.sep

# ---------------------------------------------------------------------------
# Parametros de conciliacion (sobreescribibles desde la API)
# ---------------------------------------------------------------------------

DEFAULT_TOL_CONCILIADO = 1.00  # diferencia maxima de monto para -> Conciliado
DEFAULT_TOL_POSIBLE    = 5.00  # diferencia maxima de monto para -> Posible Conciliacion
DEFAULT_DIAS_VENTANA   = 3     # ventana maxima en dias entre fecha banco y libro

# ---------------------------------------------------------------------------
# Filtros del banco
# ---------------------------------------------------------------------------

# Solo los movimientos cuya 'Descripcion' EMPIECE con alguno de estos valores
# participan en la conciliacion. Cualquier otra descripcion se descarta.
BANK_VALID_DESCRIPTIONS = (
    'LIQ TARJETA',
    'LIQUIDACION T CREDITO',
    'LIQUIDACION TDC',
    'LIQUIDACION TDD',
    'LIQ MONEDERO',
)

# ---------------------------------------------------------------------------
# Filtros del libro contable
# ---------------------------------------------------------------------------

# Solo los registros cuyo 'Proveedor' EMPIECE con este valor participan.
# Prefijos descartados: VR, DJFR, FB, IP, AGGN (ajustes manuales).
BOOK_VALID_PROVIDER_PREFIX = 'VENTAS'