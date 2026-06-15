# Huella Digital del Árbol

Repositorio del prototipo `Huella Digital del Árbol` para OSINFOR. El proyecto consolida evidencia forestal y expone una consulta pública de trazabilidad desde dos bases SQLite de solo lectura:

- `db/huella_origen.db`: expedientes heredados `clean-pc01-501` e `inconsistent-pc01-1170`.
- `db/huella_catalog.db`: catálogo ampliado con búsqueda por GTF, troza, árbol y título habilitante.

La solución no declara legalidad, no reemplaza una GTF y no sustituye una certificación oficial ni una decisión administrativa.

## Objetivo funcional

Cuando las fuentes lo permiten, el sistema reconstruye el siguiente linaje:

`titulo habilitante -> plan/resolucion -> parcela -> arbol censado -> supervision -> tala -> trozado -> despacho -> GTF -> balance por especie y parcela`

Reglas funcionales confirmadas:

- Llave de árbol: `titulo_habilitante + parcela_corta + codigo_arbol`
- Llave de troza: `titulo_habilitante + parcela_corta + codigo_troza`
- Llave de balance: `titulo_habilitante + parcela_corta + especie`
- Una GTF puede contener varias trozas
- No existe “saldo del árbol”
- Los vacíos no equivalen a cero
- El campo `R` no tiene semántica confirmada y no debe afectar estados, volúmenes ni relaciones

## Stack

### Backend

- Python
- FastAPI
- SQLite

Dependencias declaradas en [requirements.txt](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\requirements.txt):

- `fastapi`
- `uvicorn`
- `httpx2`
- `pandas`
- `openpyxl`
- `pypdf`

### Frontend

- React 19
- TypeScript
- Vite
- pnpm

Scripts principales en [frontend/package.json](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\frontend\package.json):

- `pnpm dev`
- `pnpm build`
- `pnpm lint`

## Estructura del repositorio

### API y acceso a datos

- [app/main.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\main.py): aplicación FastAPI, endpoints públicos y cabeceras de seguridad.
- [app/service.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\service.py): proyección pública sobre `huella_origen.db`.
- [app/repository.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\repository.py): consultas de solo lectura a `huella_origen.db`.
- [app/database.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\database.py): conexión SQLite read-only para la base heredada.
- [app/catalog_service.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\catalog_service.py): proyección pública del catálogo ampliado.
- [app/catalog_repository.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\catalog_repository.py): búsqueda exacta y detalle desde `huella_catalog.db`.
- [app/catalog_database.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\catalog_database.py): conexión SQLite read-only para el catálogo.

### Bases y esquemas

- [db/huella_origen.db](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\db\huella_origen.db): base pública heredada.
- [db/huella_catalog.db](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\db\huella_catalog.db): catálogo SQLite ampliado.
- [db/schema.sql](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\db\schema.sql): esquema de `huella_origen.db`.
- [db/catalog_schema.sql](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\db\catalog_schema.sql): esquema del catálogo.

### ETL y utilitarios

- [scripts/build_db.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\build_db.py): reconstruye `huella_origen.db` a partir de `staging/cases/`.
- [scripts/build_catalog.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\build_catalog.py): construye `huella_catalog.db`.
- [scripts/catalog_normalization.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\catalog_normalization.py): normalización de encabezados, códigos, GTF, especies, volúmenes y fechas.
- [scripts/catalog_parsers.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\catalog_parsers.py): parseo de Excel y PDF.
- [scripts/inventory_sources.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\inventory_sources.py): inventario de fuentes reales.
- [scripts/smoke_api.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\smoke_api.py), [scripts/smoke_public_query.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\smoke_public_query.py), [scripts/smoke_catalog_api.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\scripts\smoke_catalog_api.py): pruebas rápidas.

### Frontend

- [frontend/src/App.tsx](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\frontend\src\App.tsx): flujo principal entre búsqueda y detalle.
- [frontend/src/api](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\frontend\src\api): clientes HTTP del frontend.
- [frontend/src/components](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\frontend\src\components): banner, búsqueda, resultados, detalle, QR, impresión y FAQ.
- [frontend/src/types](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\frontend\src\types): contratos TypeScript del frontend.

### Pruebas

- [tests/test_api.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\tests\test_api.py): API pública heredada.
- [tests/test_public_query.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\tests\test_public_query.py): proyecciones públicas de `huella_origen.db`.
- [tests/test_catalog.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\tests\test_catalog.py): catálogo, normalización, checks e índices.
- [tests/test_catalog_api.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\tests\test_catalog_api.py): búsqueda y detalle del catálogo vía FastAPI.

### Datos y staging

- `raw/`: fuentes originales; no se deben modificar.
- `staging/cases/`: JSON heredados de expedientes.
- `staging/catalog/`: inventarios, manifiestos y reportes del catálogo.

