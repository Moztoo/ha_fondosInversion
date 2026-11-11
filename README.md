# BBVA México · Fondos de Inversión (Home Assistant App)

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![SQLite WAL](https://img.shields.io/badge/SQLite-WAL%20Hardened-003B57.svg)](https://sqlite.org)
[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-App%20%2F%20Add--on-41BDF5.svg)](https://www.home-assistant.io/)
[![Ingress Ready](https://img.shields.io/badge/Home%20Assistant-Ingress%20Sidebar-blueviolet.svg)](https://www.home-assistant.io/blog/2019/04/15/hassio-ingress/)

Aplicación oficial para Home Assistant y microservicio autónomo que descarga y procesa diariamente los **"Anaquel con Rendimientos Históricos del Día Actual"** de los fondos de inversión de BBVA México. 

Extrae y almacena **todas las columnas oficiales** en una base de datos histórica SQLite y proporciona una interfaz web financiera accesible directamente desde la barra lateral de Home Assistant (Ingress).

---

## ✨ Características Principales

1. **Extracción Completa de Todas las Columnas Oficiales**:
   - `Fondo` (Ticker ej. `BBVALIQ`, `BBVAGUB`, `BBVAPZO`)
   - `Serie` (`B`, `C`, `P`, `PV`, `UHN`, `PF1`, etc.)
   - `Segmento` (`Personas Físicas`, `Personas Morales`, `Colaboradores BBVA`)
   - `Categoría` (`Fondos de Deuda`, `Fondos de Liquidez en Divisas`, `Fondos de Estrategias`, etc.)
   - `Mínimo de Inversión` (MXN)
   - `Calificación` (`AAA/1`, `AAA/2`, `AA/3`, `AA/4`, etc.)
   - `Rendimiento Diario` (%)
   - `Rendimiento Semanal` (%)
   - `Rendimiento Acumulado Mes` (%)
   - `Rendimiento Acumulado Año` (%)
   - `Rendimiento 1 Año` (%)
   - `Rendimiento 2 Años` (%)
   - `Precio Actual por Título` (MXN)
   - `Fecha de Reporte` (`YYYY-MM-DD`)

2. **Rastreo Especializado para Deuda de Personas Físicas**:
   - Filtro dedicado en un clic: **⭐ Deuda P. Físicas**, que agrupa todas las categorías de deuda (corto plazo, liquidez diaria, mediano plazo, gubernamentales, corporativas).

3. **App Nativa para Home Assistant (Add-on con Ingress)**:
   - Se instala directamente desde la **Tienda de Complementos** de Home Assistant.
   - Aparece en el menú lateral de Home Assistant sin necesidad de extensiones externas ni HACS.
   - Almacena su base de datos de manera persistente en `/data/bbva_fondos.db`.

4. **API REST con Contrato Formal OpenAPI 3.1**:
   - Expone endpoints estándar documentados en [`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md) y [`openapi.json`](./openapi.json).
   - Compatible con cualquier otro servicio, script en Python o automatización que requiera consultar precios o rendimientos.

---

## 📱 Instalación en Home Assistant como App (Add-on)

1. En tu Home Assistant, dirígete a:
   **Ajustes** $\rightarrow$ **Complementos** $\rightarrow$ **Tienda de Complementos** (botón inferior derecho).
2. Haz clic en el menú de tres puntos superior derecho $\rightarrow$ **Repositorios**.
3. Añade la URL del repositorio:
   ```text
   https://github.com/Moztoo/ha_fondosInversion
   ```
4. Recarga la página y busca en la lista el complemento **BBVA Fondos de Inversión**.
5. Haz clic en **Instalar**.
6. Activa las opciones:
   - ✅ **Iniciar al arrancar**
   - ✅ **Vigilar**
   - ✅ **Mostrar en la barra lateral**
7. Haz clic en **Iniciar** y luego en **Abrir la interfaz web** o accede directamente desde el icono en la barra lateral de Home Assistant.

---

## 💻 Ejecución Local Standalone

Si deseas ejecutarlo de forma independiente en tu computadora o servidor:

```bash
cd /home/ricardom/ha_fondosInversion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload
```

- **Dashboard Web**: [http://localhost:8088/](http://localhost:8088/)
- **Documentación Swagger**: [http://localhost:8088/docs](http://localhost:8088/docs)
- **Contrato OpenAPI**: [http://localhost:8088/api/v1/contract](http://localhost:8088/api/v1/contract)

---

## 📡 Endpoints de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/v1/series` | Lista completa de series con **todas las columnas** (precios, mínimos, calificaciones, rendimientos). |
| `GET` | `/api/v1/funds` | Lista agrupada por fondos. |
| `GET` | `/api/v1/funds/{ticker}/{series}/history` | Historial de precios y rendimientos para graficar o analizar. |
| `GET` | `/api/v1/filters` | Lista de categorías y segmentos disponibles. |
| `GET` | `/api/v1/health` | Estado del servicio y estadísticas de la base de datos. |
| `POST`| `/api/v1/sync` | Forzar la descarga y procesamiento del último PDF oficial. |

Consulta [`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md) para ver la especificación completa y ejemplos en cURL y Python.

---

## 🐳 Despliegue con Docker

```bash
docker compose up -d --build
```
