"""
reconciliation.py
=================
Responsabilidad unica: aplicar los criterios de conciliacion sobre los
DataFrames ya limpios que entrega file_processing.py.

Criterios implementados:
  1. Conciliacion 1 a 1 exacta      (mismo monto, ventana de fechas)
  2. Conciliacion con tolerancia     (diferencia <= tol_conciliado -> Conciliado;
                                      diferencia <= tol_posible   -> Posible Conciliacion)
  3. Conciliacion N a 1 / 1 a N     (suma de montos del mismo lote coincide)
  4. (bonus) Diferencia con huerfano del banco
  5. (bonus) Generacion de reporte Excel

Estrategia de rendimiento:
  Los DataFrames se agrupan por ('tienda', 'lote') antes de comparar.
  Esto reduce la complejidad de O(n*m) global a comparaciones dentro
  de grupos pequenos, donde n y m son el total de registros de cada archivo.

Estados posibles de un registro:
  - 'No Conciliado'
  - 'Conciliado'
  - 'Posible Conciliacion'
"""

import pandas as pd

from config import (
    DEFAULT_TOL_CONCILIADO,
    DEFAULT_TOL_POSIBLE,
    DEFAULT_DIAS_VENTANA,
    OUTPUT_DIR,
)


# ---------------------------------------------------------------------------
# Funcion principal de orquestacion
# ---------------------------------------------------------------------------

def reconcile(
    df_bank: pd.DataFrame,
    df_book: pd.DataFrame,
    tol_conciliado: float = DEFAULT_TOL_CONCILIADO,
    tol_posible: float    = DEFAULT_TOL_POSIBLE,
    dias_ventana: int     = DEFAULT_DIAS_VENTANA,
) -> dict:
    """
    Orquesta todos los criterios de conciliacion en orden.

    Los criterios se aplican secuencialmente. Un registro que ya concilio
    en un criterio anterior no vuelve a evaluarse en los siguientes.
    Esto garantiza idempotencia: ejecutar reconcile() dos veces sobre
    los mismos datos produce el mismo resultado.

    Parametros
    ----------
    df_bank        : DataFrame del banco, ya filtrado y normalizado.
    df_book        : DataFrame del libro, ya filtrado y normalizado.
    tol_conciliado : Diferencia maxima de monto para -> 'Conciliado'.
    tol_posible    : Diferencia maxima de monto para -> 'Posible Conciliacion'.
    dias_ventana   : Dias maximos de diferencia entre fechas banco y libro.

    Retorna
    -------
    dict con claves:
        'resumen'  : dict con conteos globales.
        'detalles' : list[dict] con todos los registros y su estado final.
    """
    # Trabajamos sobre copias para no mutar los DataFrames originales.
    # Esto es clave para la idempotencia -- los datos de entrada no cambian.
    bank = df_bank.copy()
    book = df_book.copy()

    # Reiniciar estados antes de cada ejecucion (garantia de idempotencia)
    bank['estado'] = 'No Conciliado'
    book['estado'] = 'No Conciliado'

    # Separar registros sin prefijo -- no participan en la logica de criterios
    # pero si aparecen en el reporte final con estado 'No Conciliado'
    bank_sin_prefijo = bank[bank['sin_prefijo'] == True].copy()
    bank = bank[bank['sin_prefijo'] == False].copy()

    # Obtener todos los grupos unicos (tienda, lote) presentes en ambos archivos
    llaves_banco = set(zip(bank['tienda'], bank['lote']))
    llaves_libro = set(zip(book['tienda'], book['lote']))
    llaves       = llaves_banco | llaves_libro

    # Iterar sobre cada grupo (tienda, lote) y aplicar criterios en orden
    for tienda, lote in llaves:
        if tienda is None or lote is None:
            continue

        # Extraer el subgrupo de cada archivo para esta llave
        mask_bank = (bank['tienda'] == tienda) & (bank['lote'] == lote)
        mask_book = (book['tienda'] == tienda) & (book['lote'] == lote)

        idx_bank = bank[mask_bank].index.tolist()
        idx_book = book[mask_book].index.tolist()

        if not idx_bank or not idx_book:
            continue

        # -- Criterio 1: exacto 1 a 1 --
        bank, book = _criterio_1_exacto(
            bank, book, idx_bank, idx_book, dias_ventana
        )

        # Recalcular indices pendientes tras criterio 1
        idx_bank = bank[(mask_bank) & (bank['estado'] == 'No Conciliado')].index.tolist()
        idx_book = book[(mask_book) & (book['estado'] == 'No Conciliado')].index.tolist()

        if not idx_bank or not idx_book:
            continue

        # -- Criterio 2: tolerancia --
        bank, book = _criterio_2_tolerancia(
            bank, book, idx_bank, idx_book,
            tol_conciliado, tol_posible, dias_ventana
        )

        # Recalcular indices pendientes tras criterio 2
        idx_bank = bank[(mask_bank) & (bank['estado'] == 'No Conciliado')].index.tolist()
        idx_book = book[(mask_book) & (book['estado'] == 'No Conciliado')].index.tolist()

        if not idx_bank or not idx_book:
            continue

        # -- Criterio 3: N a 1 --
        bank, book = _criterio_3_n_a_1(
            bank, book, idx_bank, idx_book,
            tol_conciliado, tol_posible
        )

    # -- Criterio 4 (bonus): diferencia conocida con registro huerfano --
    bank = _criterio_4_huerfano(bank, book)

    # Reunir banco completo (con y sin prefijo)
    bank_final = pd.concat([bank, bank_sin_prefijo], ignore_index=True)

    resumen  = _build_resumen(bank_final, book)
    detalles = _build_detalles(bank_final, book)

    return {'resumen': resumen, 'detalles': detalles, 'df_banco': bank_final, 'df_libro': book}


