import main


def test_run_once_calls_runner(monkeypatch):
    called = {"count": 0}

    class FakeRunner:
        def run_once(self):
            called["count"] += 1

        def serve(self):
            raise AssertionError("serve should not be called")

    monkeypatch.setattr(main, "build_runner", lambda: FakeRunner())

    exit_code = main.main(["run-once"])

    assert exit_code == 0
    assert called["count"] == 1
