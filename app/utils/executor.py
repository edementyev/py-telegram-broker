from aiogram import Dispatcher
from aiogram.utils.executor import Executor
from loguru import logger

from app import config
from app.misc import dp
from app.models import db

runner = Executor(dp)


async def on_startup_webhook(dispatcher: Dispatcher):
    logger.info("Configure Web-Hook URL to: {url}", url=config.WEBHOOK_URL)
    await dispatcher.bot.set_webhook(config.WEBHOOK_URL)


def setup():
    logger.info("Configure executor...")
    db.setup(runner)
    runner.on_startup(on_startup_webhook, webhook=True, polling=False)