# ---------------------------------------------------------------------------
# Criterio 1 -- Conciliacion 1 a 1 exacta
# ---------------------------------------------------------------------------

def _criterio_1_exacto(
    bank: pd.DataFrame,
    book: pd.DataFrame,
    idx_bank: list,
    idx_book: list,
    dias_ventana: int,
) -> tuple:
    """
    Intenta emparejar registros 1 a 1 con monto exactamente igual
    y fecha dentro de la ventana permitida.

    Algoritmo:
      Para cada registro del banco (en orden), busca el primer registro
      del libro con el mismo monto y fecha dentro de la ventana.
      Una vez emparejado, el registro del libro queda marcado y no
      puede volver a usarse ('usado' evita duplicar conciliaciones).

    Por que no usamos merge directo:
      Un merge por monto exacto podria crear pares duplicados si hay
      varios registros con el mismo monto en el mismo lote. El loop
      garantiza que cada registro se use una sola vez.
    """
    usados_libro = set()

    for ib in idx_bank:
        if bank.at[ib, 'estado'] != 'No Conciliado':
            continue

        monto_banco = bank.at[ib, 'Monto']
        fecha_banco = bank.at[ib, 'Fecha Efectiva']

        for il in idx_book:
            if il in usados_libro:
                continue
            if book.at[il, 'estado'] != 'No Conciliado':
                continue

            monto_libro = book.at[il, 'Monto']
            fecha_libro = book.at[il, 'Fecha Contable']

            if monto_banco == monto_libro and _fecha_dentro_ventana(
                fecha_banco, fecha_libro, dias_ventana
            ):
                bank.at[ib, 'estado'] = 'Conciliado'
                book.at[il, 'estado'] = 'Conciliado'
                usados_libro.add(il)
                break

    return bank, book


# ---------------------------------------------------------------------------
# Criterio 2 -- Conciliacion con tolerancia
# ---------------------------------------------------------------------------

