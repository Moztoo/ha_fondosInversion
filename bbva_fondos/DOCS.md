# BBVA México · Fondos de Inversión (Home Assistant App)

Esta aplicación para Home Assistant descarga automáticamente los **"Anaquel con Rendimientos Históricos del Día Actual"** de BBVA México, parsea todas las columnas y almacena los datos en una base de datos SQLite histórica.

## Características
- **Todas las columnas del Anaquel extraídas**: Ticker, Serie, Segmento, Categoría, Mínimo de Inversión, Calificación, Rendimientos (Diario, Semanal, Mes, Año, 1A, 2A) y Precio.
- **Fondos Favoritos**: Marca con una estrella ★ cualquier serie de cualquier fondo para tener acceso rápido en la pestaña *★ Favoritos*.
- **Alertas y Señales Automáticas a Home Assistant**: Al caer la actualización del Anaquel, se toman los fondos favoritos y se envía una notificación a tu dispositivo con el rendimiento mensual y precio, además de disparar el evento `bbva_fondos_updated` en el bus de Home Assistant.
- **Sincronización Automática Diaria a las 10:00 PM**: Descarga de fondo automatizada sin intervención manual.
- **Seguimiento Especializado**: Rastreo de todos los fondos de deuda de personas físicas de todas las categorías con un solo clic.
- **Panel de Control Integrado (Ingress)**: Disponible directamente en la barra lateral de Home Assistant sin salir de la interfaz.
- **Gráficas Históricas con Chart.js**: Visualiza la evolución del valor por título y rendimientos a lo largo del tiempo.
- **API REST con Contrato Formal**: Disponible en el puerto `8088` para consultar desde otras integraciones o scripts.

## Configuración
En la pestaña de **Configuración** del complemento:
```yaml
auto_sync_enabled: true
auto_sync_time: "22:00"
auto_sync_on_startup: true
notify_device: "mobile_app_sevastopol"
segment: "Personas Físicas"
```
- `notify_device`: Nombre del servicio o dispositivo en Home Assistant al que llegarán las notificaciones push (ej. `mobile_app_sevastopol`, `notify.notify` o dejar vacío para desactivar).

## Instalación
1. Ve a **Ajustes** $\rightarrow$ **Complementos** $\rightarrow$ **Tienda de Complementos**.
2. Haz clic en los tres puntos superiores $\rightarrow$ **Repositorios**.
3. Agrega la URL del repositorio: `https://github.com/Moztoo/ha_fondosInversion`
4. Busca **BBVA Fondos de Inversión** y haz clic en **Instalar**.
5. Activa la opción **Mostrar en la barra lateral** e inicia el complemento.
