# Face Recognition Server

FastAPI-based attendance system with face recognition, Redis caching, RabbitMQ queue, and Prometheus metrics.

## Quick start

```bash
cp .env.example .env
# แก้ไขค่าใน .env ให้เหมาะกับ environment

docker compose up --build
```

## Services

| Service     | URL                        |
|-------------|----------------------------|
| API         | http://localhost:8000      |
| API docs    | http://localhost:8000/docs |
| RabbitMQ UI | http://localhost:15672     |
| Prometheus  | http://localhost:9090      |

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/
```
