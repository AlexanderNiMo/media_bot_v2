# -*- coding: utf-8 -*-

"""

Модуль описывающий взаимодействие между элементами системы с помощью паттерна Посредник



"""

from .mediator_types.mediator_message import MediatorActionMessage
from .mediator_class import AppMediator
from .mediator_client import AppMediatorClient
from .mediator_client import command_message
