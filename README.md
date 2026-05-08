# Bank Reconciliation Service

Microservicio REST para conciliación bancaria automática. Compara extractos bancarios contra el libro contable aplicando criterios de tolerancia y conciliación N:1, y genera un reporte Excel con los resultados.

**Stack:** Python 3.11+ · Flask · pandas · pytest · openpyxl

---

## Requisitos previos

- Python 3.11 o superior
- pip

Para verificar que los tienes instalados:

```bash
python --version
pip --version
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/<tu-usuario>/Microservicio-Conciliacion-Bancaria.git
cd Microservicio-Conciliacion-Bancaria

# 2. Crear el entorno virtual
python -m venv venv

# 3. Activar el entorno virtual
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecutar el servidor

```bash
python src/app.py
```

El servidor queda disponible en `http://localhost:5000`.

Para confirmar que está corriendo, abre el navegador en:
```
http://localhost:5000/health
```

Deberías ver:
```json
{ "ok": true, "service": "reconciliation" }
```

---

## Probar los endpoints

### `GET /health`

**Navegador:**
```
http://localhost:5000/health
```

**PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:5000/health -Method GET | Select-Object -ExpandProperty Content
```

**curl (Windows 10/11):**
```bash
curl.exe -X GET http://localhost:5000/health
```

---

### `POST /reconciliar`

Ejecuta la conciliación con los archivos de la carpeta `datos/` y parámetros por defecto:

**PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:5000/reconciliar -Method POST | Select-Object -ExpandProperty Content
```

**curl (Windows 10/11):**
```bash
curl.exe -X POST http://localhost:5000/reconciliar
```

---

### `POST /reconciliar` con parámetros personalizados

Los parámetros se pasan como query string en la URL:

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `tolerancia_conciliacion` | `1.00` | Diferencia máxima de monto para considerar `Conciliado` |
| `tolerancia_posible` | `5.00` | Diferencia máxima de monto para considerar `Posible Conciliación` |
| `dias_ventana` | `3` | Días máximos de diferencia entre fechas banco y libro |

**Ejemplo con parámetros personalizados:**

```powershell
Invoke-WebRequest -Uri "http://localhost:5000/reconciliar?tolerancia_conciliacion=5&tolerancia_posible=20&dias_ventana=5" -Method POST | Select-Object -ExpandProperty Content
```

---

## Ejecutar las pruebas unitarias

```bash
pytest tests/ -v
```

Deberías ver 7 tests en verde:

```
tests/test_reconciliation.py::test_conciliacion_exacta_1_a_1 PASSED
tests/test_reconciliation.py::test_monto_fuera_de_tolerancia PASSED
tests/test_reconciliation.py::test_posible_conciliacion PASSED
tests/test_reconciliation.py::test_distinta_tienda_no_concilia PASSED
tests/test_reconciliation.py::test_fecha_fuera_de_ventana PASSED
tests/test_reconciliation.py::test_conciliacion_n_a_1 PASSED
tests/test_reconciliation.py::test_diferencia_dentro_tol_conciliado PASSED
7 passed
```

---

## Abrir el notebook de exploración

El notebook documenta el análisis de los datos realizado antes de escribir el código:

```bash
jupyter notebook
```

Navega a `notebooks/exploracion.ipynb` y ejecuta todas las celdas con `Cell → Run All`.

---

## Reportes Excel

Cada vez que se llama a `POST /reconciliar`, se genera automáticamente un reporte Excel en la carpeta `outputs/` con el formato:

```
reporte_conciliacion_YYYY-MM-DD_HHhMMmSSs.xlsx
```

El reporte incluye:
- Una tabla de resumen con totales, porcentaje de conciliación y leyenda de colores
- El detalle de todos los registros (banco y libro) con su estado final

Los colores indican el estado de cada registro:
- **Verde** → Conciliado
- **Amarillo** → Posible Conciliación
- **Rojo** → No Conciliado

En la carpeta `ejemplos/` se incluyen dos reportes pregenerados para referencia:
- `reporte_default_tol1_tol5_ventana3dias.xlsx` — parámetros por defecto
- `reporte_prueba_tol500_tol50000_ventana30dias.xlsx` — parámetros permisivos de prueba

---

## Estructura del proyecto

```
bank-reconciliation-service/
├── src/
│   ├── app.py                  # API Flask (endpoints /health y /reconciliar)
│   ├── config.py               # Configuración centralizada (rutas, tolerancias, filtros)
│   ├── file_processing.py      # Carga, filtrado y normalización de CSVs
│   └── reconciliation.py       # Lógica de conciliación (criterios 1-5)
├── tests/
│   └── test_reconciliation.py  # 7 pruebas unitarias
├── notebooks/
│   └── exploracion.ipynb       # Análisis exploratorio de los datos
├── datos/
│   ├── movimientos_banco.csv
│   └── libro_contable.csv
├── ejemplos/
│   ├── reporte_default_tol1_tol5_ventana3dias.xlsx
│   └── reporte_prueba_tol500_tol50000_ventana30dias.xlsx
├── outputs/                    # Reportes generados (no versionados)
├── requirements.txt
├── RESPUESTAS.md
└── README.md
```

---

## Criterios de conciliación implementados

| # | Criterio | Estado resultante |
|---|----------|------------------|
| 1 | Exacta 1 a 1 — mismo monto, fecha dentro de ventana | `Conciliado` |
| 2 | Tolerancia configurable de monto | `Conciliado` / `Posible Conciliación` |
| 3 | N a 1 — suma de montos del mismo lote coincide | `Conciliado` |
| 4 | Huérfano del banco cubre diferencia residual *(bonus)* | `Conciliado` |
| 5 | Reporte Excel con colores por estado *(bonus)* | — |

---

## Configuración

Todos los parámetros configurables del sistema están centralizados en `src/config.py`:

```python
DEFAULT_TOL_CONCILIADO = 1.00   # tolerancia para Conciliado
DEFAULT_TOL_POSIBLE    = 5.00   # tolerancia para Posible Conciliación
DEFAULT_DIAS_VENTANA   = 3      # ventana de fechas en días
```

Modificar estos valores cambia el comportamiento por defecto del sistema sin tocar la lógica.
---