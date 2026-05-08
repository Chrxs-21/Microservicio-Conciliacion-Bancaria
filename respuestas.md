## 1. API REST

Una API REST es básicamente una forma estándar de comunicación entre sistemas a través de internet. Podemos entenderlo mejor haciendo la analogia de un menú de restaurante: el cliente (quien hace la petición) ve el menú (los endpoints disponibles), hace su pedido (la petición HTTP), y el restaurante (el servidor) le trae lo que pidió (la respuesta). Todo esto ocurre siguiendo unas reglas claras para que ambos lados se entiendan. Vale la pena mencionar que las APIs son una parte integral de las arquitecturas de microservicios (como el realizado en la prueba), donde su funcion principal en este contexto es la de facilitar la comunicación entre los componentes, permitiendo que estos funcionen de manera independiente, lo cual es fundamental para el diseño de sistemas modernos y escalables.

**Principales verbos HTTP:**

 `GET`= Para obtener información sin modificar nada. En la prueba se usa en /health para verificar que el servicio está corriendo. 
 `POST`= Para enviar datos y ejecutar una acción. Lo usamos en /reconciliar para iniciar el proceso de conciliación. 
 `PUT`=  Para reemplazar un recurso existente completamente.
 `PATCH`= Para modificar solo una parte de un recurso.
 `DELETE`= Para eliminar un recurso.

**Códigos de respuesta HTTP:**

 `200` OK — la solicitud fue exitosa y se retorna el resultado esperado.
 `400` Bad Request — la solicitud tiene errores (parametros invalidos, datos malformados).
 `401` Unauthorized — el cliente no esta autenticado para acceder al recurso.
 `404` Not Found — el recurso o endpoint solicitado no existe.
 `500` Internal Server Error — ocurrio un error inesperado en el servidor.

En este proyecto usamos `200` para respuestas exitosas, `400` para parametros invalidos y `500` para errores internos durante la conciliacion.

---

## 2. Microservicios

Una arquitectura de microservicios es una forma de construir software donde en vez de tener una sola aplicación grande que hace todo, divides el sistema en servicios pequeños e independientes, cada uno con una responsabilidad específica. Cada servicio se puede desarrollar, desplegar y escalar por separado, y se comunican entre sí normalmente a través de APIs.
Este proyecto es un buen ejemplo, ya que es un microservicio que se encarga exclusivamente de la conciliación bancaria. No sabe nada de facturación, nómina ni ningún otro proceso, solo concilia.

**Ventajas frente a una arquitectura monolitica:**

1. **Escalabilidad independiente**: si el servicio de conciliación empieza a recibir mucha carga, puedes escalar solo ese servicio sin tocar el resto del sistema. En un monolito tendrías que escalar todo aunque el cuello de botella sea solo una parte.
2. **Despliegue independiente**: puedes actualizar y desplegar el microservicio de conciliación sin afectar ni interrumpir otros servicios que están corriendo en producción. En un monolito, cualquier cambio implica redesplegar toda la aplicación.

**Desventajas frente a una arquitectura monolitica:**

1. **Mayor complejidad operacional**: gestionar muchos servicios independientes requiere más infraestructura, más monitoreo y más coordinación que un solo sistema centralizado. Un monolito es más simple de operar al principio.
2. **Latencia de red**: cuando los microservicios necesitan comunicarse entre sí, lo hacen a través de la red, lo que introduce una latencia que no existe en un monolito donde todo corre en el mismo proceso.

---

## 3. Pruebas Unitarias

Las pruebas unitarias son importantes porque te dan la seguridad de que cada parte del código funciona correctamente de forma aislada. Sin ellas, cada vez que modificas algo tienes que probar todo manualmente para asegurarte de que no se rompió nada, lo cual es lento, propenso a errores y poco confiable.
En este proyecto por ejemplo, si alguien modifica la lógica del Criterio 2 de tolerancia y accidentalmente rompe el Criterio 1, el test test_conciliacion_exacta_1_a_1 falla inmediatamente y te dice exactamente qué se rompió, sin necesidad de correr el sistema completo ni revisar miles de registros manualmente.

**Diferencia entre prueba unitaria y prueba de integracion:**

Una prueba unitaria verifica un componente de forma completamente aislada, sin depender de ningún sistema externo. En este proyecto, los tests usan DataFrames sintéticos pequeños con valores controlados (no los CSVs reales) precisamente para que cada test sea independiente y su resultado sea predecible.

