import logging
from .WorkerABC import Worker
from .TorrentTrackers import download
from mediator import send_message
from app_enums import ComponentType
from database import DbManager

logger = logging.getLogger(__name__)


class DownloadWorker(Worker):
    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')
        download(self.config, self.job.download_url)

    @property
    def result(self):
        messages = []
        clients = self.get_clients_for_notification()
        message_text = '{0} {1} будет скачан, через несколько минут. \n {2}'.format(
            'Фильм' if self.job.season == '' else 'Сериал',
            self.job.text_query,
            self.job.kinopoisk_url
        )
        for clien in clients:
            messages.append(
                send_message(
                    ComponentType.CRAWLER,
                    {
                        'user_id': clien,
                        'message_text': message_text,
                        'choices': []
                    }
                )
            )
        return messages

    def get_clients_for_notification(self):
        db_manager = DbManager(self.config)
        result = []
        if self.job.client_id == '':
            result.append(self.job.client_id)

        for user in db_manager.get_users_for_notification():
            result.append(user.client_id)

        return result

