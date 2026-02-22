#  DOCUSTREAM

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)

**A production-ready REST API microservice for converting documents between DOCX and PDF formats.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Reference](#-api-reference) • [Deployment](#-deployment)

</div>

---

##  Overview

**DOCUSTREAM** is a fully self-contained, enterprise-grade document conversion microservice designed for:

- ✅ **DOCX ↔ PDF** bidirectional conversions
- ✅ **Async processing** with configurable concurrency
- ✅ **RESTful API** with interactive Swagger UI
- ✅ **API Key authentication** for secure access
- ✅ **Structured JSON logging** with daily rotation
- ✅ **No external brokers** - pure asyncio task queue
- ✅ **Cross-platform** - Windows, Linux, macOS support
- ✅ **Production-ready** - health checks, error handling, persistence

---

##  Features

| Feature | Details |
|---------|---------|
| **Conversion Types** | DOCX → PDF, PDF → DOCX |
| **Concurrency** | Configurable async workers (default: 4) |
| **Job Queue** | Up to 100 tasks with semaphore control |
| **API Key Auth** | Secure header-based authentication |
| **Logging** | Structured logs with daily rotation (30-day retention) |
| **Storage** | Configurable file storage (default: `./data`) |
| **Job TTL** | Auto-cleanup of old jobs (default: 1 hour) |
| **File Size** | Configurable limit (default: 50 MB) |
| **Status Tracking** | PENDING → PROCESSING → SUCCESS/FAILED |
| **Error Handling** | Comprehensive exception handling with logging |

---

##  Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DOCUSTREAM                              │
│                    REST API Microservice                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
        ┌───────▼────────┐        ┌────────▼──────────┐
        │   FastAPI App  │        │  Middleware Layer │
        │  (main.py)     │        │  (middleware.py)  │
        │                │        │                   │
        │ - Lifespan     │        │ - Auth (API Key)  │
        │ - Routes       │        │ - JSON Logging    │
        │ - Exceptions   │        │ - Request IDs     │
        └────────┬───────┘        └──────────────────-┘
                 │
        ┌────────▼──────────────────┐
        │    Routes Layer           │
        │    (routes.py)            │
        │                           │
        │  POST   /jobs/submit      │
        │  GET    /jobs/{id}        │
        │  GET    /jobs/{id}/download
        │  GET    /jobs             │
        │  GET    /health           │
        └────────┬──────────────────┘
                 │
    ┌────────────┼────────────────────────┐
    │            │                        │
    ▼            ▼                        ▼
┌─────────┐  ┌──────────────┐  ┌──────────────────┐
│  Jobs   │  │  Processor   │  │  Storage Manager │
│ Store   │  │  (asyncio)   │  │  (Async I/O)     │
│         │  │              │  │                  │
│- In-mem │  │ - Task Queue │  │ - File Upload    │
│- JSON   │  │ - Semaphore  │  │ - File Download  │
│persist  │  │ - Workers    │  │ - Cleanup        │
└────┬────┘  └──────┬───────┘  └────────┬─────────┘
     │              │                   │
     │     ┌────────▼─────────┐         │
     │     │   Converter      │         │
     │     │  (converter.py)  │         │
     │     │                  │         │
     │     │ - DOCX → PDF     │         │
     │     │   (LibreOffice)  │         │
     │     │ - PDF → DOCX     │         │
     │     │   (pdf2docx)     │         │
     │     └──────────────────┘         │
     │                                  │
     │        ┌──────────────────┐      │
     └───────►│  Data Directory  │◄────-┘
              │   ./data/        │
              │                  │
              │ - jobs.json      │
              │ - input files    │
              │ - output files   │
              │ - logs/          │
              └──────────────────┘
```

### Request Flow Diagram

```
CLIENT REQUEST
    │
    ▼
┌──────────────────────────┐
│  HTTP POST /jobs/submit  │
│  - File upload           │
│  - source_format         │
│  - target_format         │
│  - X-API-Key header      │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│   Authentication Layer   │
│  - Verify API Key        │
└──────────────┬───────────┘
               │
     ┌─────────▼─────────┐
     │   YES      NO     │
     ▼                   ▼
  ┌─────┐          ┌──────────┐
  │PASS │          │HTTP 401  │
  └──┬──┘          │Unauthorized
     │             └──────────┘
     │
     ▼
┌──────────────────────────┐
│   Validation Layer       │
│  - File size check       │
│  - Format validation     │
│  - Source ≠ Target       │
└──────────────┬───────────┘
               │
     ┌─────────▼─────────┐
     │ VALID   INVALID   │
     ▼                   ▼
  ┌─────┐          ┌──────────┐
  │PASS │          │HTTP 400  │
  └──┬──┘          │Bad Request
     │             └──────────┘
     │
     ▼
┌──────────────────────────┐
│  Create Job Record       │
│  - Generate job_id (UUID)
│  - Set status: PENDING   │
│  - Save to jobs.json     │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│  Store Upload File       │
│  - Save to storage_dir   │
│  - Validate file type    │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│  Queue Conversion Task   │
│  - Check queue space     │
│  - Add coroutine to queue
│  - Return job_id         │
└──────────────┬───────────┘
               │
     ┌─────────▼──────────┐
     │  QUEUED  FULL      │
     ▼                    ▼
  ┌──────────┐      ┌──────────┐
  │HTTP 200  │      │HTTP 503  │
  │{job_id}  │      │Queue Full│
  └──────────┘      └──────────┘
               │
               ▼
        CLIENT GETS JOB_ID

═══════════════════════════════════════

ASYNC PROCESSING (Background)

Task Processor Workers (4 concurrent)
  │
  ▼
┌──────────────────────────┐
│ Worker pulls from queue  │
│ (Semaphore: max 4)       │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│  Update job status       │
│  PENDING → PROCESSING    │
│  Update started_at       │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│  LibreOffice subprocess  │
│  OR pdf2docx library     │
│  - Call converter        │
│  - Generate output file  │
│  - Monitor for timeout   │
└──────────────┬───────────┘
               │
     ┌─────────▼──────────────┐
     │ SUCCESS    FAILED      │
     ▼                        ▼
┌─────────────┐      ┌──────────────┐
│Update Status│      │Update Status │
│SUCCESS      │      │FAILED        │
│Set output   │      │Set error msg │
│Set completed│      │Set completed │
│Log success  │      │Log failure   │
└─────────────┘      └──────────────┘
```

### Job State Machine

```
┌─────────┐
│ PENDING │◄───────────────────┐
└────┬────┘                    │
     │ (Task picked up)        │
     ▼                         │
┌──────────────┐         ┌─────┴─────────┐
│  PROCESSING  │◄────────┤ (Retry logic) │
└────┬─────────┘         └───────────────┘
     │
     ├─ Conversion succeeds ──┐
     │                        ▼
     │                  ┌──────────┐
     │                  │ SUCCESS  │
     │                  └──────────┘
     │
     └─ Conversion fails ────┐
                             ▼
                        ┌──────────┐
                        │ FAILED   │
                        └──────────┘
```

---

##  Quick Start

### System Requirements

- **Python**: 3.11 or higher
- **LibreOffice**: Required for DOCX↔PDF conversion
  - **Windows**: https://www.libreoffice.org/download/
  - **Linux**: `sudo apt-get install libreoffice`
  - **macOS**: `brew install libreoffice`

### 1️. Installation

```bash
# Clone repository
cd d:/Github_Projects/DocuStream

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2️. Configuration

```bash
# Copy example config
cp .env.example .env
```

Edit `.env`:

```dotenv
# Security
API_KEY=your-32-character-secure-api-key-here

# Storage
STORAGE_DIR=./data
MAX_FILE_SIZE_MB=50

# Concurrency
MAX_CONCURRENT_TASKS=4
MAX_QUEUE_LENGTH=100

# Job Management
JOB_TTL_SECONDS=3600
LOG_LEVEL=INFO

# LibreOffice Path (Optional - auto-detected on most systems)
SOFFICE_PATH=C:\Program Files\LibreOffice\program\soffice.exe
```

### 3️. Find LibreOffice Path (Windows)

```powershell
Get-ChildItem -Path "C:\", "D:\", "E:\" -Filter "soffice.exe" `
  -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
```

Copy the full path to `.env`:

```dotenv
SOFFICE_PATH=C:\Program Files\LibreOffice\program\soffice.exe
```

### 4️. Run Server

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

**Server running at:**
- 🌐 API: http://127.0.0.1:8000
- 📚 Swagger UI: http://127.0.0.1:8000/docs
- 📖 ReDoc: http://127.0.0.1:8000/redoc

---

## API Reference

### Authentication

All endpoints except `/health` require the `X-API-Key` header:

```bash
-H "X-API-Key: your-32-character-secure-api-key-here"
```

### Endpoints

#### 1️.  Health Check

**No authentication required**

```bash
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

#### 2️. Submit Conversion Job

```bash
POST /jobs/submit
```

**Parameters:**
- `file` (File) - Document to convert
- `source_format` (Enum) - `docx` or `pdf`
- `target_format` (Enum) - `docx` or `pdf`

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/jobs/submit \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.docx" \
  -F "source_format=docx" \
  -F "target_format=pdf"
```

**Response (200 OK):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PENDING"
}
```

**Error Responses:**
- `400 Bad Request` - Source and target formats identical or unsupported
- `401 Unauthorized` - Invalid/missing API key
- `413 Payload Too Large` - File exceeds MAX_FILE_SIZE_MB
- `422 Unprocessable Entity` - Invalid parameters
- `503 Service Unavailable` - Task queue is full

---

#### 3️.  Get Job Status

```bash
GET /jobs/{job_id}
```

**Example:**
```bash
curl http://127.0.0.1:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "X-API-Key: your-api-key"
```

**Response (200 OK):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS",
  "source_format": "docx",
  "target_format": "pdf",
  "input_filename": "document.docx",
  "output_file": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
  "error": null,
  "created_at": "2026-02-23T10:30:15.123456",
  "started_at": "2026-02-23T10:30:16.456789",
  "completed_at": "2026-02-23T10:30:22.789012"
}
```

**Job Status Values:**
- `PENDING` - Waiting in queue
- `PROCESSING` - Currently being converted
- `SUCCESS` - Conversion completed successfully
- `FAILED` - Conversion failed (see error field)

**Error Responses:**
- `401 Unauthorized` - Invalid/missing API key
- `404 Not Found` - Job ID does not exist

---

#### 4️. Download Converted Document

```bash
GET /jobs/{job_id}/download
```

**Example:**
```bash
curl -O http://127.0.0.1:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download \
  -H "X-API-Key: your-api-key"
