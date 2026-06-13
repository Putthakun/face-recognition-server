import logging

import aio_pika
from app.core.config import settings
from app.models.schemas import RecognitionTask
from app.services.face_service import face_service

logger = logging.getLogger(__name__)

_connection: aio_pika.Connection | None = None


async def get_connection() -> aio_pika.Connection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _connection


async def _handle_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        task = RecognitionTask.model_validate_json(message.body)
        result = await face_service.recognize(task)

        logger.info(
            "camera=%d employee=%s confidence=%.3f",
            result.camera_id,
            result.employee_id,
            result.confidence,
        )

        # Post transaction to .NET API (always — even if employee_id is None)
        await face_service.post_transaction(result)


async def start_consumer() -> None:
    connection = await get_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    # Declare the same exchange the edge publishes to
    exchange = await channel.declare_exchange(
        "face_events",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    # Declare queue and bind to exchange with edge's routing key
    queue = await channel.declare_queue(settings.rabbitmq_queue, durable=True)
    await queue.bind(exchange, routing_key="face.detected")

    await queue.consume(_handle_message)
    logger.info("Listening on queue '%s' (bound to face_events / face.detected)", settings.rabbitmq_queue)
