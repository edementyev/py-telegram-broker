import argparse
import asyncio
import logging
import sys
from datetime import datetime

import aiohttp
import pytz
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from app.config import Config, ConfigManager
from app.decorate_log import LVL_CALL
from app.storage_util import FSMContextFactory

clock = datetime(2020, 1, 1, tzinfo=pytz.timezone('Europe/Moscow'))

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', dest='debug',
                    action='store_true', default=False)
args = parser.parse_args()
config = ConfigManager(args.debug).config

stdout_handler = logging.StreamHandler(sys.stderr)
log_handlers = [stdout_handler]
if config.log.use_file:
    try:
        with open(config.log.file_path, mode='x'):
            pass
    except FileExistsError:
        pass
    file_handler = logging.FileHandler(config.log.file_path)
    log_handlers.append(file_handler)
# noinspection PyArgumentList
logging.basicConfig(format=u'%(filename)s [ LINE:%(lineno)+3s ]#%(levelname)+8s [%(asctime)s]  %(message)s',
                    level=LVL_CALL,
                    handlers=log_handlers)

event_loop = asyncio.get_event_loop()
proxy_url = None
proxy_auth = None
if config.app.use_proxy:
    proxy_url = config.proxy.url
    if len(config.proxy.username) > 0:
        proxy_auth = aiohttp.BasicAuth(login=config.proxy.username,
                                       password=config.proxy.password)
bot = Bot(token=config.app.token,
          loop=event_loop,
          proxy=proxy_url,
          proxy_auth=proxy_auth)
dp = Dispatcher(bot,
                loop=event_loop,
                storage=RedisStorage2(config.redis.host,
                                      config.redis.port,
                                      db=config.redis.db,
                                      prefix=config.redis.prefix))
dp.middleware.setup(LoggingMiddleware())

import app.db
import app.handlers
