from abc import ABCMeta, abstractmethod

from multiprocessing import Process


class AbstractCrawlerWorker(metaclass=ABCMeta):
    """
    Абстрактный класс описывает worker, который выполняется в отдельном процессе
    и выполняет необходимые действия

    """

    def __init__(self, job, config):
        self.process = None
        self.returned_data = None
        self.job = job
        self.config = config

    @abstractmethod
    def start(self):
        """
        Запускает исполнение операции
        :return:
        """
        pass

    @abstractmethod
    def kill(self):
        """
        Аварийно останавливает выполнение

        :return:
        """
        pass

    @property
    @abstractmethod
    def result(self):
        """
        Возвращает результат выполнения

        :return:
        """
        pass

    @property
    @abstractmethod
    def ended(self):
        """
        Проверяет закончилось ли выполнение процесса

        :return:
        """
        pass


class Worker(AbstractCrawlerWorker):
    def start(self):
        self.process = Process(target=self.get_target())
        self.process.start()

    def kill(self):
        if not self.ended:
            self.process.terminate()

    def get_target(self):
        def a():
            print('Start worker')

        return a

    @property
    def result(self) -> list:
        return []

    @property
    def ended(self):
        return not self.process.is_alive()