def _criterio_2_tolerancia(
    bank: pd.DataFrame,
    book: pd.DataFrame,
    idx_bank: list,
    idx_book: list,
    tol_conciliado: float,
    tol_posible: float,
    dias_ventana: int,
) -> tuple:
    """
    Aplica tolerancia de monto sobre los registros que no conciliaron
    en el criterio 1.

    Reglas:
      diferencia <= tol_conciliado -> 'Conciliado'
      diferencia <= tol_posible    -> 'Posible Conciliacion'
      diferencia >  tol_posible    -> sin cambio ('No Conciliado')

    El mismo mecanismo de 'usados_libro' evita emparejar un registro
    del libro con multiples registros del banco.
    """
    usados_libro = set()

    for ib in idx_bank:
        if bank.at[ib, 'estado'] != 'No Conciliado':
            continue

        monto_banco = bank.at[ib, 'Monto']
        fecha_banco = bank.at[ib, 'Fecha Efectiva']

        mejor_il    = None
        mejor_diff  = float('inf')
        mejor_estado = None

        for il in idx_book:
            if il in usados_libro:
                continue
            if book.at[il, 'estado'] != 'No Conciliado':
                continue

            monto_libro = book.at[il, 'Monto']
            fecha_libro = book.at[il, 'Fecha Contable']

            if not _fecha_dentro_ventana(fecha_banco, fecha_libro, dias_ventana):
                continue

            diff = abs(monto_banco - monto_libro)

            if diff <= tol_conciliado and diff < mejor_diff:
                mejor_il     = il
                mejor_diff   = diff
                mejor_estado = 'Conciliado'
            elif diff <= tol_posible and diff < mejor_diff:
                mejor_il     = il
                mejor_diff   = diff
                mejor_estado = 'Posible Conciliacion'

        if mejor_il is not None:
            bank.at[ib, 'estado']       = mejor_estado
            book.at[mejor_il, 'estado'] = mejor_estado
            usados_libro.add(mejor_il)

    return bank, book


# ---------------------------------------------------------------------------
# Criterio 3 -- Conciliacion N a 1 / 1 a N
# ---------------------------------------------------------------------------

def _criterio_3_n_a_1(
    bank: pd.DataFrame,
    book: pd.DataFrame,
    idx_bank: list,
    idx_book: list,
    tol_conciliado: float,
    tol_posible: float,
) -> tuple:
    """
    Compara la SUMA de montos del grupo banco contra la SUMA del grupo libro
    para el mismo lote. Si coinciden dentro de la tolerancia, todos los
    registros del grupo se marcan con el estado correspondiente.

    Este criterio cubre el caso donde el banco agrupa en un solo movimiento
    lo que el libro registro como multiples ventas (o viceversa).

    Nota: este criterio no aplica ventana de fechas porque opera sobre
    la suma del grupo completo, no sobre pares individuales.
    """
    suma_banco = bank.loc[idx_bank, 'Monto'].sum()
    suma_libro = book.loc[idx_book, 'Monto'].sum()

    diff = abs(suma_banco - suma_libro)

    if diff <= tol_conciliado:
        estado = 'Conciliado'
    elif diff <= tol_posible:
        estado = 'Posible Conciliacion'
    else:
        return bank, book

    bank.loc[idx_bank, 'estado'] = estado
    book.loc[idx_book, 'estado'] = estado

    return bank, book



# ---------------------------------------------------------------------------
# Criterio 4 (bonus) -- Diferencia conocida con registro huerfano
# ---------------------------------------------------------------------------

