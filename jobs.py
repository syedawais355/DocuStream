import asyncio
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from config import get_settings


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    source_format: str
    target_format: str
    input_filename: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_file: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "JobRecord":
        data = data.copy()
        data["status"] = JobStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data["started_at"]:
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data["completed_at"]:
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)


class JobStore:
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()
        self._jobs_file = self.storage_dir / "jobs.json"
    
    async def load(self) -> None:
        async with self._lock:
            if self._jobs_file.exists():
                try:
                    with open(self._jobs_file, "r") as f:
                        data = json.load(f)
                    self._jobs = {
                        job_id: JobRecord.from_dict(record)
                        for job_id, record in data.items()
                    }
                except Exception:
                    self._jobs = {}
    
    async def _persist(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        data = {
            job_id: record.to_dict()
            for job_id, record in self._jobs.items()
        }
        with open(self._jobs_file, "w") as f:
            json.dump(data, f, indent=2)
    
    async def create(
        self, source_format: str, target_format: str, filename: str
    ) -> str:
        async with self._lock:
            job_id = str(uuid.uuid4())
            record = JobRecord(
                job_id=job_id,
                status=JobStatus.PENDING,
                source_format=source_format,
                target_format=target_format,
                input_filename=filename,
                created_at=datetime.utcnow(),
            )
            self._jobs[job_id] = record
            await self._persist()
            return job_id
    
    async def get(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def update(
        self,
        job_id: str,
        status: JobStatus,
        output_file: Optional[str] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> None:
        async with self._lock:
            if job_id not in self._jobs:
                return
            
            record = self._jobs[job_id]
            record.status = status
            if output_file:
                record.output_file = output_file
            if error:
                record.error = error
            if started_at:
                record.started_at = started_at
            if status in (JobStatus.SUCCESS, JobStatus.FAILED):
                record.completed_at = datetime.utcnow()
            
            await self._persist()
    
    async def list(
        self, status_filter: Optional[str] = None, limit: int = 50
    ) -> tuple[list[JobRecord], int]:
        async with self._lock:
            jobs = list(self._jobs.values())
            
            if status_filter:
                try:
                    status_enum = JobStatus(status_filter)
                    jobs = [j for j in jobs if j.status == status_enum]
                except ValueError:
                    pass
            
            jobs.sort(key=lambda x: x.created_at, reverse=True)
            return jobs[:limit], len(jobs)
    
    async def cleanup_expired(self, ttl_seconds: int) -> int:
        async with self._lock:
            now = datetime.utcnow()
            to_delete = [
                job_id
                for job_id, record in self._jobs.items()
                if record.completed_at
                and (now - record.completed_at).total_seconds() > ttl_seconds
            ]
            
            for job_id in to_delete:
                del self._jobs[job_id]
            
            if to_delete:
                await self._persist()
            
            return len(to_delete)


_job_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _job_store
    if _job_store is None:
        settings = get_settings()
        _job_store = JobStore(settings.storage_path)
    return _job_store
