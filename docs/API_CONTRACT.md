# Contrato de Interfaz y Especificación de API · BBVA Fondos de Inversión

Este documento define formalmente la especificación y el contrato de interfaz del servicio **BBVA Fondos de Inversión**, permitiendo a cualquier sistema externo (Home Assistant, scripts de automatización, microservicios contables o plataformas de analítica financiera) consumir, consultar y sincronizar los rendimientos históricos de los fondos de inversión de BBVA México.

---

## 1. Principios de Diseño de la Interfaz

El servicio implementa una arquitectura RESTful bajo las directrices del skill `backend`:
- **Protocolo**: HTTP/1.1 y HTTP/2 sobre JSON (`Content-Type: application/json`).
- **Envoltura Estándar de Éxito (`StandardResponse`)**: Todas las respuestas exitosas devuelven un objeto JSON con la llave `success: true`, los datos en `data`, y opcionalmente metadatos y paginación en `meta`.
- **Envoltura Estándar de Error (`StandardErrorResponse`)**: Todos los errores HTTP devuelven un objeto JSON consistente con `success: false` y un objeto `error` que incluye código legible por máquina (`code`) y mensaje explicativo (`message`).
- **Idempotencia**: Las consultas son seguras y reproducibles (`GET`), mientras que la sincronización (`POST /api/v1/sync`) es idempotente mediante el control de fechas en base de datos.
- **Tipado Estricto**: Basado en especificación **OpenAPI 3.1** con esquemas Pydantic v2.

---

## 2. Envoltorios de Mensajería (Payload Envelopes)

### Envoltorio de Éxito
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 50,
    "total": 158,
    "filters": {
      "segment": "Personas Físicas",
      "category": null,
      "search": "BBVALIQ"
    }
  }
}
```

### Envoltorio de Error
```json
{
  "success": false,
  "error": {
    "code": "FUND_NOT_FOUND",
    "message": "No fund series found matching ticker 'XYZ'.",
    "details": null
  }
}
```

---

## 3. Catálogo de Endpoints

### 3.1 `GET /api/v1/health`
Monitoreo de estado operativo del servicio y métricas de persistencia.

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "total_funds": 158,
    "total_series": 427,
    "total_snapshots": 492,
    "last_report_date": "2026-11-10",
    "last_sync_time": "2026-11-10 19:30:33"
  }
}
```

---

### 3.2 `GET /api/v1/filters`
Obtiene las opciones únicas de filtros disponibles (segmentos de cliente y categorías de fondos).

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": {
    "segments": [
      "Colaboradores BBVA",
      "Personas Físicas",
      "Personas Morales"
    ],
    "categories": [
      "Fondos Ciclos de Vida",
      "Fondos de Deuda",
      "Fondos de Estrategias",
      "Fondos de Liquidez en Divisas",
      "Fondos de MultiActivos",
      "Fondos de Renta Variable"
    ]
  }
}
```

---

### 3.3 `GET /api/v1/series`
Consulta exhaustiva de todas las series individuales de fondos con **todas las columnas** extraídas del Anaquel (precios, montos mínimos, calificaciones y rendimientos en todos los horizontes temporales).

- **Parámetros de Consulta (Query Params)**:
  | Parámetro | Tipo | Obligatorio | Descripción |
  | :--- | :--- | :--- | :--- |
  | `segment` | `string` | No | Filtro por segmento (`Personas Físicas`, `Personas Morales`, `Colaboradores BBVA`) |
  | `category` | `string` | No | Filtro por categoría exacta del fondo |
  | `is_debt_only` | `boolean` | No | Si es `true`, filtra todos los fondos de deuda y liquidez excluyendo renta variable |
  | `search` | `string` | No | Búsqueda por ticker (ej. `BBVALIQ`) o serie |
  | `sort_by` | `string` | No | Columna de ordenamiento (`ticker`, `precio`, `rendimiento_1a`, `rendimiento_diario`, etc.) |
  | `order` | `string` | No | Dirección (`ASC` o `DESC`, predeterminado `ASC`) |
  | `page` | `integer` | No | Número de página (predeterminado: `1`) |
  | `limit` | `integer` | No | Elementos por página (predeterminado: `50`, máx: `500`) |

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": [
    {
      "ticker": "BBVALIQ",
      "series": "B",
      "segment": "Personas Físicas",
      "category": "Fondos de Deuda",
      "minimo_inversion": 0.0,
      "calificacion": "AAA/1",
      "rendimiento_diario": 4.40,
      "rendimiento_semanal": 4.21,
      "rendimiento_mes": 2.93,
      "rendimiento_anio": 4.26,
      "rendimiento_1a": 4.39,
      "rendimiento_2a": 5.67,
      "precio": 22.009366,
      "report_date": "2026-11-10"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 50,
    "total": 492
  }
}
```

