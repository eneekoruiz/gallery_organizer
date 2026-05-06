from core.metrics import Metrics


def test_metrics_singleton():
    m1 = Metrics()
    m2 = Metrics()
    assert m1 is m2


def test_metrics_increment():
    m = Metrics()
    initial = m.get("files_processed")
    m.increment("files_processed", 5)
    assert m.get("files_processed") == initial + 5


def test_metrics_set():
    m = Metrics()
    m.set("last_operation_duration", 42.5)
    assert m.get("last_operation_duration") == 42.5


def test_metrics_record_cleanup():
    m = Metrics()
    initial_runs = m.get("maintenance_runs")
    m.record_cleanup(10, 5, 3.5)
    assert m.get("maintenance_runs") == initial_runs + 1
    assert m.get("cleanup_orphans_total") >= 10
    assert m.get("cleanup_links_total") >= 5
    assert m.get("last_maintenance_duration_seconds") == 3.5


def test_metrics_record_error():
    m = Metrics()
    initial_errors = m.get("maintenance_errors")
    m.record_maintenance_error()
    assert m.get("maintenance_errors") == initial_errors + 1


def test_metrics_timer_context():
    m = Metrics()
    with m.timer("test_operation"):
        pass
    assert m.get("last_test_operation_seconds") > 0


def test_metrics_get_all():
    m = Metrics()
    all_metrics = m.get_all()
    assert isinstance(all_metrics, dict)
    assert "maintenance_runs" in all_metrics
