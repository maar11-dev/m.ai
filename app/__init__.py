from fastapi import FastAPI
from .router import router


def create_app() -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    return application
