from fastapi import FastAPI
from observability import (
    ObservabilityConfig,
    RequestIdMiddleware,
    configure_process_logging,
    configure_process_tracing,
    create_request_log_middleware,
    instrument_fastapi_app,
    request_id_middleware_options,
)


def configure_app_observability(app: FastAPI, config: ObservabilityConfig) -> None:
    configure_process_logging()
    configure_process_tracing(config)
    instrument_fastapi_app(app)
    app.add_middleware(RequestIdMiddleware, **request_id_middleware_options())
    app.middleware("http")(create_request_log_middleware(config))
