import os


os.environ.setdefault("SERVICE_VERSION", "test-version")
os.environ.setdefault("SERVICE_ENVIRONMENT", "test")


def pytest_addoption(parser):
    parser.addoption(
        "--run-notification-api-benchmark",
        action="store_true",
        default=False,
        help="Run the isolated MongoDB API benchmark for notification-service.",
    )
    parser.addoption("--notification-benchmark-samples", type=int, default=30)
    parser.addoption("--notification-benchmark-warmup", type=int, default=3)
    parser.addoption(
        "--notification-benchmark-artifact-dir",
        default="tests/tmp/reports/notification-api-benchmark",
    )
    parser.addoption("--notification-benchmark-preset", default="smoke")