```

**Response (200 OK):** Binary file stream

**Error Responses:**
- `400 Bad Request` - Job has not completed successfully
- `401 Unauthorized` - Invalid/missing API key
- `404 Not Found` - Job ID or output file not found

---

#### 5️. List Jobs

```bash
GET /jobs?status={status}&limit={limit}&offset={offset}
```

**Parameters:**
- `status` (Optional) - Filter by job status: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`
- `limit` (Optional) - Max results (default: 50)
- `offset` (Optional) - Pagination offset (default: 0)

**Example:**
```bash
curl "http://127.0.0.1:8000/jobs?status=SUCCESS&limit=20&offset=0" \
  -H "X-API-Key: your-api-key"
```

**Response (200 OK):**
```json
{
  "jobs": [
    {
      "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "SUCCESS",
      "source_format": "docx",
      "target_format": "pdf",
      "input_filename": "document.docx",
      "output_file": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
      "error": null,
      "created_at": "2026-02-23T10:30:15.123456",
      "started_at": "2026-02-23T10:30:16.456789",
      "completed_at": "2026-02-23T10:30:22.789012"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

## Project Structure

```
DocuStream/
├── main.py                 # FastAPI app + lifespan management
├── routes.py               # API endpoints (5 routes)
├── processor.py            # Async task queue + workers
├── converter.py            # DOCX/PDF conversion logic
├── jobs.py                 # Job store + persistence
├── storage.py              # File I/O operations
├── config.py               # Settings from .env
├── dependencies.py         # API key authentication
├── middleware.py           # Request logging + correlation IDs
├── logger.py               # Structured logging setup
├── exceptions.py           # Custom exception classes
├── requirements.txt        # Python dependencies
├── .env.example            # Environment config template
├── .env                    # Environment config (local)
├── README.md               # This file
└── data/
    ├── jobs.json           # Job records (persisted)
    ├── logs/               # Daily log files
    │   └── docustream.log
    ├── [input files]       # Uploaded documents
    └── [output files]      # Converted documents
