import logging
import time
from multiprocessing import Queue
import traceback

from media_bot_v2.config import Config
from media_bot_v2.crawler.Workers.utils import MediaTask
from media_bot_v2.app_enums import ComponentType, ActionType
from media_bot_v2.database import DbManager
from media_bot_v2.mediator import AppMediatorClient, MediatorActionMessage

from .Workers import TorrentSearchWorker, DownloadWorker, get_torrent_worker


logger = logging.getLogger(__name__)


class Crawler(AppMediatorClient):
    CLIENT_TYPE = ComponentType.CRAWLER
    CLIENT_ACTIONS = [
        ActionType.FORCE_CHECK,
        ActionType.CHECK_FILMS,
        ActionType.CHECK_SERIALS,
        ActionType.CHECK,
        ActionType.ADD_TORRENT_WATCHER,
        ActionType.ADD_TORRENT_TO_TORRENT_CLIENT,
        ActionType.DOWNLOAD_TORRENT
    ]

    def __init__(self, in_queue: Queue, out_queue: Queue, config: Config, threads: int):

        super(Crawler, self).__init__(in_queue, out_queue, config)

        self.__threads = threads
        self.active_workers = []
        self.jobs = []
        db_manager = DbManager(config.db_cfg)
        self.db_handler = CrawlerMessageHandler(db_manager)
        self.messages = []

    def main_actions(self):
        logger.info('Запуск основного потока работы {}'.format(self))
        while True:
            time.sleep(10)
            try:
                self.update_jobs()
            except Exception as ex:
                logging.error('При обновлении обработчиков произошла ощибка {}'.format(traceback.print_exc()))

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

        for worker in self.active_workers:
            try:
                self.messages += worker.result
            except Exception as ex:
                logger.error('При обработке результата воркера {0} произошла ошибка {1}'.format(worker, ex))
        self.active_workers = list((i for i in self.active_workers if not i.ended))

    def handle_worker_results(self):
        ex = None
        try:
            for elem in self.messages:
                self.send_message(elem)
        except Exception as ex:
            ex = ex
            logger.error('При отправке сообщения {0} произошла ошибка {1}'.format(elem, ex))
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
        logger.debug('Запуск worker {}'.format(worker))
        worker.start()
        self.active_workers.append(worker)

    def get_worker(self, job: MediaTask):
        if job.action_type.value in [
            ActionType.FORCE_CHECK.value,
            ActionType.CHECK_FILMS.value,
            ActionType.CHECK_SERIALS.value,
            ActionType.CHECK.value
        ]:
            return TorrentSearchWorker(job, self.config.tracker_cfg)
        elif job.action_type.value in [
            ActionType.ADD_TORRENT_WATCHER.value,
            ActionType.ADD_TORRENT_TO_TORRENT_CLIENT.value
        ]:
            return get_torrent_worker(job, self.config)
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

            if element.download_url is None \
                or element.download_url == '' \
                or message.action.value in (
                    ActionType.ADD_TORRENT_WATCHER.value,
                    ActionType.ADD_TORRENT_TO_TORRENT_CLIENT.value):
                action = message.action
            else:
                action = ActionType.DOWNLOAD_TORRENT

            result.append(
                MediaTask(
                    **{
                        'action_type': action,
                        'client_id': data.client_id,
                        'media': element,
                        'crawler_data': data,
                    }
                )
            )

        return result


if __name__ == '__main__':
    pass
