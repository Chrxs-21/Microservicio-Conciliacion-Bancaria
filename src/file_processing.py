"""
file_processing.py
==================
Responsabilidad unica: cargar, limpiar y normalizar los dos archivos CSV
(movimientos del banco y libro contable) antes de que la logica de
conciliacion los consuma.

Pasos que ocurren aqui:
  1. Lectura del CSV con pandas.
  2. Filtrado de registros que no participan en la conciliacion.
  3. Conversion de columnas de fecha a objetos datetime.
  4. Extraccion de los campos 'prefijo', 'tienda' y 'lote' a partir
     de la referencia.
  5. Marcado de registros sin prefijo para revision manual por Finanzas.
  6. Normalizacion de tipos (montos como float, tipos CREDIT/DEBIT uniformes).

Nada de logica de conciliacion vive aqui.
"""

import re
import pandas as pd

from config import (
    BANK_VALID_DESCRIPTIONS,
    BOOK_VALID_PROVIDER_PREFIX,
)


# ---------------------------------------------------------------------------
# Parser de referencia
# ---------------------------------------------------------------------------

def parse_reference(ref: str, source: str = 'banco') -> dict:
    """
    Descompone una referencia en prefijo, tienda y lote.

    El patron general es: [Prefijo][Tienda][Lote]
    - Prefijo : letras iniciales que identifican el medio de pago.
    - Tienda  : siempre 3 digitos numericos (en todos los prefijos).
    - Lote    : digitos restantes (longitud varia segun prefijo).

    Caso especial -- prefijo M (Monedero Patria):
      El libro contable inserta un digito '0' fijo en la posicion 4
      que el banco no tiene. El parametro 'source' permite manejar
      esta inconsistencia sin afectar el resto de los prefijos.

    Parametros
    ----------
    ref    : str
        Codigo de referencia. Ejemplo: 'D59900001', 'BD2040026'.
    source : str
        'banco' o 'libro'. Solo afecta el parsing del prefijo M.

    Retorna
    -------
    dict con claves: 'prefijo', 'tienda', 'lote'.
    Cada campo es None si la referencia no puede parsearse.

    Ejemplos
    --------
    >>> parse_reference('D59900001', 'banco')
    {'prefijo': 'D', 'tienda': '599', 'lote': '00001'}
    >>> parse_reference('M1560001', 'libro')
    {'prefijo': 'M', 'tienda': '156', 'lote': '001'}
    """
    if not isinstance(ref, str):
        return {'prefijo': None, 'tienda': None, 'lote': None}

    match = re.match(r'^([A-Za-z]+)', ref)
    if not match:
        return {'prefijo': None, 'tienda': None, 'lote': None}

    prefijo = match.group(1).upper()
    numeros = ref[len(prefijo):]

    if prefijo in ('D', 'C', 'BD', 'BC'):
        tienda = numeros[:3]
        lote   = numeros[3:]
    elif prefijo == 'M':
        tienda = numeros[:3]
        # El libro inserta un '0' fijo en posicion 4 que el banco no tiene.
        lote   = numeros[3:] if source == 'banco' else numeros[4:]
    else:
        return {'prefijo': prefijo, 'tienda': None, 'lote': None}

    return {'prefijo': prefijo, 'tienda': tienda, 'lote': lote}


# ---------------------------------------------------------------------------
# Filtros internos
# ---------------------------------------------------------------------------

def _filter_bank(df: pd.DataFrame) -> pd.DataFrame:
    """
    Conserva solo los movimientos del banco que son liquidaciones de
    medios de pago, identificados por el inicio de su columna 'Descripcion'.

    Los prefijos validos estan definidos en config.BANK_VALID_DESCRIPTIONS.
    Cualquier otro movimiento (transferencias, comisiones, etc.) se descarta
    porque no tiene contraparte en el libro contable.

    Por que startswith sobre una tupla:
        pandas .str.startswith() acepta una tupla de prefijos y aplica
        un OR logico entre ellos, lo que es mas eficiente que encadenar
        multiples filtros con | (OR).
    """
    mascara = df['Descripcion'].str.startswith(BANK_VALID_DESCRIPTIONS, na=False)
    return df[mascara].copy()


def _filter_book(df: pd.DataFrame) -> pd.DataFrame:
    """
    Conserva solo los registros del libro cuyo 'Proveedor' empiece
    con BOOK_VALID_PROVIDER_PREFIX ('VENTAS').

    Los prefijos descartados (VR, DJFR, FB, IP, AGGN) corresponden
    a ajustes manuales que no deben conciliarse automaticamente.
    """
    mascara = df['Proveedor'].str.startswith(BOOK_VALID_PROVIDER_PREFIX, na=False)
    return df[mascara].copy()


# ---------------------------------------------------------------------------
# Carga del banco
# ---------------------------------------------------------------------------