def _criterio_4_huerfano(
    bank: pd.DataFrame,
    book: pd.DataFrame,
) -> pd.DataFrame:
    """
    Busca registros del banco sin par en el libro (huerfanos) cuyo monto
    coincida exactamente con la diferencia residual de un grupo ya procesado.

    Caso tipico:
      Banco lote X: 1000.00  (No Conciliado tras criterios 1-3)
      Libro lote X: 800.00   (No Conciliado tras criterios 1-3)
      Diferencia  : 200.00

      Banco huerfano (tienda/lote sin par en libro): 200.00
      -> Los tres registros se marcan como Conciliado.

    Un registro huerfano es aquel cuya combinacion (tienda, lote) no
    aparece en ningun registro del libro. Esto lo distingue de registros
    que simplemente no conciliaron por diferencia de monto.

    Parametros
    ----------
    bank : DataFrame del banco con estados actualizados tras criterios 1-3.
    book : DataFrame del libro con estados actualizados tras criterios 1-3.

    Retorna
    -------
    DataFrame del banco con estados actualizados para los huerfanos
    que resuelven diferencias residuales.
    """
    # Identificar llaves (tienda, lote) presentes en el libro
    llaves_libro = set(zip(book['tienda'], book['lote']))

    # Registros del banco cuya llave NO existe en el libro -> huerfanos
    mask_huerfano = bank.apply(
        lambda r: (r['tienda'], r['lote']) not in llaves_libro
        and r['estado'] == 'No Conciliado'
        and r['tienda'] is not None,
        axis=1
    )
    huerfanos = bank[mask_huerfano]

    if huerfanos.empty:
        return bank

    # Para cada grupo (tienda, lote) del libro con registros No Conciliados,
    # calcular la diferencia residual y buscar un huerfano que la cubra
    llaves_banco = set(zip(
        bank[bank['estado'] == 'No Conciliado']['tienda'],
        bank[bank['estado'] == 'No Conciliado']['lote']
    ))

    for tienda, lote in llaves_banco & llaves_libro:
        if tienda is None or lote is None:
            continue

        idx_banco_grupo = bank[
            (bank['tienda'] == tienda) &
            (bank['lote'] == lote) &
            (bank['estado'] == 'No Conciliado')
        ].index.tolist()

        idx_libro_grupo = book[
            (book['tienda'] == tienda) &
            (book['lote'] == lote) &
            (book['estado'] == 'No Conciliado')
        ].index.tolist()

        if not idx_banco_grupo or not idx_libro_grupo:
            continue

        suma_banco = bank.loc[idx_banco_grupo, 'Monto'].sum()
        suma_libro = book.loc[idx_libro_grupo, 'Monto'].sum()
        diferencia = abs(suma_banco - suma_libro)

        if diferencia == 0:
            continue

        # Buscar un huerfano cuyo monto sea exactamente la diferencia
        for ih in huerfanos.index:
            if bank.at[ih, 'estado'] != 'No Conciliado':
                continue
            if abs(bank.at[ih, 'Monto'] - diferencia) < 0.001:
                bank.loc[idx_banco_grupo, 'estado'] = 'Conciliado'
                book.loc[idx_libro_grupo, 'estado'] = 'Conciliado'
                bank.at[ih, 'estado'] = 'Conciliado'
                break

    return bank

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fecha_dentro_ventana(
    fecha_banco: pd.Timestamp,
    fecha_libro: pd.Timestamp,
    dias_ventana: int,
) -> bool:
    """
    Retorna True si la diferencia absoluta entre fechas es <= dias_ventana.

    Retorna False si cualquiera de las fechas es NaT (nula), ya que no
    podemos verificar la ventana sin ambas fechas.
    """
    if pd.isna(fecha_banco) or pd.isna(fecha_libro):
        return False
    return abs((fecha_banco - fecha_libro).days) <= dias_ventana


def _build_resumen(
    bank: pd.DataFrame,
    book: pd.DataFrame,
    total_banco_crudo: int = 0,
    total_libro_crudo: int = 0,
) -> dict:
    """
    Construye el dict 'resumen' con todos los conteos requeridos por la API.

    Sigue la estructura del enunciado como base y agrega campos adicionales
    que aportan mayor visibilidad sobre el resultado de la conciliacion.

    Campos del enunciado:
      total_banco              : total de registros en el archivo del banco
      total_libro              : total de registros en el archivo del libro
      registros_filtrados_banco: registros descartados del banco por filtro
      registros_filtrados_libro: registros descartados del libro por filtro
      conciliados              : total de pares conciliados (banco + libro)
      posibles_conciliados     : total en estado Posible Conciliacion
      no_conciliados           : total en estado No Conciliado (banco + libro)

    Campos adicionales (mayor visibilidad):
      sin_prefijo_banco        : registros sin prefijo para revision de Finanzas
      conciliados_banco        : conciliados solo del banco
      conciliados_libro        : conciliados solo del libro
    """
    conciliados_banco = int((bank['estado'] == 'Conciliado').sum())
    conciliados_libro = int((book['estado'] == 'Conciliado').sum())
    posibles_banco    = int((bank['estado'] == 'Posible Conciliacion').sum())
    posibles_libro    = int((book['estado'] == 'Posible Conciliacion').sum())
    no_conc_banco     = int((bank['estado'] == 'No Conciliado').sum())
    no_conc_libro     = int((book['estado'] == 'No Conciliado').sum())
    sin_prefijo       = int(bank.get('sin_prefijo', pd.Series(dtype=bool)).sum())

    return {
        # -- Estructura exacta del enunciado --
        'total_banco'               : total_banco_crudo or len(bank),
        'total_libro'               : total_libro_crudo or len(book),
        'registros_filtrados_banco' : max(0, (total_banco_crudo or len(bank)) - len(bank)),
        'registros_filtrados_libro' : max(0, (total_libro_crudo or len(book)) - len(book)),
        'conciliados'               : conciliados_banco + conciliados_libro,
        'posibles_conciliados'      : posibles_banco + posibles_libro,
        'no_conciliados'            : no_conc_banco + no_conc_libro,
        # -- Campos adicionales para mayor visibilidad --
        'sin_prefijo_banco'         : sin_prefijo,
        'conciliados_banco'         : conciliados_banco,
        'conciliados_libro'         : conciliados_libro,
        'posibles_banco'            : posibles_banco,
        'posibles_libro'            : posibles_libro,
        'no_conciliados_banco'      : no_conc_banco,
        'no_conciliados_libro'      : no_conc_libro,
    }


