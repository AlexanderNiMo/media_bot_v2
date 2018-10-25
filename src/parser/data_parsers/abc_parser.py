# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod


class ABCParser(metaclass=ABCMeta):
    """

    Абстрактное представление класса парсера данных

    """
    @abstractmethod
    def parse(self, message: ParserMessage):
        pass