def load_bank(filepath: str) -> pd.DataFrame:
    """
    Carga el CSV de movimientos del banco, filtra y normaliza.

    Columnas del CSV original relevantes para la conciliacion:
      - Referencia      : codigo identificador del movimiento
      - Fecha Efectiva  : fecha en que ocurrio el movimiento
      - Descripcion     : texto descriptivo (usado para filtrar)
      - Tipo            : 'CREDIT' o 'DEBIT'
      - Monto           : monto del movimiento

    Columnas que agrega este modulo:
      - prefijo         : letras iniciales de la referencia
      - tienda          : 3 digitos de identificacion de tienda
      - lote            : digitos restantes de identificacion de lote
      - sin_prefijo     : True si la referencia no tiene prefijo alfabetico
      - estado          : estado inicial 'No Conciliado' para todos

    Parametros
    ----------
    filepath : str
        Ruta al archivo movimientos_banco.csv.

    Retorna
    -------
    pd.DataFrame con todos los registros del banco normalizados.
    Los registros sin prefijo se incluyen con sin_prefijo=True
    para visibilidad del area de Finanzas.
    """
    df = pd.read_csv(filepath, dtype=str)

    # Renombrar columna con tilde para evitar problemas de encoding
    df = df.rename(columns={'Descripción': 'Descripcion'})

    # Filtrar solo liquidaciones de medios de pago
    df = _filter_bank(df)

    # Convertir fechas a datetime
    # errors='coerce' convierte fechas invalidas a NaT en vez de lanzar error
    df['Fecha Efectiva'] = pd.to_datetime(df['Fecha Efectiva'], errors='coerce')
    df['Fecha Contable'] = pd.to_datetime(df['Fecha Contable'], errors='coerce')

    # Convertir monto a float
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce')

    # Normalizar tipo a mayusculas (CREDIT / DEBIT)
    df['Tipo'] = df['Tipo'].str.upper().str.strip()

    # Extraer prefijo, tienda y lote
    parsed = df['Referencia'].apply(lambda r: parse_reference(r, source='banco'))
    df['prefijo'] = parsed.apply(lambda x: x['prefijo'])
    df['tienda']  = parsed.apply(lambda x: x['tienda'])
    df['lote']    = parsed.apply(lambda x: x['lote'])

    # Marcar registros sin prefijo para revision manual por Finanzas.
    # Estos no participan en la conciliacion automatica pero si aparecen
    # en el reporte final con estado 'No Conciliado'.
    df['sin_prefijo'] = df['prefijo'].isna()

    # Estado inicial de todos los registros
    df['estado'] = 'No Conciliado'

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Carga del libro contable
# ---------------------------------------------------------------------------

def load_book(filepath: str) -> pd.DataFrame:
    """
    Carga el CSV del libro contable, filtra y normaliza.

    Columnas del CSV original relevantes para la conciliacion:
      - Numero de Transaccion : codigo identificador del registro
      - Fecha Contable        : fecha en que se contabilizo
      - Fecha de Transaccion  : fecha de la transaccion original
      - Proveedor             : texto descriptivo (usado para filtrar)
      - Tipo                  : 'Credit' o 'Debit'
      - Monto                 : monto de la transaccion

    Columnas que agrega este modulo:
      - prefijo   : letras iniciales del numero de transaccion
      - tienda    : 3 digitos de identificacion de tienda
      - lote      : digitos restantes de identificacion de lote
      - estado    : estado inicial 'No Conciliado' para todos

    Parametros
    ----------
    filepath : str
        Ruta al archivo libro_contable.csv.

    Retorna
    -------
    pd.DataFrame con los registros VENTAS del libro normalizados.
    """
    df = pd.read_csv(filepath, dtype=str)

    # Filtrar solo registros VENTAS
    df = _filter_book(df)

    # Convertir fechas a datetime
    df['Fecha Contable']       = pd.to_datetime(df['Fecha Contable'], errors='coerce')
    df['Fecha de Transaccion'] = pd.to_datetime(
        df['Fecha de Transacción'], errors='coerce'
    )

    # Convertir monto a float
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce')

    # Normalizar tipo a mayusculas (CREDIT / DEBIT)
    df['Tipo'] = df['Tipo'].str.upper().str.strip()

    # Extraer prefijo, tienda y lote
    parsed = df['Número de Transacción'].apply(
        lambda r: parse_reference(r, source='libro')
    )
    df['prefijo'] = parsed.apply(lambda x: x['prefijo'])
    df['tienda']  = parsed.apply(lambda x: x['tienda'])
    df['lote']    = parsed.apply(lambda x: x['lote'])

    # Estado inicial de todos los registros
    df['estado'] = 'No Conciliado'

    df = df.reset_index(drop=True)
    return df