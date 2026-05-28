from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Face Recognition Server"
    debug: bool = False

    database_url: str
    redis_url: str = "redis://localhost:6379"
    rabbitmq_url: str = "amqp://guest:guest@localhost/"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    face_model_path: str = "models/face_recognition_model"
    face_threshold: float = 0.6

    class Config:
        env_file = ".env"


settings = Settings()