```

### Module Responsibilities

| Module | Responsibility |
|--------|-----------------|
| `main.py` | FastAPI app initialization, lifespan hooks, exception handlers |
| `routes.py` | REST endpoint definitions, request validation, response formatting |
| `processor.py` | Async task queue management, worker pool, concurrency control |
| `converter.py` | Document conversion (DOCX↔PDF), LibreOffice integration |
| `jobs.py` | Job record management, in-memory store, JSON persistence |
| `storage.py` | File I/O, upload handling, file cleanup |
| `config.py` | Settings management via pydantic-settings from .env |
| `dependencies.py` | FastAPI dependency injection, API key verification |
| `middleware.py` | Request/response logging with structured JSON format |
| `logger.py` | Centralized logging with TimedRotatingFileHandler |
| `exceptions.py` | Custom exception hierarchy for error handling |

---

## Monitoring & Logging

### Log Format

All logs follow a structured pipe-separated format:

```
YYYY-MM-DD HH:MM:SS | LEVEL | logger_name | message
```

**Example:**
```
2026-02-23 10:30:15 | INFO     | docustream | Job a1b2c3d4-...: created | file=document.docx | docx->pdf
2026-02-23 10:30:16 | INFO     | docustream | Job a1b2c3d4-...: processing started
2026-02-23 10:30:22 | INFO     | docustream | Job a1b2c3d4-...: completed successfully | output_size=150234
2026-02-23 10:30:22 | INFO     | docustream | {"method": "GET", "path": "/jobs/a1b2c3d4-.../download", "status": 200, "duration_ms": 1.23, "correlation_id": "xyz-123"}
```

### Log Files

Logs are stored in: `./data/logs/docustream.log`

**Features:**
- Daily rotation (rolls over at midnight)
- 30-day retention (auto-cleanup)
- Console + file output simultaneously
- Timestamp, level, logger name, message

### View Live Logs

```bash
# Windows
Get-Content -Path data/logs/docustream.log -Tail 20 -Wait

