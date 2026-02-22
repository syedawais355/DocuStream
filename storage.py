import shutil
from pathlib import Path
from aiofiles import open as aopen
from config import get_settings
from exceptions import StorageError


class StorageManager:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
    
    def job_dir(self, job_id: str) -> Path:
        job_path = self.base_dir / job_id
        job_path.mkdir(parents=True, exist_ok=True)
        return job_path
    
    def output_dir(self, job_id: str) -> Path:
        output_path = self.base_dir / job_id / "output"
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    
    async def save_upload(
        self, job_id: str, filename: str, file_obj
    ) -> Path:
        job_path = self.job_dir(job_id)
        input_path = job_path / filename
        settings = get_settings()
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        
        bytes_written = 0
        try:
            async with aopen(input_path, "wb") as f:
                while True:
                    chunk = await file_obj.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        input_path.unlink(missing_ok=True)
                        raise StorageError(
                            f"File exceeds maximum size of {settings.max_file_size_mb}MB"
                        )
                    await f.write(chunk)
        except StorageError:
            raise
        except Exception as e:
            input_path.unlink(missing_ok=True)
            raise StorageError(f"Failed to save uploaded file: {str(e)}") from e
        
        return input_path
    
    def input_path(self, job_id: str, filename: str) -> Path:
        return self.base_dir / job_id / filename
    
    def cleanup_job(self, job_id: str) -> None:
        job_path = self.base_dir / job_id
        if job_path.exists():
            shutil.rmtree(job_path, ignore_errors=True)


_storage_manager: StorageManager | None = None


def get_storage_manager() -> StorageManager:
    global _storage_manager
    if _storage_manager is None:
        settings = get_settings()
        _storage_manager = StorageManager(settings.storage_path)
    return _storage_manager
