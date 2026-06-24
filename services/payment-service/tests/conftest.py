import os


os.environ.setdefault("SERVICE_VERSION", "test-version")
os.environ.setdefault("SERVICE_ENVIRONMENT", "test")


def pytest_addoption(parser):
    parser.addoption(
        "--run-payment-api-benchmark",
        action="store_true",
        default=False,
        help="Run the isolated PostgreSQL API benchmark for payment-service.",
    )
    parser.addoption("--payment-benchmark-samples", type=int, default=30)
    parser.addoption("--payment-benchmark-warmup", type=int, default=3)
    parser.addoption(
        "--payment-benchmark-artifact-dir",
        default="tests/tmp/reports/payment-api-benchmark",
    )
    parser.addoption("--payment-benchmark-preset", default="smoke")