# Linux/macOS
tail -f data/logs/docustream.log
```

---

## Performance Tuning

### Configuration Parameters

```dotenv
# Concurrency Settings
MAX_CONCURRENT_TASKS=4      # Simultaneous conversions
MAX_QUEUE_LENGTH=100        # Max pending jobs

# File Settings
MAX_FILE_SIZE_MB=50         # Max upload size
STORAGE_DIR=./data          # Where files are stored

# Job Settings
JOB_TTL_SECONDS=3600        # Auto-cleanup after 1 hour
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
```

### Scaling Recommendations

| Scenario | Setting |
|----------|---------|
| **Low Load** (1-10 jobs/day) | `MAX_CONCURRENT_TASKS=2` |
| **Medium Load** (50-500 jobs/day) | `MAX_CONCURRENT_TASKS=4` (default) |
| **High Load** (1000+ jobs/day) | `MAX_CONCURRENT_TASKS=8-16` |
| **Large Files** (>50MB) | Increase `MAX_FILE_SIZE_MB`, add storage |
| **Long Queue** (spike traffic) | Increase `MAX_QUEUE_LENGTH=200` |

---

## Troubleshooting

### LibreOffice Not Found

**Error:**
```
LibreOffice not found. Install LibreOffice or set SOFFICE_PATH in .env
```

**Solution:**
1. Install LibreOffice: https://www.libreoffice.org/download/
2. Find path: `Get-ChildItem -Path 'C:\' -Filter 'soffice.exe' -Recurse -ErrorAction SilentlyContinue`
3. Update `.env`: `SOFFICE_PATH=C:\Program Files\LibreOffice\program\soffice.exe`
4. Restart server

---

### Queue Full Error

**Error:**
```
HTTP 503: Task queue is full, try again later
```

**Solution:**
- Reduce concurrent conversions or increase processing time
- Increase `MAX_QUEUE_LENGTH` in `.env`
- Increase `MAX_CONCURRENT_TASKS` to process faster

---

### Job Not Found

**Error:**
```
HTTP 404: Job not found
```

**Solutions:**
- Verify job_id is correct
- Check if job expired (JOB_TTL_SECONDS default: 1 hour)
- View all jobs: `GET /jobs`

---

### File Too Large

**Error:**
```
HTTP 413: File exceeds maximum size
```

