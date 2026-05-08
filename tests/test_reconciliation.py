"""
test_reconciliation.py
======================
Pruebas unitarias para la logica de conciliacion.

Filosofia:
  - Cada test es AISLADO: usa DataFrames sinteticos pequenos, no los CSVs reales.
  - Cada test verifica UN comportamiento especifico.
  - Los tests no dependen entre si ni de estado externo.

Casos cubiertos:
  1. Conciliacion exacta 1 a 1                    -> Conciliado
  2. Monto fuera de toda tolerancia               -> No Conciliado
  3. Diferencia en rango posible                  -> Posible Conciliacion
  4. Misma referencia pero distinta tienda        -> No Conciliado
  5. Fechas fuera de la ventana permitida         -> No Conciliado
  6. Conciliacion N a 1                           -> Conciliado
  7. Diferencia dentro de tol_conciliado          -> Conciliado

Para ejecutar:
  pytest tests/ -v
"""

import sys
import os
import pytest
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from reconciliation import reconcile


# ---------------------------------------------------------------------------
# Helpers para construir DataFrames sinteticos
# ---------------------------------------------------------------------------

def make_bank(tienda: str, lote: str, monto: float, fecha: str) -> pd.DataFrame:
    """
    Construye un DataFrame de banco con un solo registro.

    Incluye todas las columnas que reconcile() espera encontrar,
    con valores neutrales para los campos que no afectan la logica
    de conciliacion (Descripcion, Tipo, etc.).
    """
    return pd.DataFrame([{
        'Referencia'    : f'D{tienda}{lote}',
        'prefijo'       : 'D',
        'tienda'        : tienda,
        'lote'          : lote,
        'Monto'         : monto,
        'Fecha Efectiva': pd.to_datetime(fecha),
        'Fecha Contable': pd.to_datetime(fecha),
        'Tipo'          : 'CREDIT',
        'Descripcion'   : 'LIQ TARJETA DEBITO',
        'sin_prefijo'   : False,
        'estado'        : 'No Conciliado',
    }])


def make_book(tienda: str, lote: str, monto: float, fecha: str) -> pd.DataFrame:
    """
    Construye un DataFrame de libro con un solo registro.
    """
    return pd.DataFrame([{
        'Número de Transacción': f'D{tienda}{lote}',
        'prefijo'              : 'D',
        'tienda'               : tienda,
        'lote'                 : lote,
        'Monto'                : monto,
        'Fecha Contable'       : pd.to_datetime(fecha),
        'Fecha de Transaccion' : pd.to_datetime(fecha),
        'Tipo'                 : 'CREDIT',
        'Proveedor'            : 'VENTAS TEST',
        'estado'               : 'No Conciliado',
    }])


def get_estado(resultado: dict, origen: str) -> str:
    """Extrae el estado del primer registro de un origen dado."""
    for d in resultado['detalles']:
        if d['origen'] == origen:
            return d['estado']
    return None


# ---------------------------------------------------------------------------
# Test 1 -- Conciliacion exacta 1 a 1
# ---------------------------------------------------------------------------

def test_conciliacion_exacta_1_a_1():
    """
    Dos registros con misma tienda, mismo lote, mismo monto y fecha
    dentro de la ventana deben quedar 'Conciliado'.
    """
    bank = make_bank(tienda='100', lote='00001', monto=1000.00, fecha='2026-04-01')
    book = make_book(tienda='100', lote='00001', monto=1000.00, fecha='2026-04-02')

    resultado = reconcile(bank, book)

    assert get_estado(resultado, 'banco') == 'Conciliado'
    assert get_estado(resultado, 'libro') == 'Conciliado'
    assert resultado['resumen']['conciliados_banco'] == 1
    assert resultado['resumen']['conciliados_libro'] == 1


# ---------------------------------------------------------------------------
# Test 2 -- Monto fuera de toda tolerancia
# ---------------------------------------------------------------------------

def test_monto_fuera_de_tolerancia():
    """
    Dos registros con misma tienda y lote pero diferencia de monto > 5.00
    deben quedar 'No Conciliado'.
    """
    bank = make_bank(tienda='100', lote='00001', monto=1000.00, fecha='2026-04-01')
    book = make_book(tienda='100', lote='00001', monto=1010.00, fecha='2026-04-01')

    resultado = reconcile(bank, book)

    assert get_estado(resultado, 'banco') == 'No Conciliado'
    assert get_estado(resultado, 'libro') == 'No Conciliado'
    assert resultado['resumen']['no_conciliados_banco'] == 1
    assert resultado['resumen']['no_conciliados_libro'] == 1


