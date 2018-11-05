# -*- coding: utf-8 -*-

"""

Описывает приложение, в приложении храняться ссылки на основные компоненты
для контролья их состояния и инициализации

"""

from .App import create_app_test
from src.app.config import Config

config = Config()
config.set_config_file()
