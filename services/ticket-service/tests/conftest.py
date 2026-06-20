import os


os.environ.setdefault("SERVICE_VERSION", "test-version")
os.environ.setdefault("SERVICE_ENVIRONMENT", "test")


def pytest_addoption(parser):
    parser.addoption(
        "--run-ticket-api-benchmark",
        action="store_true",
        default=False,
        help="Run the isolated PostgreSQL API benchmark for ticket-service.",
    )
    parser.addoption("--ticket-benchmark-samples", type=int, default=30)
    parser.addoption("--ticket-benchmark-warmup", type=int, default=3)
    parser.addoption(
        "--ticket-benchmark-artifact-dir",
        default="tests/tmp/reports/ticket-api-benchmark",
    )
    parser.addoption("--ticket-benchmark-preset", default="smoke")
