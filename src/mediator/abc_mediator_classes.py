# -*- coding: utf-8 -*-

"""

Модуль описывает абстрактные классы осуществляющие взаимодействие по паттерну посредник

"""
from abc import ABCMeta, abstractmethod
from multiprocessing import Process, Queue


from src.app_enums import ComponentType, ActionType


class MediatorMessage(metaclass=ABCMeta):
    """

    Абстрактный класс описывающий сообщение медиатора

    """

    @property
    @abstractmethod
    def component(self)-> ComponentType:
        pass

    @property
    @abstractmethod
    def action(self)-> ActionType:
        pass


class MessageData(metaclass=ABCMeta):
    """

    Абстрактный класс описывающий данные сообщения

    """

    def __getitem__(self, item):
        if item in self.__dict__:
            return super(self.__class__, self).__getattribute__(item)


class MediatorClient(Process, metaclass=ABCMeta):
    """
    Абстрактный класс описывающий клиента, принимающего сообщение

    CLIENT_TYPE - Тип клиента для адресации
    CLIENT_ACTIONS - Возможные действия

    """
    CLIENT_TYPE = None
    CLIENT_ACTIONS = list()

    @abstractmethod
    def listen(self) -> None:
        """
        Метод цикла прослушивания сообщений
        """
        pass

    @abstractmethod
    def handle_message(self, message: MediatorMessage):
        pass

    @property
    @abstractmethod
    def queue(self)-> Queue:
        pass

    @property
    @abstractmethod
    def config(self):
        pass


class Application(metaclass=ABCMeta):
    """

    Описывает класс со структурой компонентов, которые будут взаимодействовать

    """

    @abstractmethod
    def get_component(self, component_type: ComponentType) -> MediatorClient:
        pass


class Mediator(Process, metaclass=ABCMeta):
    """

    Класс описывает абстрактного посредника для взаимодействия внутри приложения

    """

    @abstractmethod
    def __init__(self):
        super(Mediator, self).__init__()
        pass

    @abstractmethod
    def run(self):
        """
        Основной цикл для прослушки сообщений.

        :return:
        """
        pass

    @abstractmethod
    def send_message(self, message: MediatorMessage) -> None:
        """

        Абстрактный метод описывающий отправку сообщений

        """
        pass
