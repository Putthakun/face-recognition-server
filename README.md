<div align="center">

# Face Recognition Server

**Face matching & attendance pipeline powered by InsightFace**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![InsightFace](https://img.shields.io/badge/InsightFace-buffalo_l-FF6F00?style=flat)](https://github.com/deepinsight/insightface)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-aio--pika-FF6600?style=flat&logo=rabbitmq&logoColor=white)](https://rabbitmq.com)
[![Redis](https://img.shields.io/badge/Redis-cache-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)

</div>

---

## Overview

`face-recognition-server` is the **matching engine** of the attendance system. It consumes face crops published by the edge device, extracts embeddings with [InsightFace](https://github.com/deepinsight/insightface) (`buffalo_l`), compares them against a cache of known employee embeddings, and records attendance transactions through `face-recognition-api` — applying cooldown rules to avoid duplicate check-ins.

It also exposes a synchronous embedding endpoint used by `face-recognition-api` when an employee photo is created or updated, so the same model powers both enrollment and recognition.

```
face-recognition-edge ──(RabbitMQ: face_events / face.detected)──▶ face-recognition-server
                                                                          │
                                          Redis "face:vectors" ◀─────────┤ (lookup)
                                                                          │
                                                  cosine similarity match │
                                                                          ▼
                                                              face-recognition-api
                                                              POST /api/transactions
```

---

## Features

- **Async RabbitMQ consumer** — subscribes to the `face_recognition` queue (topic exchange `face_events`, routing key `face.detected`) and processes detection events as they arrive
- **Embedding extraction** — `POST /api/embeddings` runs InsightFace on an uploaded image and returns the face embedding, or `face_detected: false` if no face is found
- **Cosine-similarity matching** — compares incoming embeddings against an in-memory face database loaded from Redis, using a configurable similarity threshold (default `0.6`)
- **Two-tier cooldown** — per-camera (10s) and per-employee (300s) cooldowns prevent duplicate attendance records from repeated detections
- **Redis-backed face DB** — embeddings are loaded from the shared `face:vectors` Redis hash at startup and can be hot-reloaded without a restart
- **Health & ops endpoints** — `/api/health` (face DB size), `/api/reload` (force reload from Redis), `/metrics` (Prometheus-format metrics)
- **Dockerized** — slim Python image with OpenCV + ONNX Runtime for CPU inference

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Face recognition | InsightFace (`buffalo_l`), ONNX Runtime (CPU) |
| Message queue | RabbitMQ via aio-pika (async consumer) |
| Cache | Redis (asyncio client) — shared `face:vectors` hash |
| Config | pydantic-settings (`.env` based) |
| Container | Docker + Docker Compose |

---

## Configuration

All configuration is via environment variables (see `app/core/config.py`):

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | — | Redis connection string |
| `REDIS_HASH_KEY` | `face:vectors` | Redis hash holding EmpId → embedding |
| `RABBITMQ_URL` | — | RabbitMQ connection string |
| `RABBITMQ_QUEUE` | `face_recognition` | Queue consumed for detection events |
| `FACE_THRESHOLD` | `0.6` | Cosine similarity threshold for a match |
| `TRANSACTION_COOLDOWN_SECONDS` | `300` | Per-employee cooldown before a new transaction is recorded |
| `CAMERA_COOLDOWN_SECONDS` | `10` | Per-camera cooldown between processed detections |
| `FACE_MODEL_NAME` | `buffalo_l` | InsightFace model pack |
| `FACE_MODEL_DIR` | `models` | Directory for downloaded model weights |
| `FACE_CTX_ID` | `-1` | InsightFace context (`-1` = CPU) |
| `DOTNET_API_URL` | — | Base URL of `face-recognition-api` |
| `DOTNET_API_KEY` | — | API key/credential for posting transactions |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/embeddings` | Extract a face embedding from an uploaded image (used during employee enrollment) |
| `GET` | `/api/health` | Health check + current face DB size |
| `POST` | `/api/reload` | Reload the face database from Redis without restarting |
| `GET` | `/metrics` | Prometheus-format metrics |
| `GET` | `/docs` | Auto-generated Swagger UI |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Running Redis + RabbitMQ (e.g. via [`face-recognition-infra`](https://github.com/Putthakun/face-recognition-infrastructure))
- A reachable [`face-recognition-api`](https://github.com/Putthakun/face-recognition-api) instance

### Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with Redis / RabbitMQ / API connection details
uvicorn app.main:app --reload
```

On startup, the service loads the face database from Redis and starts the RabbitMQ consumer in the background (FastAPI `lifespan`).

### Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

### Testing

```bash
pytest tests/
```

---

## Related Services

This service is part of a larger system. See [`real-time-face-recognition-attendance-system`](https://github.com/Putthakun/real-time-face-recognition-attendance-system) for the full architecture overview.

| Repo | Role |
|---|---|
| [`face-recognition-edge`](https://github.com/Putthakun/face-recognition-edge) | Captures video, detects faces (YOLOv8), publishes crops to RabbitMQ |
| [`face-recognition-api`](https://github.com/Putthakun/face-recognition-api) | System of record — employees, cameras, transactions, auth |
| [`face-recognition-web`](https://github.com/Putthakun/face-recognition-web) | Vue 3 dashboard for admins/supervisors |
| [`face-recognition-infra`](https://github.com/Putthakun/face-recognition-infrastructure) | Shared SQL Server, Redis, RabbitMQ via Docker Compose |
