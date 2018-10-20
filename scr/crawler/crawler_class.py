import logging
import time

from app_enums import ComponentType, ActionType, MediaType
from crawler.Workers import DownloadWorker
from crawler.Workers import TorrentSearchWorker
from database import DbManager
from mediator import AppMediatorClient, MediatorActionMessage, CrawlerData
from multiprocessing import Queue

logger = logging.getLogger(__name__)

class Job:
    def __init__(self,
                 action_type,
                 client_id,
                 media_id,
                 title,
                 season,
                 year,
                 download_url,
                 torrent_tracker,
                 theam_id,
                 **kwargs
                 ):
        self.action_type = action_type
        self.client_id = client_id
        self.media_id = media_id
        self.title = title
        self.download_url = download_url
        self.torrent_tracker = torrent_tracker
        self.theam_id = theam_id
        self.season = season
        self.year = year
        self.__dict__.update(**kwargs)

    @property
    def text_query(self):
        return '{}'.format(self.title, )


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
        self.db_handler = CrawlerMessageHandler(db_manager)
        self.messages = []

    def main_actions(self):
        logger.info('Запуск основного потока работы {}'.format(self))
        while True:
            time.sleep(10)
            try:
                self.update_jobs()
            except Exception as ex:
                logging.error('При обновлении обработчиков произошла ощибка {}'.format(ex))

    def handle_message(self, message: MediatorActionMessage):
        logger.info(
            'Полученно новое сообщение. для Crawler от {0} с данными {}'.format(
                message.from_component,
                message
            )
        )

        self.add_jobs(message)

    def add_jobs(self, message: MediatorActionMessage):

        jobs = self.db_handler.get_job_list(message)
        for job in jobs:
            self.jobs.append(job)

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

    def add_thread(self, job):
        worker = self.get_worker(job)
        worker.start()
        self.active_workers.append(worker)

    @staticmethod
    def get_worker(job: Job):
        if job.action_type in [
            ActionType.FORCE_CHECK,
            ActionType.CHECK_FILMS,
            ActionType.CHECK_SERIALS,
            ActionType.CHECK
        ]:
            return TorrentSearchWorker(job)
        elif job.action_type in [
            ActionType.DOWNLOAD_TORREN
        ]:
            return DownloadWorker(job)


class CrawlerMessageHandler:
    """
    Класс обрабатывает сообщения от компонентов и возвращает список данных для обработки
    """

    def __init__(self, db_manager: DbManager):
        self.db_manager = db_manager

    def get_job_list(self, message: MediatorActionMessage) -> list:
        result = []
        db = self.db_manager
        data = message.data
        media = []
        if not data.media_id == 0:
            media = [db.find_media(data.media_id, data.media_type, data.season)]
        elif not data.media_type == MediaType.BASE_MEDIA:
            media = db.find_all_media(data.media_type)
        if len(media)==0:
            logger.error('Не удалось найти данные в базе по запросу {}'.format(message.data))

        for element in media:

            try:
                season = element.season
            except AttributeError:
                season = ''

            result.append(
                Job(
                    **{
                        'type': message.action,
                        'client_id': data.client_id,
                        'media_id': data.media_id,
                        'title': element.label,
                        'season': season,
                        'year': element.year,
                        'download_url': element.download_url,
                        'torrent_tracker': element.torrent_tracker,
                        'theam_id': element.theam_id,
                    }
                )
            )

        return result


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