Una prueba de integración en cambio verifica que varios componentes funcionan correctamente juntos. Por ejemplo, probar que al llamar POST /reconciliar con los archivos CSV reales, el sistema carga los datos, los procesa y retorna un JSON correcto, ahí están interactuando Flask, file_processing.py y reconciliation.py al mismo tiempo.

Vale la pena aclarar que usar valores fijos en los tests no es lo mismo que hardcodear. Hardcodear sería poner una tolerancia fija dentro de la lógica de producción. En los tests, los valores fijos son escenarios controlados donde conocemos exactamente la entrada y sabemos cuál debe ser la salida. Es la única forma de hacer los tests confiables y deterministas.

---

## 4. Git

`git clone`: descarga una copia completa de un repositorio remoto a tu máquina local, incluyendo todo el historial de cambios y todas las ramas. Es el primer paso cuando vas a trabajar en un proyecto que ya existe en GitHub.

`git branch`: lista las ramas existentes o crea una nueva. Las ramas permiten trabajar en una funcionalidad de forma aislada sin afectar el código principal. En este proyecto creamos una rama por cada issue, como feat/procesamiento-datos o test/pruebas-unitarias.

`git add`: marca los archivos que quieres incluir en el próximo commit. No todos los cambios que hiciste tienen que ir juntos, git add te permite elegir exactamente qué va en cada snapshot.

`git commit`: guarda un snapshot de los cambios marcados con git add, junto con un mensaje que describe qué se hizo. Es como tomar una foto del estado del código en ese momento, con una nota que explica por qué.

`git push`: sube los commits que tienes localmente al repositorio remoto en GitHub, haciendo los cambios visibles para el resto del equipo.

`git pull`: descarga y fusiona los cambios del repositorio remoto en tu rama local. Es lo primero que se debería hacer al iniciar una sesión de trabajo para asegurarte de tener la versión más reciente del código.

**Pull Request (PR):** es una solicitud formal para fusionar los cambios de una rama hacia otra, normalmente hacia develop o main. Antes de fusionarse, otros miembros del equipo pueden revisar el código, dejar comentarios y sugerir mejoras. Es la base del trabajo colaborativo profesional. Nadie sube código directamente a main sin que alguien más lo haya revisado primero.

En este proyecto usamos PRs para integrar cada feature desde su rama de trabajo hacia develop y una vez culminado por completo y probado que todo funcione como fue previsto, se usó otro PR de develop hacia main.

---

## 5. Pandas

Si tuviera un DataFrame con una columna fecha como string y necesitara filtrar los registros del último mes, haría lo siguiente:

**Paso 1 — Convertir la columna a datetime:**

```python
df['fecha'] = pd.to_datetime(df['fecha'])
```
Este paso es imprescindible antes de cualquier comparación. Si la columna sigue siendo texto, pandas no sabe que '2026-03-31' es anterior a '2026-04-01' — los estaría comparando como strings, no como fechas.

**Paso 2 — Calcular el rango del ultimo mes:**

```python
hoy = pd.Timestamp.today()
inicio_mes = hoy - pd.DateOffset(months=1)
```

**Paso 3 — Filtrar con una mascara booleana:**

```python
mascara = df['fecha'] >= inicio_mes
df_ultimo_mes = df[mascara]
```

Una máscara booleana es una serie de valores True y False del mismo largo que el DataFrame. Pandas la usa para conservar solo las filas donde el valor es True. Es la forma más eficiente de filtrar en pandas porque opera sobre todas las filas a la vez, sin necesidad de iterar una por una con un bucle.
En este proyecto aplicamos exactamente este mismo concepto en file_processing.py para filtrar los registros del banco y del libro:

```python
mascara = df['Descripcion'].str.startswith(BANK_VALID_DESCRIPTIONS, na=False)
df_filtrado = df[mascara]
```
---

## 6. Diseño y Escalabilidad

Si el servicio tuviera que procesar millones de registros, consideraria las siguientes mejoras:

**Optimizacion del algoritmo:**
El algoritmo actual ya toma una decisión importante para el rendimiento: agrupa los registros por (tienda, lote) antes de comparar, evitando comparar cada registro del banco contra cada registro del libro. Sin ese agrupamiento, con un millón de registros en cada archivo estaríamos hablando de un billón de comparaciones. Sin embargo, para volúmenes muy grandes se podría complementar con procesamiento por partes usando Dask, que es una librería similar a pandas pero diseñada para datos que no caben en memoria.

