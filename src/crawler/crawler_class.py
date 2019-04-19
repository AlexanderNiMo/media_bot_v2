import logging
import time

from src.app_enums import ComponentType, ActionType
from .Workers import TorrentSearchWorker, DelugeWorker, DownloadWorker
from src.database import DbManager, MediaData
from src.mediator import AppMediatorClient, MediatorActionMessage, CrawlerData
from multiprocessing import Queue

logger = logging.getLogger(__name__)


class Media_Task:
    """
    Описывает класс даных со всеми необходимыми
    данными для передачи в процессы воркеров

    """
    def __init__(self, action_type, client_id, media: MediaData, crawler_data: CrawlerData, **kwargs):
        self.action_type = action_type
        self.client_id = client_id
        self.media = media
        self.crawler_data = crawler_data
        self.__dict__.update(**kwargs)

    def __getattr__(self, item):
        if item in self.__dict__:
            return super(Media_Task, self).__getattribute__(item)
        else:
            return getattr(self.media, item)

    @property
    def text_query(self):
        return '{0} {1} {2}'.format(
            self.title,
            self.year,
            'сезон {}'.format(self.season) if not self.season == '' else ''
        )


class Crawler(AppMediatorClient):
    CLIENT_TYPE = ComponentType.CRAWLER
    CLIENT_ACTIONS = [
        ActionType.FORCE_CHECK,
        ActionType.CHECK_FILMS,
        ActionType.CHECK_SERIALS,
        ActionType.CHECK,
        ActionType.ADD_TORRENT_WATCHER,
        ActionType.ADD_TORRENT_TO_TORRENT_CLIENT
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
            'Полученно новое сообщение. для Crawler от {0} с данными {1}'.format(
                message.from_component,
                message.data
            )
        )

        self.add_jobs(message)

    def add_jobs(self, message: MediatorActionMessage):
        logger.debug('Добавление задач, для выполнения на основании сообщения {}'.format(message))
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
        logger.debug('Проверка статуса заданий.')

        for worker in self.active_workers:
            self.messages += worker.result
        self.active_workers = list((i for i in self.active_workers if not i.ended))

    def handle_worker_results(self):
        logger.debug('Обработка результатов работы.')
        ex = None
        try:
            for elem in self.messages:
                self.send_message(elem)
        except Exception as ex:
            ex = ex
        finally:
            self.messages = []
            if ex is not None:
                raise ex

    def add_workers(self):

        while len(self.active_workers) <= self.__threads:
            if len(self.jobs) == 0:
                break
            self.add_thread(self.jobs.pop(0))

    def add_thread(self, job):
        worker = self.get_worker(job)
        worker.start()
        self.active_workers.append(worker)

    def get_worker(self, job: Media_Task):
        if job.action_type.value in [
            ActionType.FORCE_CHECK.value,
            ActionType.CHECK_FILMS.value,
            ActionType.CHECK_SERIALS.value,
            ActionType.CHECK.value
        ]:
            return TorrentSearchWorker(job, self.config)
        elif job.action_type.value in [
            ActionType.ADD_TORRENT_WATCHER.value,
            ActionType.ADD_TORRENT_TO_TORRENT_CLIENT.value
        ]:
            return DelugeWorker(job, self.config)
        elif job.action_type.value in [
            ActionType.DOWNLOAD_TORRENT.value,
        ]:
            return DownloadWorker(job, self.config)


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

        session = db.get_session()
        if not data.media_id == 0:
            media = db.find_media(data.media_id, data.media_type, data.season, session)
            if media is None:
                media = []
            else:
                media = [media]
        else:
            media = db.find_all_media(data.media_type, session)
        if len(media) == 0 and not data.media_id == 0:
            logger.error('Не удалось найти данные в базе по запросу {}'.format(message.data))
            return []
        session.close()
        for element in media:

            element.torrent_id = element.torrent_id if data.torrent_id is None else data.torrent_id

            result.append(
                Media_Task(
                    **{
                        'action_type': message.action,
                        'client_id': data.client_id,
                        'media': element,
                        'crawler_data': data,
                    }
                )
            )

        return result


if __name__ == '__main__':
    from multiprocessing import Queue
    from app import config as conf

    logger = logging.getLogger()
    consol_hndl = logging.StreamHandler()
    logger.addHandler(consol_hndl)
    logger.setLevel(logging.DEBUG)

    c = Crawler(Queue(), Queue(), conf, 10)

    msg = MediatorActionMessage(ComponentType.CRAWLER, ActionType.CHECK, ComponentType.CRAWLER)
    msg.data = CrawlerData(123109378, 577266)

    c.add_jobs(msg)
    c.update_jobs()
    c.start()
