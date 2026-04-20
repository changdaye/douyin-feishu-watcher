from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler


class SchedulerRunner:
    def __init__(self, *, interval_minutes: int, job) -> None:
        self.interval_minutes = interval_minutes
        self.job = job

    def run_once(self) -> None:
        self.job()

    def serve(self) -> None:
        scheduler = BlockingScheduler()
        scheduler.add_job(self.job, "interval", minutes=self.interval_minutes, max_instances=1)
        scheduler.start()
