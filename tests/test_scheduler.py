from app.scheduler import SchedulerRunner


def test_scheduler_runner_calls_startup_callback_before_start(monkeypatch):
    events = []

    class FakeScheduler:
        def add_job(self, job, trigger, minutes, max_instances):
            events.append(("add_job", trigger, minutes, max_instances))

        def start(self):
            events.append(("start",))

    monkeypatch.setattr("app.scheduler.BlockingScheduler", lambda: FakeScheduler())

    runner = SchedulerRunner(
        interval_minutes=30,
        job=lambda: events.append(("job",)),
        startup_callback=lambda: events.append(("startup",)),
    )

    runner.serve()

    assert events == [
        ("add_job", "interval", 30, 1),
        ("startup",),
        ("start",),
    ]