## Fuentes de datos confirmadas

Las ocho fuentes reales esperadas del catálogo son:

- `raw/censo/censo_forestal.xlsx`
- `raw/muestra/muestra_supervisada.xlsx`
- `raw/libro/pc01/libro_operaciones_pc01.xlsx`
- `raw/libro/pc01/libro_operaciones_pc02.xlsx`
- `raw/libro/pc01/libro_operaciones_pc03.xlsx`
- `raw/balance/pc01/balance_extraccion_pc01.pdf`
- `raw/balance/pc01/balance_extraccion_pc02.pdf`
- `raw/balance/pc01/balance_extraccion_pc03.pdf`

## Modelo de exposición pública

Estados visibles permitidos:

- `CONSISTENTE`
- `POR_REVISAR`
- `INCOMPLETO`
- `NO_EVALUADO`
- `INCONSISTENTE` solo como compatibilidad heredada

Controles visibles permitidos:

- `PASS`
- `FAIL`
- `NOT_EVALUATED`

No deben exponerse en la UI ni en la API pública:

- RUC
- DNI
- coordenadas
- placas
- inspectores
- observaciones internas
- valor de `R`
- rutas locales
- registros crudos

## Endpoints actuales

### Generales

- `GET /`
  - estado general del servicio
- `GET /health`
  - salud del backend
  - modo de base `read-only`
  - conteo de expedientes heredados
  - disponibilidad del catálogo
  - conteo de trazas del catálogo

### API pública

- `GET /api/v1/cases`
  - lista pública de los dos expedientes heredados
- `GET /api/v1/verifications/{case_id}`
  - intenta resolver primero contra `huella_origen.db`
  - si no existe, consulta `trace_catalog` en `huella_catalog.db`
- `GET /api/v1/search?query=<valor>`
  - búsqueda exacta contra `search_identifiers`
  - soporta GTF, troza, árbol y título habilitante
  - máximo 20 resultados

## Arranque local

### 1. Backend

Instalar dependencias Python:

```powershell
python -m pip install -r requirements.txt
```

Levantar FastAPI:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

URLs útiles:

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Docs OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Frontend

Desde `frontend/`:

```powershell
pnpm dev
```

La app queda disponible normalmente en:

- [http://localhost:5173](http://localhost:5173)

### 3. Flujo recomendado de desarrollo

1. Levantar backend en `127.0.0.1:8000`
2. Levantar frontend con `pnpm dev`
3. Verificar búsqueda y detalle desde la interfaz

## Pruebas

### Backend

```powershell
python -m unittest discover -s tests -v
```

### Smoke tests

```powershell
python .\scripts\smoke_api.py
python .\scripts\smoke_public_query.py
python .\scripts\smoke_catalog_api.py
```

### Frontend

```powershell
cd frontend
pnpm build
pnpm lint
```

## Bases de datos y modo de acceso

Las dos conexiones SQLite se abren en modo URI `mode=ro` y activan:

- `sqlite3.Row`
- `PRAGMA foreign_keys = ON`
- `PRAGMA query_only = ON`

No se mantienen conexiones globales; cada capa de acceso abre y cierra su conexión por operación.

## Casos de regresión relevantes

### Expediente heredado limpio

- `case_id`: `clean-pc01-501`
- árbol `501`
- parcela `PC 01`
- troza `501/A`
- GTF `017-0001426`
- estado esperado `CONSISTENTE`

### Expediente heredado con observaciones

- `case_id`: `inconsistent-pc01-1170`
- árbol `1170`
- parcela `PC 01`
- trozas `1170/A`, `1170/B`, `1170/C`
- GTF `017-0001311`, `017-0001332`, `017-0001349`
- estado esperado heredado en UI pública: `Evidencia con observaciones`

## Restricciones operativas

- No modificar `raw/`
- No sobrescribir `db/huella_origen.db`
- No sobrescribir `db/huella_catalog.db` salvo una reconstrucción explícita del catálogo
- No cambiar contratos ni reglas de trazabilidad sin validación funcional
- No interpretar el campo `R`
- No usar términos públicos como `legal`, `ilegal`, `aprobado`, `certificado` o `fraude`

## Estado actual del repositorio

El repositorio ya incluye:

- API pública FastAPI sobre dos bases SQLite
- búsqueda por identificadores del catálogo
- pantalla inicial de búsqueda
- detalle con origen, especie, volumen, controles, transporte, balance, QR, huella digital e impresión

Si necesitas continuar el desarrollo, el punto de entrada recomendado es [app/main.py](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\app\main.py) para backend y [frontend/src/App.tsx](C:\Users\Pedro Lopevia\Escritorio\transformagob-osinfor\frontend\src\App.tsx) para frontend.
