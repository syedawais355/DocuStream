import asyncio
import logging
from pathlib import Path
from typing import Callable, Coroutine, Any
from converter import convert_docx_to_pdf, convert_pdf_to_docx
from jobs import get_job_store, JobStatus
from storage import get_storage_manager
from exceptions import ConversionError, StorageError
from config import get_settings
from logger import get_logger

logger = get_logger()


class AsyncTaskProcessor:
    def __init__(self, max_concurrent: int, max_queue_length: int):
        self.max_concurrent = max_concurrent
        self.max_queue_length = max_queue_length
        self.queue: asyncio.Queue | None = None
        self.semaphore: asyncio.Semaphore | None = None
        self.workers: list[asyncio.Task] = []
        self.running = False
    
    async def start(self) -> None:
        self.queue = asyncio.Queue(maxsize=self.max_queue_length)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.running = True
        
        for _ in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
    
    async def _worker(self) -> None:
        while self.running:
            try:
                coro_factory = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                async with self.semaphore:
                    await coro_factory()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker error: {type(e).__name__}")
    
    def queue_task(
        self, job_id: str, coro_factory: Callable[[], Coroutine[Any, Any, None]]
    ) -> bool:
        if self.queue is None or self.queue.full():
            return False
        try:
            self.queue.put_nowait(coro_factory)
            return True
        except asyncio.QueueFull:
            return False
    
    async def stop(self) -> None:
        self.running = False
        
        if self.queue:
            try:
                while not self.queue.empty():
                    await asyncio.wait_for(self.queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
        
        for worker in self.workers:
            worker.cancel()
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()


class DocumentProcessor:
    def __init__(self, task_processor: AsyncTaskProcessor):
        self.task_processor = task_processor
    
    def submit_conversion(
        self, job_id: str, filename: str, source: str, target: str
    ) -> bool:
        async def coro_factory() -> None:
            await self.process_document(job_id, filename, source, target)
        
        return self.task_processor.queue_task(job_id, coro_factory)
    
    async def process_document(
        self, job_id: str, filename: str, source: str, target: str
    ) -> None:
        job_store = get_job_store()
        storage = get_storage_manager()
        
        await job_store.update(job_id, JobStatus.PROCESSING, started_at=None)
        logger.info(f"Job {job_id}: processing started")
        
        try:
            loop = asyncio.get_event_loop()
            input_path = storage.input_path(job_id, filename)
            output_dir = storage.output_dir(job_id)
            
            if source == "docx" and target == "pdf":
                output_path = await loop.run_in_executor(
                    None, convert_docx_to_pdf, input_path, output_dir
                )
            elif source == "pdf" and target == "docx":
                output_path = await loop.run_in_executor(
                    None, convert_pdf_to_docx, input_path, output_dir
                )
            else:
                raise ConversionError(f"Unsupported conversion: {source} → {target}")
            
            await job_store.update(
                job_id,
                JobStatus.SUCCESS,
                output_file=str(output_path),
            )
            logger.info(f"Job {job_id}: completed successfully | output_size={output_path.stat().st_size}")
        except ConversionError as e:
            logger.warning(f"Job {job_id}: conversion failed | {str(e)}")
            await job_store.update(job_id, JobStatus.FAILED, error=str(e))
        except StorageError as e:
            logger.warning(f"Job {job_id}: storage error | {str(e)}")
            await job_store.update(job_id, JobStatus.FAILED, error=str(e))
        except Exception as e:
            logger.exception(f"Job {job_id}: unexpected error")
            await job_store.update(job_id, JobStatus.FAILED, error="Internal server error")


_task_processor: AsyncTaskProcessor | None = None
_document_processor: DocumentProcessor | None = None


async def get_task_processor() -> AsyncTaskProcessor:
    global _task_processor
    if _task_processor is None:
        settings = get_settings()
        _task_processor = AsyncTaskProcessor(
            settings.max_concurrent_tasks,
            settings.max_queue_length,
        )
        await _task_processor.start()
    return _task_processor


async def get_document_processor() -> DocumentProcessor:
    global _document_processor
    if _document_processor is None:
        task_processor = await get_task_processor()
        _document_processor = DocumentProcessor(task_processor)
    return _document_processor


async def cleanup_task_processor() -> None:
    global _task_processor
    if _task_processor:
        await _task_processor.stop()
        _task_processor = None
