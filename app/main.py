from contextlib import asynccontextmanager
from fastapi import FastAPI
from .core import Database, settings
from .routers.products import router as products_router
from .routers.skincare import router as skincare_router
import ngrok

@asynccontextmanager
async def lifespan(app: FastAPI):
    ngrok.set_auth_token(settings.NGROK_AUTH_TOKEN)
    public_url = ngrok.connect(addr=8000, domain="cute-weasel-locally.ngrok-free.app", proto="http")
    Database.connect()
    yield
    Database.disconnect()


def create_app() -> FastAPI:
    """Application factory pattern"""
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan
    )
    

    app.include_router(products_router, prefix=settings.API_PREFIX)
    app.include_router(skincare_router, prefix=settings.API_PREFIX)
    
    
    return app


app = create_app()
