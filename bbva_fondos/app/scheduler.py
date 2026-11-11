"""Background scheduler for automated daily synchronization of BBVA Fondos."""
import asyncio
from datetime import datetime, date
import logging
from typing import Optional

from app.config import settings
from app.service import FondosService

logger = logging.getLogger("bbva_fondos.scheduler")

class BackgroundSyncScheduler:
    """Manages scheduled daily synchronization and initial startup sync."""

    def __init__(self, service: Optional[FondosService] = None):
        self.service = service or FondosService()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._last_synced_date: Optional[date] = None

    async def start(self):
        """Start the background scheduler task."""
        if not settings.AUTO_SYNC_ENABLED:
            logger.info("Automatic scheduled sync is disabled in configuration.")
            return

        self.is_running = True
        logger.info(
            "Starting Background Sync Scheduler: Target daily time = %s (Startup sync = %s)",
            settings.AUTO_SYNC_TIME,
            settings.AUTO_SYNC_ON_STARTUP,
        )
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Gracefully stop the background scheduler."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background Sync Scheduler stopped.")

    async def _run_loop(self):
        """Scheduler loop checking target time every 30 seconds."""
        # 1. Check if startup sync is required (e.g. empty database)
        if settings.AUTO_SYNC_ON_STARTUP:
            try:
                health = self.service.get_health()
                if health.total_snapshots == 0:
                    logger.info("Database is empty on startup. Triggering initial automatic sync...")
                    res = await asyncio.to_thread(self.service.sync_data)
                    logger.info("Initial startup sync completed: %s", res.message)
                    self._last_synced_date = date.today()
            except Exception as e:
                logger.error("Error during initial startup sync: %s", e)

        # 2. Main periodic loop
        while self.is_running:
            try:
                now = datetime.now()
                current_hh_mm = now.strftime("%H:%M")
                today = now.date()

                # Check if it matches target time and hasn't synced today at this slot
                if current_hh_mm == settings.AUTO_SYNC_TIME:
                    if self._last_synced_date != today:
                        logger.info(
                            "Scheduled auto-sync trigger activated at %s (Daily 10:00 PM / %s)",
                            current_hh_mm,
                            settings.AUTO_SYNC_TIME,
                        )
                        res = await asyncio.to_thread(self.service.sync_data)
                        logger.info("Scheduled auto-sync finished: %s", res.message)
                        self._last_synced_date = today

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)
                await asyncio.sleep(60)

scheduler = BackgroundSyncScheduler()
