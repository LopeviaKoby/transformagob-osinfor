# Guía de Replicación Técnica

Esta guía detalla los pasos técnicos y consideraciones operativas necesarias para replicar, ejecutar y mantener el sistema **Huella Digital del Árbol**.

---

## 🛠️ Requisitos Previos

Asegúrate de contar con el siguiente software instalado en tu entorno local:
- **Python 3.10 o superior**
- **Node.js (versión LTS recomendada)**
- **pnpm** (gestor de paquetes para el frontend)
- **Git**

---

## 🚀 Replicación Paso a Paso

### 1. Preparación del Backend
1. Abre tu terminal en el directorio raíz del proyecto (`transformagob-osinfor`).
2. Crea un entorno virtual de Python para mantener aisladas las dependencias:
   ```bash
   python -m venv .venv
   ```
3. Activa el entorno virtual:
   - **En Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **En macOS/Linux (Bash):**
     ```bash
     source .venv/bin/activate
     ```
4. Instala las dependencias necesarias:
   ```bash
   python -m pip install -r requirements.txt
   ```

### 2. Generación de las Bases de Datos (SQLite)
El sistema utiliza dos bases de datos SQLite que se construyen a partir de fuentes de staging y datos raw:
1. Reconstruye la base de datos de casos heredados (`huella_origen.db`):
   ```bash
   python scripts/build_db.py
   ```
2. Construye el catálogo de trazabilidad ampliado (`huella_catalog.db`) a partir de las fuentes en `raw/`:
   ```bash
   python scripts/build_catalog.py
   ```
   *Nota: Las bases de datos resultantes se crearán en la carpeta `db/` y están excluidas de Git mediante `.gitignore` para evitar redundancias de almacenamiento.*

### 3. Configuración e Inicio del Frontend
1. Navega al directorio del frontend:
   ```bash
   cd frontend
   ```
2. Instala los paquetes y dependencias del proyecto usando `pnpm`:
   ```bash
   pnpm install
   ```
3. (Opcional) Crea el archivo de configuración de variables de entorno a partir del ejemplo:
   ```bash
   cp .env.example .env
   ```
4. Inicia el servidor de desarrollo del frontend:
   ```bash
   pnpm dev
   ```
   La aplicación web estará disponible de manera predeterminada en [http://localhost:5173](http://localhost:5173).

### 4. Inicio del Backend API
1. Regresa al directorio raíz e inicia el servidor de desarrollo FastAPI usando `uvicorn`:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Puedes verificar el estado de la API visitando:
   - **Salud del backend:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   - **Documentación interactiva (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📊 Estado Actual del Proyecto

El prototipo se encuentra completamente funcional y cuenta con los siguientes componentes integrados:

- **Backend (API FastAPI):** 
  - Capa de servicios y repositorios desacoplada.
  - Conexión de solo lectura (`read-only`) y bajo demanda a dos bases SQLite: una para los casos de regresión históricos y otra para el catálogo dinámico de trazas.
  - Endpoints de consulta de casos, búsqueda predictiva y resolución de trazabilidad total por identificadores.
- **Frontend (React + TypeScript + Vite):**
  - Interfaz de búsqueda responsiva con sugerencias.
  - Vista detallada del linaje forestal, visualización del flujo de volúmenes maderables entre etapas, paneles de control/validación y generación de código QR.
  - Soporte nativo para impresión optimizada de las fichas de trazabilidad.
- **Etapa de Datos (ETL):** 
  - Scripts en Python estructurados para parsear datos brutos de hojas de cálculo de censos forestales, libros de operaciones y balances de extracción en PDF.
  - Normalización robusta de códigos de identificación, especies y control de calidad.

---

## ⚠️ Restricciones Operativas

Al realizar modificaciones en el código o incorporar nuevos datos, es obligatorio cumplir con las siguientes directrices del negocio:

- **Seguridad en la Base de Datos:** Las consultas ejecutadas por la API hacia SQLite deben ser estrictamente de solo lectura. No se permiten operaciones de escritura/modificación desde la API pública.
- **Privacidad de la Información:** Queda estrictamente prohibido exponer en la interfaz de usuario (UI), respuestas de API o logs públicos datos sensibles como:
  - RUC, DNI, nombres de inspectores, placas vehiculares, coordenadas geográficas exactas, observaciones internas de auditoría o rutas de archivos locales.
- **Terminología y Clasificación:** El sistema **no debe emitir veredictos de legalidad**. No utilices en las proyecciones visuales términos como: *legal, ilegal, aprobado, certificado, fraude*. 
  - En su lugar, utiliza los estados permitidos: `CONSISTENTE`, `POR_REVISAR`, `INCOMPLETO`, `NO_EVALUADO`.
  - Para los controles, utiliza únicamente: `PASS`, `FAIL`, `NOT_EVALUATED`.
- **Campo `R`:** El campo denominado `R` en los esquemas carece de semántica de negocio validada. No debe ser expuesto al público ni debe afectar estados, cálculos de volúmenes o relaciones de linaje.
- **Integridad de Datos:** Un vacío en el origen de datos nunca debe ser mapeado o interpretado como cero (`0`). Mantén el valor vacío original para evitar distorsiones en el flujo.

---

## 💡 Recomendaciones de Desarrollo y Mantenimiento

1. **Uso de Pruebas de Regresión:**
   Antes de realizar cualquier despliegue, ejecuta el conjunto de pruebas unitarias y de humo para asegurar que no se hayan roto los casos estándar:
   ```bash
   # Pruebas unitarias
   python -m unittest discover -s tests -v

   # Pruebas de humo de API y consulta
   python scripts/smoke_api.py
   python scripts/smoke_public_query.py
   python scripts/smoke_catalog_api.py
   ```
2. **Casos de Regresión Críticos:**
   Verifica siempre que los siguientes casos de prueba conserven sus propiedades:
   - **`clean-pc01-501`** (Árbol 501, Parcela PC 01, especie Manchinga): Debe reportar consistencia en los volúmenes (`5.881 -> 5.643 -> 5.192`) y estado `CONSISTENTE`.
   - **`inconsistent-pc01-1170`** (Árbol 1170, Parcela PC 01): Debe detectar el cambio de especie entre censo (Estoraque) y supervisión (Azúcar huayo) y reportar estado `POR_REVISAR`.
3. **Manejo de Volúmenes y Precisión:**
   Si decides ampliar el catálogo de base de datos o modificar la lógica de cálculo, utiliza siempre tipos numéricos de precisión (`Decimal` o equivalentes reales en base de datos) para evitar discrepancias por redondeo decimal.
4. **Extensiones del Catálogo:**
   Si se reciben nuevos datos de origen en la carpeta `raw/`, actualiza el manifiesto correspondiente en `staging/catalog/` y regenera el catálogo usando `scripts/build_catalog.py` para recalcular índices de búsqueda y reportes de consistencia.