def _build_detalles(bank: pd.DataFrame, book: pd.DataFrame) -> list:
    """
    Construye la lista 'detalles' con todos los registros y su estado final.
    Incluye una columna 'origen' para distinguir banco de libro.
    """
    cols_banco = ['Referencia', 'tienda', 'lote', 'Monto', 'Fecha Efectiva',
                  'Tipo', 'Descripcion', 'estado', 'sin_prefijo']
    cols_libro = ['Número de Transacción', 'tienda', 'lote', 'Monto',
                  'Fecha Contable', 'Tipo', 'Proveedor', 'estado']

    # Seleccionar solo columnas que existen en cada DataFrame
    cols_banco = [c for c in cols_banco if c in bank.columns]
    cols_libro = [c for c in cols_libro if c in book.columns]

    bank_det = bank[cols_banco].copy()
    book_det = book[cols_libro].copy()

    bank_det['origen'] = 'banco'
    book_det['origen'] = 'libro'

    combined = pd.concat([bank_det, book_det], ignore_index=True)

    # Convertir fechas a string para serializar a JSON
    for col in combined.select_dtypes(include=['datetime64']).columns:
        combined[col] = combined[col].dt.strftime('%Y-%m-%d').where(
            combined[col].notna(), other=None
        )

    # Reemplazar NaN por None para JSON limpio.
    # fillna(value) no funciona para todos los tipos, por lo que usamos
    # applymap para convertir cada celda individualmente.
    import math

    def nan_to_none(val):
        if val is None:
            return None
        try:
            if math.isnan(float(val)) if not isinstance(val, str) else False:
                return None
        except (TypeError, ValueError):
            pass
        return val

    records = combined.to_dict(orient='records')
    return [
        {k: nan_to_none(v) for k, v in row.items()}
        for row in records
    ]


# ---------------------------------------------------------------------------
# Criterio 5 (bonus) -- Reporte de salida Excel
# ---------------------------------------------------------------------------