---

### 3.4 `GET /api/v1/funds`
Consulta paginada del catálogo de fondos con sus métricas más recientes y series asociadas.

- **Parámetros de Consulta (Query Params)**:
  | Parámetro | Tipo | Obligatorio | Descripción |
  | :--- | :--- | :--- | :--- |
  | `segment` | `string` | No | Filtro por segmento (`Personas Físicas`, `Personas Morales`, `Colaboradores BBVA`) |
  | `category` | `string` | No | Filtro por categoría exacta del fondo |
  | `search` | `string` | No | Búsqueda por ticker (ej. `BBVALIQ`) o nombre |
  | `page` | `integer` | No | Número de página (predeterminado: `1`) |
  | `limit` | `integer` | No | Elementos por página (predeterminado: `50`, máx: `500`) |

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": [
    {
      "ticker": "BBVALIQ",
      "name": "Fondo BBVALIQ",
      "category": "Fondos de Deuda",
      "segment": "Personas Físicas",
      "series_list": ["B", "C", "GB", "P", "PV", "UHN"],
      "latest_price": 22.009366,
      "latest_rendimiento_1a": 4.39,
      "latest_report_date": "2026-11-10"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 50,
    "total": 1,
    "filters": {
      "segment": "Personas Físicas",
      "category": null,
      "search": "BBVALIQ"
    }
  }
}
```

---

### 3.4 `GET /api/v1/funds/{ticker}`
Consulta a detalle todas las series registradas para un ticker específico, incluyendo montos mínimos de inversión, calificaciones de riesgo y el último snapshot de rendimientos y precios.

- **Parámetros de Ruta**:
  - `ticker` (`string`, ej. `BBVALIQ`, `BBVARV`).
- **Parámetros de Consulta**:
  - `segment` (`string`, opcional): Filtra solo las series de ese segmento.

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": [
    {
      "id": 7,
      "ticker": "BBVALIQ",
      "series": "B",
      "segment": "Personas Físicas",
      "category": "Fondos de Deuda",
      "minimo_inversion": 0.0,
      "calificacion": "AAA/1",
      "latest_snapshot": {
        "report_date": "2026-11-10",
        "rendimiento_diario": 4.40,
        "rendimiento_semanal": 4.21,
        "rendimiento_mes": 2.93,
        "rendimiento_anio": 4.26,
        "rendimiento_1a": 4.39,
        "rendimiento_2a": 5.67,
        "precio": 22.009366
      },
      "history_count": 1
    }
  ],
  "meta": {
    "total": 1
  }
}
```

---

### 3.5 `GET /api/v1/funds/{ticker}/{series}`
Detalle de una serie específica.

- **Parámetros de Ruta**:
  - `ticker` (`string`): Ticker del fondo.
  - `series` (`string`): Serie a consultar (ej. `B`, `C`, `PV`).
- **Respuesta (200 OK)**: Objeto `FundSeriesDetail` individual.
- **Respuesta (404 Not Found)**: Error si el ticker o la serie no existen.

