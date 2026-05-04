from app.workers import worker_main


def test_worker_module_has_main():
    assert callable(worker_main.main)
