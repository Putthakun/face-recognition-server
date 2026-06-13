from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Face Recognition Server"
    debug: bool = False

    # Redis — face vectors cache (shared with .NET API)
    redis_url: str = "redis://localhost:6379"
    redis_hash_key: str = "face:vectors"  # must match .NET FaceVectorCacheService

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost/"
    rabbitmq_queue: str = "face_recognition"

    # Face matching
    face_threshold: float = 0.6
    transaction_cooldown_seconds: int = 300  # 5 min — same employee re-entry
    camera_cooldown_seconds: int = 10        # 10 sec — blur→clear same person
    face_model_name: str = "buffalo_l"
    face_model_dir: str = "models"
    face_ctx_id: int = -1  # -1 = CPU, 0 = GPU

    # .NET API — for posting transactions
    dotnet_api_url: str = "http://localhost:5081"
    dotnet_api_key: str = ""  # internal API key (optional)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