**Cola de trabajos asincrona:**
Actualmente el endpoint POST /reconciliar procesa todo dentro del mismo request HTTP, lo que significa que el cliente tiene que esperar hasta que termine. Con millones de registros eso podría tardar minutos. La solución sería usar una cola de tareas como Celery con Redis: el cliente envía los archivos, recibe un id de tarea inmediatamente, y luego consulta el resultado cuando está listo sin tener que mantener la conexión abierta.

**Base de datos:**
En lugar de leer archivos CSV cada vez, los movimientos del banco y el libro se almacenarían en una base de datos como PostgreSQL, con índices en las columnas tienda y lote. Esto permite hacer consultas eficientes sin cargar millones de filas en memoria de una sola vez.

**Escalado horizontal:**
El servicio se empaquetaría en un contenedor Docker para poder levantar múltiples instancias del mismo servicio detrás de un balanceador de carga. Si la demanda aumenta, se agregan más instancias; si baja, se reducen.

**Historial de conciliaciones:**
Actualmente cada ejecución genera un reporte Excel nuevo. A escala, los resultados se guardarían en base de datos para permitir consultas históricas sin recalcular desde cero.


## 7. DESICIONES DE DISEÑO Y JUSTIFICACIONES

**Uso de Jupyter Notebook para la exploración de datos**
Antes de escribir cualquier línea de código de producción, se utilizó un Jupyter Notebook (notebooks/exploracion.ipynb) para explorar los archivos CSV reales. Esto no estaba en el enunciado pero se consideró una práctica importante.

- Lo que se ganó: fue posible entender la estructura real de los datos antes de asumir nada, se descubrieron inconsistencias como la del prefijo M entre banco y libro, y quedó documentado el razonamiento que llevó a cada decisión de diseño. Facilita poder ver el proceso de pensamiento que utilice, no solo el resultado final.
- Lo que se perdió: es un archivo adicional que requiere tener Jupyter instalado para ejecutarlo.

**config.py como módulo de configuración centralizada**
El enunciado pedía que las tolerancias fueran configurables. Se decidió ir un paso más allá y centralizar toda la configuración del proyecto en un solo archivo config.py, incluyendo rutas de archivos, tolerancias y filtros.

- Lo que se ganó: cualquier persona que reciba el proyecto sabe exactamente dónde cambiar cualquier parámetro sin tener que buscar dentro de la lógica. También evita que el mismo valor esté definido en múltiples lugares.
- Lo que se perdió: un archivo adicional que en proyectos muy pequeños podría considerarse innecesario.

**Enriquecimiento del resumen de la API**
El enunciado define una estructura base para el campo resumen. Se decidió mantener esa estructura y agregar campos adicionales que separan los conteos por origen (banco vs libro).

- Lo que se ganó: el área de Finanzas puede identificar rápidamente si las diferencias están concentradas en un sistema específico, lo cual es información valiosa al investigar discrepancias.
- Lo que se perdió: una respuesta JSON más extensa que podría considerarse verbosa para un consumidor que solo necesita los totales básicos.

**Registros sin prefijo**
Se encontraron 2 registros en el banco con referencias "01046" y "02046" que no tienen prefijo alfabético y por lo tanto no se pueden parsear para extraer tienda y lote. Una decisión fácil habría sido descartarlos silenciosamente.
Se decidió incluirlos en el reporte final con estado No Conciliado y marcarlos con sin_prefijo=True, además de contabilizarlos por separado en el resumen. El razonamiento es que estos registros existen en el sistema del banco por alguna razón. Ignorarlos podría ocultar un problema real que el área de Finanzas necesita investigar.

**Reportes Excel con timestamp en el nombre**
En vez de sobreescribir siempre el mismo archivo reporte_conciliacion.xlsx, cada ejecución genera un archivo nuevo con el formato reporte_conciliacion_YYYY-MM-DD_HHhMMmSSs.xlsx.
- Lo que se ganó: se preserva el historial de ejecuciones, lo que permite comparar resultados entre distintos parámetros sin perder información anterior.
- Lo que se perdió: la carpeta outputs/ puede acumular muchos archivos si el servicio se ejecuta frecuentemente. En producción se implementaría una política de retención automática.