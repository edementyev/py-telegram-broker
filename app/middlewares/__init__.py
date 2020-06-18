from aiogram import Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from loguru import logger

from app.middlewares.update_user import UpdateUserMiddleware


def setup(dispatcher: Dispatcher):
    logger.info("Configure middlewares...")

    dispatcher.middleware.setup(LoggingMiddleware("bot"))
    dispatcher.middleware.setup(UpdateUserMiddleware())
