from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.base.config.settings import settings


class AppServer(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
        if not origins:
            origins = ["*"]
        self.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=origins != ["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
