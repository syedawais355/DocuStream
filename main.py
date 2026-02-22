import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from config import get_settings
from logger import setup_logger, get_logger
from jobs import get_job_store
from processor import get_task_processor, cleanup_task_processor
from routes import router
from middleware import StructuredLoggingMiddleware
from exceptions import DocustreamError

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    logger.info("DOCUSTREAM starting up | version=1.0.0")
    
    job_store = get_job_store()
    await job_store.load()
    logger.info("Job store loaded from disk")
    
    task_processor = await get_task_processor()
    logger.info("Task processor started")
    
    yield
    
    logger.info("DOCUSTREAM shutting down")
    await cleanup_task_processor()
    logger.info("Task processor stopped")


app = FastAPI(title="DOCUSTREAM", version="1.0.0", lifespan=lifespan)
app.add_middleware(StructuredLoggingMiddleware)
app.include_router(router)


@app.exception_handler(DocustreamError)
async def docustream_exception_handler(request, exc: DocustreamError):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
