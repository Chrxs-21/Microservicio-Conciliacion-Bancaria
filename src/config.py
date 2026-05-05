"""
config.py
=========
Configuración centralizada del microservicio de conciliación bancaria.

Todas las constantes configurables del proyecto viven aquí.
Ningún otro módulo debe hardcodear rutas, tolerancias ni prefijos de filtrado.

Uso:
    from config import BANK_FILE, DEFAULT_TOL_CONCILIADO
"""

# ---------------------------------------------------------------------------
# Rutas de archivos
# ---------------------------------------------------------------------------

BANK_FILE  = "datos/movimientos_banco.csv"
BOOK_FILE  = "datos/libro_contable.csv"
OUTPUT_DIR = "outputs/"

# ---------------------------------------------------------------------------
# Parámetros de conciliación (sobreescribibles desde la API)
# ---------------------------------------------------------------------------

DEFAULT_TOL_CONCILIADO = 1.00  # diferencia máxima de monto para → Conciliado
DEFAULT_TOL_POSIBLE    = 5.00  # diferencia máxima de monto para → Posible Conciliación
DEFAULT_DIAS_VENTANA   = 3     # ventana máxima en días entre fecha banco y libro

# ---------------------------------------------------------------------------
# Filtros del banco
# ---------------------------------------------------------------------------

# Solo los movimientos cuya 'Descripción' EMPIECE con alguno de estos valores
# participan en la conciliación. Cualquier otra descripción se descarta.
BANK_VALID_DESCRIPTIONS = (
    "LIQ TARJETA",
    "LIQUIDACION T CREDITO",
    "LIQUIDACION TDC",
    "LIQUIDACION TDD",
    "LIQ MONEDERO",
)

# ---------------------------------------------------------------------------
# Filtros del libro contable
# ---------------------------------------------------------------------------

# Solo los registros cuyo 'Proveedor' EMPIECE con este valor participan.
# Prefijos descartados: VR, DJFR, FB, IP, AGGN (ajustes manuales).
BOOK_VALID_PROVIDER_PREFIX = "VENTAS"