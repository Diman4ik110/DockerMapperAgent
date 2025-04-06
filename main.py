from agent.core import Agent
from agent.config import Config
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/agent.log"), logging.StreamHandler()]
)

async def main():
    try:
        # Загрузка конфигурации
        config = Config("/etc/DockerNetAgent/agent.conf")

        # Инициализация агента
        agent = Agent(config)

        # Запуск агента
        await agent.run()
    except Exception as e:
        logging.error(f"Ошибка при выполнении агента: {e}")

if __name__ == "__main__":
    asyncio.run(main())