**Solution:**
- Increase `MAX_FILE_SIZE_MB` in `.env`
- Compress source file before uploading

---

### API Key Invalid

**Error:**
```
HTTP 401: Unauthorized
```

**Solutions:**
- Add `X-API-Key` header to request
- Update `.env` API_KEY if forgotten
- Use 32+ character keys for production

---

## Usage Examples

### Python Client

```python
import requests
import time

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "your-32-character-secure-api-key-here"
HEADERS = {"X-API-Key": API_KEY}

# 1. Submit job
with open("document.docx", "rb") as f:
    files = {"file": f}
    data = {"source_format": "docx", "target_format": "pdf"}
    response = requests.post(
        f"{BASE_URL}/jobs/submit",
        files=files,
        data=data,
        headers=HEADERS
    )
    job_id = response.json()["job_id"]

# 2. Poll for completion
while True:
    response = requests.get(
        f"{BASE_URL}/jobs/{job_id}",
        headers=HEADERS
    )
    job = response.json()
    
    if job["status"] == "SUCCESS":
        print(f"Conversion complete!")
        break
    elif job["status"] == "FAILED":
        print(f"Conversion failed: {job['error']}")
        break
    else:
        print(f"Status: {job['status']}")
        time.sleep(1)

# 3. Download result
if job["status"] == "SUCCESS":
    response = requests.get(
        f"{BASE_URL}/jobs/{job_id}/download",
        headers=HEADERS
    )
    with open("document.pdf", "wb") as f:
        f.write(response.content)
    print("File saved: document.pdf")
```

### cURL Examples

```bash
API_KEY="your-32-character-secure-api-key-here"

# Check health
curl http://127.0.0.1:8000/health

# Submit job
JOB_ID=$(curl -s -X POST http://127.0.0.1:8000/jobs/submit \
  -H "X-API-Key: $API_KEY" \
  -F "file=@document.docx" \
  -F "source_format=docx" \
  -F "target_format=pdf" | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# Check status
curl http://127.0.0.1:8000/jobs/$JOB_ID -H "X-API-Key: $API_KEY" | jq .

# Download (when ready)
curl http://127.0.0.1:8000/jobs/$JOB_ID/download \
  -H "X-API-Key: $API_KEY" \
  -o converted_document.pdf
```

### JavaScript/Node.js Client

```javascript
const API_KEY = "your-32-character-secure-api-key-here";
const BASE_URL = "http://127.0.0.1:8000";

async function convertDocument(file) {
  // 1. Submit job
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source_format", "docx");
  formData.append("target_format", "pdf");

  const submitResponse = await fetch(`${BASE_URL}/jobs/submit`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
    body: formData,
  });

  const { job_id } = await submitResponse.json();
  console.log("Job submitted:", job_id);

  // 2. Poll for completion
  let job = null;
  while (true) {
    const statusResponse = await fetch(`${BASE_URL}/jobs/${job_id}`, {
      headers: { "X-API-Key": API_KEY },
    });

    job = await statusResponse.json();

    if (job.status === "SUCCESS") {
      console.log("Conversion complete!");
      break;
    } else if (job.status === "FAILED") {
      console.error("Conversion failed:", job.error);
      break;
    } else {
      console.log("Status:", job.status);
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  // 3. Download result
  if (job.status === "SUCCESS") {
    const downloadResponse = await fetch(
      `${BASE_URL}/jobs/${job_id}/download`,
      { headers: { "X-API-Key": API_KEY } }
    );

    const blob = await downloadResponse.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "converted_document.pdf";
    a.click();
  }
}
```

---

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install LibreOffice
RUN apt-get update && apt-get install -y libreoffice

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build & Run:**
```bash
docker build -t docustream:latest .
docker run -p 8000:8000 \
  -e API_KEY="your-secure-key" \
  -e SOFFICE_PATH="/usr/bin/soffice" \
  docustream:latest
```

### Environment Variables

```bash
API_KEY=your-secure-api-key
STORAGE_DIR=/data
MAX_FILE_SIZE_MB=50
MAX_CONCURRENT_TASKS=4
MAX_QUEUE_LENGTH=100
JOB_TTL_SECONDS=3600
LOG_LEVEL=INFO
SOFFICE_PATH=/usr/bin/soffice
```

## Support

For issues, questions, or suggestions:
-  GitHub Issues
---