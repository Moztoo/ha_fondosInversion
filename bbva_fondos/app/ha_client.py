"""Home Assistant REST API Client for Notifications and Update Signals.

Conforms to ha-server and mqtt-notify standards.
Dispatches push notifications to specified Home Assistant devices and fires events
onto the Home Assistant bus.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger("bbva_fondos.ha_client")

class HomeAssistantClient:
    """Dispatches notifications and signals to Home Assistant Core."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        notify_device: Optional[str] = None,
    ):
        self.token = token if token is not None else settings.HA_TOKEN
        url = base_url or settings.HA_URL or "http://192.168.1.20:8123/api"
        self.base_url = url.rstrip("/")
        self.notify_device = (
            notify_device if notify_device is not None else settings.NOTIFY_DEVICE
        ).strip()

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def normalize_service_name(self, device: str) -> str:
        """Strip notify. prefix if present for direct service endpoint."""
        clean = device.strip()
        if clean.startswith("notify."):
            clean = clean[len("notify."):]
        return clean

    def fire_event(self, event_name: str, event_data: Dict[str, Any]) -> bool:
        """Fire a Home Assistant event (signal) via /api/events/{event_name}."""
        if not self.base_url:
            logger.warning("No Home Assistant URL configured; skipping event broadcast.")
            return False

        endpoint = f"{self.base_url}/events/{event_name}"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(endpoint, json=event_data, headers=self._get_headers())
                if res.status_code in (200, 201):
                    logger.info("Fired Home Assistant signal event '%s' successfully.", event_name)
                    return True
                else:
                    logger.warning(
                        "Failed to fire Home Assistant event '%s': HTTP %d %s",
                        event_name, res.status_code, res.text
                    )
                    return False
        except Exception as e:
            logger.warning("Error firing Home Assistant event '%s': %s", event_name, e)
            return False

    def send_notification(
        self,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        target_device: Optional[str] = None,
    ) -> bool:
        """Call Home Assistant notify service for the configured device."""
        device = target_device if target_device is not None else self.notify_device
        if not device or device.lower() in ("none", "disabled", "false", ""):
            logger.info("Notification skipped: notify_device is disabled or empty.")
            return False

        service_name = self.normalize_service_name(device)
        endpoint = f"{self.base_url}/services/notify/{service_name}"

        payload: Dict[str, Any] = {
            "title": title,
            "message": message,
        }
        if data:
            payload["data"] = data

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(endpoint, json=payload, headers=self._get_headers())
                if res.status_code in (200, 201):
                    logger.info("Push notification delivered via '%s' successfully.", service_name)
                    return True
                else:
                    # Fallback to general notify.notify if specific device endpoint failed
                    if service_name != "notify":
                        logger.warning(
                            "Notify service '%s' returned HTTP %d. Retrying with 'notify.notify' fallback...",
                            service_name, res.status_code
                        )
                        fallback_endpoint = f"{self.base_url}/services/notify/notify"
                        fb_res = client.post(fallback_endpoint, json=payload, headers=self._get_headers())
                        if fb_res.status_code in (200, 201):
                            logger.info("Push notification delivered via fallback 'notify' successfully.")
                            return True
                    logger.warning(
                        "Failed to call notify service '%s': HTTP %d %s",
                        service_name, res.status_code, res.text
                    )
                    return False
        except Exception as e:
            logger.warning("Error sending notification to Home Assistant: %s", e)
            return False

    def notify_favorites_update(
        self,
        favorites: List[Dict[str, Any]],
        report_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Format and dispatch notification and event signal for favorited funds."""
        if not favorites:
            logger.info("No favorite funds marked; skipping notification.")
            return {"sent": False, "reason": "no_favorites", "favorites_count": 0}

        date_str = report_date or "Día Actual"
        lines = []
        for fav in favorites:
            ticker = fav.get("ticker", "")
            series = fav.get("series", "")
            rend_mes = fav.get("rendimiento_mes")
            precio = fav.get("precio")

            if rend_mes is not None:
                sign = "+" if rend_mes > 0 else ""
                mes_str = f"{sign}{rend_mes:.2f}% (mes)"
            else:
                mes_str = "N/D (mes)"

            precio_str = f"${precio:.4f}" if precio is not None else ""
            lines.append(f"• {ticker} ({series}): {mes_str} | {precio_str}".strip())

        title = "📈 BBVA Fondos · Rendimientos"
        body = f"Actualización oficial ({date_str}):\n" + "\n".join(lines)

        notification_data = {
            "channel": "Others",
            "group": "others",
            "notification_icon": "mdi:chart-line",
            "tag": "bbva_fondos_update",
        }

        # 1. Fire signal event into Home Assistant bus
        event_payload = {
            "report_date": report_date,
            "favorites_count": len(favorites),
            "favorites": [
                {
                    "ticker": fav.get("ticker"),
                    "series": fav.get("series"),
                    "name": fav.get("fund_name"),
                    "category": fav.get("category"),
                    "segment": fav.get("segment"),
                    "rendimiento_mes": fav.get("rendimiento_mes"),
                    "rendimiento_diario": fav.get("rendimiento_diario"),
                    "rendimiento_1a": fav.get("rendimiento_1a"),
                    "precio": fav.get("precio"),
                    "report_date": fav.get("report_date"),
                }
                for fav in favorites
            ],
        }
        event_ok = self.fire_event("bbva_fondos_updated", event_payload)

        # 2. Send push notification to target device
        notify_ok = self.send_notification(
            title=title,
            message=body,
            data=notification_data,
        )

        return {
            "sent": notify_ok,
            "event_fired": event_ok,
            "device": self.notify_device,
            "favorites_count": len(favorites),
            "summary": body,
        }
