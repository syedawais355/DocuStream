from enum import Enum
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from jobs import get_job_store, JobStatus
from processor import get_document_processor
from storage import get_storage_manager
from dependencies import verify_api_key
from logger import get_logger
from exceptions import StorageError, JobNotFoundError

logger = get_logger()
router = APIRouter()


class DocumentFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"


@router.post("/jobs/submit")
async def submit_job(
    file: UploadFile = File(...),
    source_format: DocumentFormat = Form(...),
    target_format: DocumentFormat = Form(...),
    _: str = Depends(verify_api_key),
) -> dict:
    source = source_format.value
    target = target_format.value
    
    if source == target:
        logger.warning(f"Rejected job: source and target formats identical ({source})")
        raise HTTPException(status_code=400, detail="Source and target formats must differ")
    
    if not ((source == "docx" and target == "pdf") or (source == "pdf" and target == "docx")):
        logger.warning(f"Rejected job: unsupported conversion {source} -> {target}")
        raise HTTPException(status_code=400, detail="Unsupported conversion")
    
    job_store = get_job_store()
    storage = get_storage_manager()
    
    try:
        job_id = await job_store.create(source, target, file.filename)
        await storage.save_upload(job_id, file.filename, file)
        logger.info(f"Job {job_id}: created | file={file.filename} | {source}->{target}")
    except StorageError as e:
        logger.error(f"Job {job_id}: storage error | {str(e)}")
        raise HTTPException(status_code=413, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")
    
    doc_processor = await get_document_processor()
    queued = doc_processor.submit_conversion(job_id, file.filename, source, target)
    
    if not queued:
        logger.warning(f"Job {job_id}: task queue full")
        raise HTTPException(status_code=503, detail="Task queue is full, try again later")
    
    return {"job_id": job_id, "status": "PENDING"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, _: str = Depends(verify_api_key)) -> dict:
    job_store = get_job_store()
    record = await job_store.get(job_id)
    
    if not record:
        logger.warning(f"Job {job_id}: not found")
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": record.job_id,
        "status": record.status.value,
        "source_format": record.source_format,
        "target_format": record.target_format,
        "input_filename": record.input_filename,
        "output_file": record.output_file,
        "error": record.error,
        "created_at": record.created_at.isoformat(),
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }


@router.get("/jobs/{job_id}/download")
async def download_job(job_id: str, _: str = Depends(verify_api_key)) -> FileResponse:
    job_store = get_job_store()
    record = await job_store.get(job_id)
    
    if not record:
        logger.warning(f"Job {job_id}: download requested but not found")
        raise HTTPException(status_code=404, detail="Job not found")
    
    if record.status != JobStatus.SUCCESS:
        logger.warning(f"Job {job_id}: download requested but status is {record.status.value}")
        raise HTTPException(status_code=400, detail="Job has not completed successfully")
    
    if not record.output_file:
        logger.error(f"Job {job_id}: output_file not set")
        raise HTTPException(status_code=404, detail="Output file not found")
    
    output_path = Path(record.output_file)
    if not output_path.exists():
        logger.error(f"Job {job_id}: output file missing from disk | {output_path}")
        raise HTTPException(status_code=404, detail="Output file missing on disk")
    
    logger.info(f"Job {job_id}: download completed | {output_path.name}")
    
    return FileResponse(
        output_path,
        filename=output_path.name,
        media_type="application/octet-stream",
    )


@router.get("/jobs")
async def list_jobs(
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    _: str = Depends(verify_api_key),
) -> dict:
    job_store = get_job_store()
    jobs, total = await job_store.list(status, limit)
    
    logger.info(f"Listed jobs | total={total} | status={status or 'all'} | limit={limit}")
    
    return {
        "total": total,
        "jobs": [
            {
                "job_id": j.job_id,
                "status": j.status.value,
                "source_format": j.source_format,
                "target_format": j.target_format,
                "input_filename": j.input_filename,
                "created_at": j.created_at.isoformat(),
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/health")
async def health() -> dict:
    logger.debug("Health check requested")
    return {"status": "ok", "version": "1.0.0"}
