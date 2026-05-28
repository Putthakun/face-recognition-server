import aio_pika
from app.core.config import settings


async def get_connection() -> aio_pika.Connection:
    return await aio_pika.connect_robust(settings.rabbitmq_url)


async def consume(queue_name: str, callback) -> None:
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, durable=True)
        async with queue.iterator() as messages:
            async for message in messages:
                async with message.process():
                    await callback(message.body)
