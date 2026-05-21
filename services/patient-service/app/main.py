from fastapi import FastAPI

from app import models
from app.config import settings
from app.database import engine
from app.observability import setup_request_logging
from app.routers import patients


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.service_name)
setup_request_logging(app, settings.service_name)
app.include_router(patients.router)


# Kubernetes probe와 로컬 확인에 사용하는 공개 헬스체크 API다.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
