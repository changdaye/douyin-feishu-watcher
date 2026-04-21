from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler


class SchedulerRunner:
    def __init__(self, *, interval_minutes: int, job, startup_callback=None) -> None:
        self.interval_minutes = interval_minutes
        self.job = job
        self.startup_callback = startup_callback

    def run_once(self) -> None:
        self.job()

    def serve(self) -> None:
        scheduler = BlockingScheduler()
        scheduler.add_job(self.job, "interval", minutes=self.interval_minutes, max_instances=1)
        if self.startup_callback is not None:
            try:
                self.startup_callback()
            except Exception as exc:  # pragma: no cover - defensive logging path
                print(f"startup_notification_failed={exc}")
        scheduler.start()