def generate_report(
    bank: pd.DataFrame,
    book: pd.DataFrame,
    output_path: str = None,
) -> str:
    """
    Genera un archivo Excel con todos los registros (banco + libro)
    y su estado final de conciliacion.

    Columnas del reporte:
      Origen | Referencia | Tienda | Lote | Monto | Fecha | Estado

    Aplica formato de color por estado:
      Verde  -> Conciliado
      Amarillo -> Posible Conciliacion
      Rojo   -> No Conciliado

    Retorna la ruta del archivo generado.
    """
    import os
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils import get_column_letter

    if output_path is None:
        from datetime import datetime
        timestamp   = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
        output_path = os.path.join(OUTPUT_DIR, f'reporte_conciliacion_{timestamp}.xlsx')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Construir filas del reporte
    filas = []

    for _, row in bank.iterrows():
        filas.append({
            'Origen'    : 'Banco',
            'Referencia': row.get('Referencia', ''),
            'Tienda'    : row.get('tienda', ''),
            'Lote'      : row.get('lote', ''),
            'Monto'     : row.get('Monto', ''),
            'Fecha'     : row['Fecha Efectiva'].strftime('%Y-%m-%d')
                          if pd.notna(row.get('Fecha Efectiva')) else '',
            'Estado'    : row.get('estado', ''),
        })

    for _, row in book.iterrows():
        filas.append({
            'Origen'    : 'Libro',
            'Referencia': row.get('Número de Transacción', ''),
            'Tienda'    : row.get('tienda', ''),
            'Lote'      : row.get('lote', ''),
            'Monto'     : row.get('Monto', ''),
            'Fecha'     : row['Fecha Contable'].strftime('%Y-%m-%d')
                          if pd.notna(row.get('Fecha Contable')) else '',
            'Estado'    : row.get('estado', ''),
        })

    # Colores por estado
    COLORES = {
        'Conciliado'          : 'C6EFCE',  # verde suave
        'Posible Conciliacion': 'FFEB9C',  # amarillo suave
        'No Conciliado'       : 'FFC7CE',  # rojo suave
    }

    wb = Workbook()
    ws = wb.active
    ws.title = 'Conciliacion'

    # -- Tabla de resumen --
    total        = len(filas)
    conciliados  = sum(1 for f in filas if f['Estado'] == 'Conciliado')
    posibles     = sum(1 for f in filas if f['Estado'] == 'Posible Conciliacion')
    no_conc      = sum(1 for f in filas if f['Estado'] == 'No Conciliado')
    pct_conc     = round(conciliados / total * 100, 1) if total else 0

    FILL_RESUMEN = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    FILL_TITULO  = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
    FONT_BLANCO  = Font(bold=True, color='FFFFFF')
    FONT_BOLD    = Font(bold=True)

    # Titulo del resumen
    titulo_celda = ws.cell(row=1, column=1, value='RESUMEN DE CONCILIACION')
    titulo_celda.font      = FONT_BLANCO
    titulo_celda.fill      = FILL_TITULO
    titulo_celda.alignment = Alignment(horizontal='center')
    ws.merge_cells('A1:G1')

    # Encabezados del resumen
    headers_resumen = ['Total Registros', 'Conciliados', '% Conciliado',
                       'Posible Conciliacion', 'No Conciliados',
                       'Banco', 'Libro']
    for col_idx, h in enumerate(headers_resumen, start=1):
        celda       = ws.cell(row=2, column=col_idx, value=h)
        celda.font  = FONT_BOLD
        celda.fill  = FILL_RESUMEN
        celda.alignment = Alignment(horizontal='center')

    # Valores del resumen
    total_banco = sum(1 for f in filas if f['Origen'] == 'Banco')
    total_libro = sum(1 for f in filas if f['Origen'] == 'Libro')
    valores_resumen = [total, conciliados, f'{pct_conc}%',
                       posibles, no_conc, total_banco, total_libro]
    for col_idx, val in enumerate(valores_resumen, start=1):
        celda           = ws.cell(row=3, column=col_idx, value=val)
        celda.alignment = Alignment(horizontal='center')
        celda.fill      = FILL_RESUMEN

    # Fila de leyenda de colores
    ws.cell(row=5, column=1, value='Leyenda:').font = FONT_BOLD
    leyenda = [
        ('Conciliado',           'C6EFCE'),
        ('Posible Conciliacion', 'FFEB9C'),
        ('No Conciliado',        'FFC7CE'),
    ]
    for col_idx, (label, color) in enumerate(leyenda, start=2):
        celda      = ws.cell(row=5, column=col_idx, value=label)
        celda.fill = PatternFill(start_color=color, end_color=color, fill_type='solid')
        celda.alignment = Alignment(horizontal='center')

    # Fila en blanco separadora
    fila_inicio_detalle = 7

    # -- Encabezados de la tabla de detalle --
    encabezados = ['Origen', 'Referencia', 'Tienda', 'Lote', 'Monto', 'Fecha', 'Estado']
    for col_idx, titulo in enumerate(encabezados, start=1):
        celda           = ws.cell(row=fila_inicio_detalle, column=col_idx, value=titulo)
        celda.font      = FONT_BLANCO
        celda.fill      = FILL_TITULO
        celda.alignment = Alignment(horizontal='center')

    # -- Datos con color por estado --
    for row_idx, fila in enumerate(filas, start=fila_inicio_detalle + 1):
        estado = fila.get('Estado', '')
        fill   = PatternFill(
            start_color=COLORES.get(estado, 'FFFFFF'),
            end_color=COLORES.get(estado, 'FFFFFF'),
            fill_type='solid'
        )
        for col_idx, key in enumerate(encabezados, start=1):
            celda           = ws.cell(row=row_idx, column=col_idx, value=fila.get(key, ''))
            celda.fill      = fill
            celda.alignment = Alignment(horizontal='center')

    # Ajustar ancho de columnas
    for col_idx in range(1, len(encabezados) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 22

    wb.save(output_path)
    return output_path