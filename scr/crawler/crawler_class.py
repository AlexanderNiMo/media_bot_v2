
import logging
import time
from multiprocessing import Process, Queue
from abc import ABCMeta, abstractmethod

from app_enums import ComponentType, ActionType, MediaType
from mediator import AppMediatorClient, MediatorActionMessage, CrawlerData
from database import DbManager

logger = logging.getLogger(__name__)


class Crawler(AppMediatorClient):

    CLIENT_TYPE = ComponentType.CRAWLER
    CLIENT_ACTIONS = [
        ActionType.FORCE_CHECK,
        ActionType.CHECK_FILMS,
        ActionType.CHECK_SERIALS,
        ActionType.CHECK,
        ActionType.DOWNLOAD_TORREN
    ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config, threads):

        super(Crawler, self).__init__(in_queue, out_queue, config)

        self.__threads = threads
        self.active_workers = []
        self.jobs = []
        db_manager = DbManager(self.config)
        self.db_handler = DataBaseHandler(db_manager)
        self.messages = []

    def handle_message(self, message: MediatorActionMessage):
        logger.info(
            'Полученно новое сообщение. для Crawler от {0} с данными {}'.format(
                message.from_component,
                message
            )
        )

        self.add_jobs(message)

    def add_jobs(self, message: MediatorActionMessage):

        if message.action == ActionType.DOWNLOAD_TORREN:
            return [
                {
                    'type': message.action,
                    'client_id': message.data.client_id,
                    'media_id': message.data.media_id
                 }
            ]

        jobs = self.db_handler.get_job_list(message)
        for job in jobs:
            job.update({'type': message.action})
            self.jobs.append(job)

    def main_actions(self):
        logger.info('Запуск основного потока работы {}'.format(self))
        while True:
            time.sleep(10)
            self.update_jobs()

    def update_jobs(self):
        """
        Выполняет работу по очистке, обработке результата и запуску воркеров
        :return:
        """
        # Проверка выполнения
        self.update_worker_status()
        # Обработка результатов
        self.handle_worker_results()
        # Добавдение новых воркеров в пул
        self.add_workers()

    def update_worker_status(self):
        """
        Проверяет статус выполнения подчиненных воркеров и сбор результатов

        :return:
        """
        logger.info('Проверка статуса заданий.')

        for worker in self.active_workers:
            if worker.ended:
                self.messages += worker.result
        self.active_workers = list((i for i in self.active_workers if not i.ended))

    def handle_worker_results(self):
        map(self.send_message, self.messages)
        self.messages = []

    def add_workers(self):

        while len(self.active_workers) <= self.__threads:
            if len(self.jobs) == 0:
                break
            self.add_thread(self.jobs.pop(0))

    def get_worker(self, job: dict):
        if job['type'] in [
            ActionType.FORCE_CHECK,
            ActionType.CHECK_FILMS,
            ActionType.CHECK_SERIALS,
            ActionType.CHECK
        ]:
            return TorrentSearchWorker(job)
        elif job['type'] in [
            ActionType.DOWNLOAD_TORREN
        ]:
            return DownloadWorker(job)

    def add_thread(self, job):
        worker = self.get_worker(job)
        worker.start()
        self.active_workers.append(worker)


class DataBaseHandler:
    """
    Класс обрабатывает сообщения от компонентов и возвращает список данных для обработки
    """

    def __init__(self, db_manager: DbManager):
        self.db_manager = db_manager

    def get_job_list(self, message: MediatorActionMessage)->list:
        result = []
        db = self.db_manager
        data = message.data
        media = []
        if not data.media_id == 0:
            media = [db.find_media(data.media_id, data.media_type, data.season)]
        elif not data.media_type == MediaType.BASE_MEDIA:
            media = db.find_all_media(data.media_type)

        for element in media:
            result.append(
                {
                    'type': message.action,
                    'client_id': data.client_id,
                    'media_id': data.media_id,
                    'title': element.label,
                    'download_url': element.download_url,
                    'torrent_tracker': element.torrent_tracker,
                    'theam_id': element.theam_id,
                 }
            )

        return result


class AbstractCrawlerWorker(metaclass=ABCMeta):
    """
    Абстрактный класс описывает worker, который выполняется в отдельном процессе
    и выполняет необходимые действия

    """
    def __init__(self, data: dict):
        self.process = None
        self.__dict__.update(**data)

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
    def result(self)->list:
        return []

    @property
    def ended(self):
        return not self.process.is_alive()


class TorrentSearchWorker(Worker):

    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')

    @property
    def result(self):
        return []


class DownloadWorker(Worker):

    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')

    @property
    def result(self):
        return []

if __name__ == '__main__':

    from multiprocessing import Queue
    from app import config

    logger = logging.getLogger()
    consol_hndl = logging.StreamHandler()
    logger.addHandler(consol_hndl)
    logger.setLevel(logging.DEBUG)

    c = Crawler(Queue(), Queue(), config, 10)

    message = MediatorActionMessage(ComponentType.CRAWLER, ActionType.CHECK, ComponentType.CRAWLER)
    message.data = CrawlerData(1, 1)

    c.add_jobs(message)
    c.update_jobs()