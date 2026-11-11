# BBVA México · Fondos de Inversión (Anaquel de Rendimientos)

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![SQLite WAL](https://img.shields.io/badge/SQLite-WAL%20Hardened-003B57.svg)](https://sqlite.org)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5.svg)](https://www.home-assistant.io/)
[![HACS Ready](https://img.shields.io/badge/HACS-Custom%20Component-orange.svg)](https://hacs.xyz/)

Servicio integral de extracción, base de datos histórica, API RESTful y dashboard financiero para consultar y graficar los **"Anaquel con Rendimientos Históricos del Día Actual"** de los fondos de inversión de BBVA México. Diseñado y preparado para su ejecución autónoma y su instalación directa en **Home Assistant**.

---

## 🏛️ Arquitectura del Sistema (Delegada vía `/skills-manager`)

El proyecto fue orquestado utilizando la metodología modular de **Skills Manager**, delegando responsabilidades a skills especializadas:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        BBVA Portal (PDF Oficial)                       │
│        "Anaquel con Rendimientos Históricos del Día Actual"            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Scraper & Parser Engine                         │
│  [app/scraper.py] Descarga resiliente HTTP con fallbacks               │
│  [app/parser.py]  Extracción pypdf: Ticker, Serie, Rendimientos, Fecha │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Base de Datos SQLite Hardened (database-architect)         │
│  [app/database.py] PRAGMAs: WAL, Foreign Keys, Busy Timeout 5000ms    │
│  [app/repository.py] Upserts idempotentes en funds, series, history    │
└──────────────┬──────────────────────────────────────────┬──────────────┘
               │                                          │
               ▼                                          ▼
┌──────────────────────────────┐        ┌────────────────────────────────┐
│   Backend RESTful (backend)  │        │   Home Assistant Integration   │
│  - FastAPI con OpenAPI 3.1   │        │   (homeassistant-integrations) │
│  - Standard Response Envelope│        │  - custom_components/bbva_fondos│
│  - docs/API_CONTRACT.md      │        │  - DataUpdateCoordinator       │
│  - UI Dashboard (ui-ux)      │        │  - UI ConfigFlow & OptionsFlow │
│  - Gráficas Chart.js         │        │  - Entidades de Moneda y %     │
└──────────────────────────────┘        └────────────────────────────────┘
```

---

## 🚀 Inicio Rápido Local

### Requisitos Previos
- Python 3.12+ (o Docker)
- Entorno virtual

### 1. Clonar e Instalar Dependencias
```bash
cd /home/ricardom/ha_fondosInversion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Iniciar el Servicio
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload
```

El servicio estará disponible en:
- **Dashboard Financiero**: [http://localhost:8088/](http://localhost:8088/)
- **Documentación Interactiva (Swagger)**: [http://localhost:8088/docs](http://localhost:8088/docs)
- **Contrato OpenAPI**: [http://localhost:8088/api/v1/contract](http://localhost:8088/api/v1/contract)

### 3. Sincronizar el PDF Oficial de BBVA
Al abrir el dashboard, presiona el botón **"Sincronizar PDF"** o ejecuta desde terminal:
```bash
curl -X POST http://localhost:8088/api/v1/sync
```

---

## 🏠 Instalación en Home Assistant

La integración está empaquetada siguiendo los estándares de **Home Assistant Community Store (HACS)** y el **Integration Quality Scale**.

### Opción A: Vía HACS (Recomendado)
1. En Home Assistant, abre **HACS** $\rightarrow$ **Integraciones** $\rightarrow$ Menú superior de 3 puntos $\rightarrow$ **Repositorios personalizados**.
2. Añade este repositorio local o URL de GitHub con categoría **Integración**.
3. Haz clic en **Descargar** y reinicia Home Assistant.

### Opción B: Copia Directa a tu Servidor Home Assistant
Copia la carpeta `custom_components/bbva_fondos` a la carpeta `config/custom_components/` de tu servidor Home Assistant:
```bash
# Ejemplo si tu Home Assistant está en la misma red local
scp -r custom_components/bbva_fondos ricardom@192.168.1.20:/home/homeassistant/.homeassistant/custom_components/
```

### Configuración en la UI de Home Assistant
1. Ve a **Ajustes** $\rightarrow$ **Dispositivos y Servicios** $\rightarrow$ **Añadir Integración**.
2. Busca **BBVA México Fondos de Inversión**.
3. Selecciona tu modo preferido:
   - **Descarga directa de PDF (Recomendado, autónomo)**: Home Assistant descarga y parsea el PDF de forma autónoma sin necesidad de servicios externos.
   - **Conectar a servicio REST**: Se conecta a la API local (`http://localhost:8088`).
4. Indica los fondos a monitorear (ej. `BBVALIQ:B, BBVARV:B, BBVAGUB:C`).

### Tarjetas Lovelace Listas para Usar
Revisa [`docs/lovelace_dashboard.yaml`](./docs/lovelace_dashboard.yaml) para copiar y pegar tarjetas prediseñadas con gráficos históricos, precios actuales y botones de sincronización manual.

---

## 📡 Contrato de la Interfaz (API Contract)

La descripción formal de la interfaz se encuentra documentada a detalle en [`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md) y en la especificación [`openapi.json`](./openapi.json).

### Resumen de Endpoints:
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Estado del servicio, versión y conteo de fondos y series. |
| `GET` | `/api/v1/filters` | Segmentos de clientes y categorías disponibles. |
| `GET` | `/api/v1/funds` | Lista paginada de fondos con filtros por segmento, categoría y texto. |
| `GET` | `/api/v1/funds/{ticker}` | Detalle de todas las series de un fondo (mínimos, calificaciones, último precio). |
| `GET` | `/api/v1/funds/{ticker}/{series}` | Detalle individual de una serie específica. |
| `GET` | `/api/v1/funds/{ticker}/{series}/history` | Historial de precios y rendimientos en serie de tiempo. |
| `POST`| `/api/v1/sync` | Dispara la descarga del PDF y actualización de la base de datos. |

---

## 🐳 Despliegue con Docker

El repositorio incluye un contenedor optimizado multi-stage y `docker-compose.yml`:

```bash
docker compose up -d --build
```

Comprueba el estado:
```bash
docker compose ps
curl http://localhost:8088/api/v1/health
```

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una suite completa de pruebas unitarias y de integración con `pytest`:
```bash
pytest -v
```

Resultado:
- `test_parser_with_sample_pdf`: Extracción precisa de fechas, calificaciones, porcentajes y precios de todas las series.
- `test_sqlite_pragmas_and_schema`: Verificación de WAL mode, claves foráneas e índices.
- `test_repository_upsert_and_query`: Inserciones idempotentes y consultas relacionales.
- `test_api.py`: Integración completa de endpoints, envoltura estándar y manejo de errores.
