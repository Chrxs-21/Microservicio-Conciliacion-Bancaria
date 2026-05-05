"""
file_processing.py
==================
Responsabilidad única: cargar, limpiar y normalizar los dos archivos CSV
(movimientos del banco y libro contable) antes de que la lógica de
conciliación los consuma.

Pasos que ocurren aquí:
  1. Lectura del CSV con pandas.
  2. Filtrado de registros que no participan en la conciliación.
  3. Conversión de columnas de fecha a objetos datetime.
  4. Extracción de los campos 'tienda' y 'lote' a partir de la referencia.
  5. Normalización de tipos (montos como float, tipos CREDIT/DEBIT uniformes).

Nada de lógica de conciliación vive aquí.
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Constantes de filtrado
# ---------------------------------------------------------------------------

# Prefijos válidos en la columna 'Descripción' del banco.
# Solo los movimientos cuya descripción EMPIECE con alguno de estos valores
# participan en la conciliación.
BANK_VALID_DESCRIPTIONS = (
    "LIQ TARJETA",
    "LIQUIDACION T CREDITO",
    "LIQUIDACION TDC",
    "LIQUIDACION TDD",
    "LIQ MONEDERO",
)

# Prefijo válido en la columna 'Proveedor' del libro contable.
BOOK_VALID_PROVIDER_PREFIX = "VENTAS"


# ---------------------------------------------------------------------------
# Carga y limpieza del banco
# ---------------------------------------------------------------------------

def load_bank(filepath: str) -> pd.DataFrame:
    """
    Carga el CSV de movimientos del banco, filtra y normaliza.

    Parámetros
    ----------
    filepath : str
        Ruta al archivo movimientos_banco.csv.

    Retorna
    -------
    pd.DataFrame
        DataFrame limpio con columnas adicionales: 'prefijo', 'tienda', 'lote'.
    """
    pass  # TODO: Sprint 1


def _filter_bank(df: pd.DataFrame) -> pd.DataFrame:
    """
    Descarta filas cuya 'Descripción' no empiece con BANK_VALID_DESCRIPTIONS.
    """
    pass  # TODO: Sprint 1


# ---------------------------------------------------------------------------
# Carga y limpieza del libro contable
# ---------------------------------------------------------------------------

def load_book(filepath: str) -> pd.DataFrame:
    """
    Carga el CSV del libro contable, filtra y normaliza.

    Parámetros
    ----------
    filepath : str
        Ruta al archivo libro_contable.csv.

    Retorna
    -------
    pd.DataFrame
        DataFrame limpio con columnas adicionales: 'prefijo', 'tienda', 'lote'.
    """
    pass  # TODO: Sprint 1


def _filter_book(df: pd.DataFrame) -> pd.DataFrame:
    """
    Descarta filas cuyo 'Proveedor' no empiece con BOOK_VALID_PROVIDER_PREFIX.
    """
    pass  # TODO: Sprint 1


# ---------------------------------------------------------------------------
# Parseo de la clave Tienda + Lote
# ---------------------------------------------------------------------------

def parse_reference(ref: str) -> dict:
    """
    Descompone una referencia (ej. 'D59900001') en sus tres componentes.

    Parámetros
    ----------
    ref : str
        Código de referencia del banco o del libro.

    Retorna
    -------
    dict con claves: 'prefijo', 'tienda', 'lote'
        Retorna {'prefijo': None, 'tienda': None, 'lote': None} si no
        se puede parsear.

    Ejemplos
    --------
    >>> parse_reference('D59900001')
    {'prefijo': 'D', 'tienda': '599', 'lote': '00001'}
    >>> parse_reference('BD2040026')
    {'prefijo': 'BD', 'tienda': '204', 'lote': '0026'}
    """
    pass  # TODO: Sprint 1 (definir tras Issue #1 de exploración)