# ---------------------------------------------------------------------------
# Test 3 -- Posible Conciliacion
# ---------------------------------------------------------------------------

def test_posible_conciliacion():
    """
    Diferencia de monto entre 1.00 y 5.00 bolivares debe producir
    estado 'Posible Conciliacion' en ambos registros.
    """
    bank = make_bank(tienda='200', lote='00002', monto=1000.00, fecha='2026-04-01')
    book = make_book(tienda='200', lote='00002', monto=1003.00, fecha='2026-04-01')

    resultado = reconcile(bank, book)

    assert get_estado(resultado, 'banco') == 'Posible Conciliacion'
    assert get_estado(resultado, 'libro') == 'Posible Conciliacion'
    assert resultado['resumen']['posibles_banco'] == 1
    assert resultado['resumen']['posibles_libro'] == 1


# ---------------------------------------------------------------------------
# Test 4 -- Distinta tienda no concilia
# ---------------------------------------------------------------------------

def test_distinta_tienda_no_concilia():
    """
    Registros con el mismo lote pero distinta tienda NO deben conciliar,
    aunque el monto y la fecha sean identicos.
    La llave de conciliacion es (tienda, lote), no solo el lote.
    """
    bank = make_bank(tienda='111', lote='00001', monto=500.00, fecha='2026-04-01')
    book = make_book(tienda='222', lote='00001', monto=500.00, fecha='2026-04-01')

    resultado = reconcile(bank, book)

    assert get_estado(resultado, 'banco') == 'No Conciliado'
    assert get_estado(resultado, 'libro') == 'No Conciliado'


# ---------------------------------------------------------------------------
# Test 5 -- Fecha fuera de ventana
# ---------------------------------------------------------------------------

def test_fecha_fuera_de_ventana():
    """
    Registros con misma tienda, mismo lote y mismo monto pero fechas
    separadas por mas de dias_ventana no deben conciliar.
    """
    bank = make_bank(tienda='300', lote='00003', monto=750.00, fecha='2026-04-01')
    book = make_book(tienda='300', lote='00003', monto=760.00, fecha='2026-04-10')

    # Ventana de 3 dias, diferencia de 9 dias -> no debe conciliar por fecha.
    # El monto difiere en 10.00 (fuera de tol_posible=5.00) para evitar que
    # el Criterio 3 los concilie por suma de grupo.
    resultado = reconcile(bank, book, dias_ventana=3)

    assert get_estado(resultado, 'banco') == 'No Conciliado'
    assert get_estado(resultado, 'libro') == 'No Conciliado'


# ---------------------------------------------------------------------------
# Test 6 -- Conciliacion N a 1
# ---------------------------------------------------------------------------

def test_conciliacion_n_a_1():
    """
    Un registro del banco y dos del libro con la misma tienda+lote
    cuya suma de montos coincida exactamente deben quedar todos 'Conciliado'.
    """
    bank = make_bank(tienda='400', lote='00004', monto=1000.00, fecha='2026-04-01')

    libro_fila_1 = make_book(tienda='400', lote='00004', monto=600.00, fecha='2026-04-01')
    libro_fila_2 = make_book(tienda='400', lote='00004', monto=400.00, fecha='2026-04-01')
    book = pd.concat([libro_fila_1, libro_fila_2], ignore_index=True)

    resultado = reconcile(bank, book)

    estados_banco = [d['estado'] for d in resultado['detalles'] if d['origen'] == 'banco']
    estados_libro = [d['estado'] for d in resultado['detalles'] if d['origen'] == 'libro']

    assert all(e == 'Conciliado' for e in estados_banco)
    assert all(e == 'Conciliado' for e in estados_libro)
    assert resultado['resumen']['conciliados_banco'] == 1
    assert resultado['resumen']['conciliados_libro'] == 2


# ---------------------------------------------------------------------------
# Test 7 -- Diferencia dentro de tol_conciliado
# ---------------------------------------------------------------------------

def test_diferencia_dentro_tol_conciliado():
    """
    Una diferencia de monto <= tol_conciliado (default 1.00) debe
    resultar en 'Conciliado', no en 'Posible Conciliacion'.
    """
    bank = make_bank(tienda='500', lote='00005', monto=1000.00, fecha='2026-04-01')
    book = make_book(tienda='500', lote='00005', monto=1000.50, fecha='2026-04-01')

    resultado = reconcile(bank, book, tol_conciliado=1.00)

    assert get_estado(resultado, 'banco') == 'Conciliado'
    assert get_estado(resultado, 'libro') == 'Conciliado'