---

### 3.6 `GET /api/v1/funds/{ticker}/{series}/history`
Línea temporal histórica de precios y rendimientos de la serie, ideal para graficar curvas de rentabilidad o alimentar modelos de inversión.

- **Parámetros de Consulta**:
  | Parámetro | Tipo | Obligatorio | Descripción |
  | :--- | :--- | :--- | :--- |
  | `segment` | `string` | No | Segmento del cliente |
  | `from_date`| `string` | No | Fecha inicial (`YYYY-MM-DD`) |
  | `to_date` | `string` | No | Fecha final (`YYYY-MM-DD`) |
  | `limit` | `integer` | No | Máximo de registros históricos (predeterminado: `365`) |

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": [
    {
      "report_date": "2026-11-10",
      "rendimiento_diario": 4.40,
      "rendimiento_semanal": 4.21,
      "rendimiento_mes": 2.93,
      "rendimiento_anio": 4.26,
      "rendimiento_1a": 4.39,
      "rendimiento_2a": 5.67,
      "precio": 22.009366
    }
  ],
  "meta": {
    "total": 1
  }
}
```

---

### 3.7 `POST /api/v1/sync`
Inicia el proceso automatizado de scraping:
1. Conecta con el repositorio web de BBVA México.
2. Descarga el PDF del "Anaquel con Rendimientos Históricos del Día Actual".
3. Extrae la fecha de elaboración y los ~500 registros de fondos y series.
4. Realiza una inserción/actualización idempotente en la base de datos SQLite WAL.

- **Respuesta (200 OK)**:
```json
{
  "success": true,
  "data": {
    "success": true,
    "status": "SUCCESS",
    "report_date": "2026-11-10",
    "total_parsed": 492,
    "new_snapshots_inserted": 492,
    "funds_updated": 158,
    "duration_seconds": 3.84,
    "message": "Successfully synced 492 records for date 2026-11-10 (158 funds added, 492 snapshots saved) in 3.84s"
  }
}
```

---

## 4. Códigos de Error del Contrato

| Código HTTP | Error Code | Descripción |
| :--- | :--- | :--- |
| `400 Bad Request` | `VALIDATION_ERROR` | Parámetros de consulta o ruta no válidos. |
| `404 Not Found` | `FUND_NOT_FOUND` | El ticker de fondo solicitado no existe en la base de datos. |
| `404 Not Found` | `SERIES_NOT_FOUND` | La serie especificada no existe para dicho ticker. |
| `502 Bad Gateway` | `SYNC_FAILED` | Error al descargar o parsear el PDF remoto de BBVA. |
| `500 Server Error` | `INTERNAL_SERVER_ERROR` | Excepción no controlada en el servidor. |

---

## 5. Ejemplos de Consumo Externo

### 5.1 En cURL
```bash
# Consultar fondos de liquidez
curl -s -X GET "http://localhost:8088/api/v1/funds?search=BBVALIQ" | jq .

# Obtener historial de precios de la serie B
curl -s -X GET "http://localhost:8088/api/v1/funds/BBVALIQ/B/history" | jq .

# Disparar sincronización manual
curl -s -X POST "http://localhost:8088/api/v1/sync" | jq .
```

### 5.2 En Python (Microservicio o Script)
```python
import httpx

API_BASE = "http://localhost:8088/api/v1"

def get_fund_current_price(ticker: str, series: str = "B") -> float:
    resp = httpx.get(f"{API_BASE}/funds/{ticker}/{series}")
    resp.raise_for_status()
    payload = resp.json()
    if payload["success"]:
        return payload["data"]["latest_snapshot"]["precio"]
    raise ValueError(payload["error"]["message"])

price = get_fund_current_price("BBVALIQ", "B")
print(f"Precio actual BBVALIQ (B): ${price:.4f}")
```
