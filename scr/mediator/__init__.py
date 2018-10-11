# -*- coding: utf-8 -*-

"""

Модуль описывающий взаимодействие между элементами системы с помощью паттерна Посредник



"""

from .mediator_types.mediator_message import MediatorActionMessage, CommandData, ClientData, CrawlerData
from .mediator_class import AppMediator
from .mediator_client import AppMediatorClient, command_message, send_message, parser_message


