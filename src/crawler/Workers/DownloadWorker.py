import logging
from os import path
from queue import Empty

from src.crawler.Workers.WorkerABC import Worker
from src.crawler.Workers.TorrentTrackers import download
from src.mediator import send_message, crawler_message
from src.app_enums import ComponentType
from src.database import DbManager


logger = logging.getLogger(__name__)


class DownloadWorker(Worker):
    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start download worker.')
        data = download(self.config, self.job.download_url)

        self.add_torrent_to_torrent_client(data)

        logger.debug('End download worker.')

    def add_torrent_to_torrent_client(self, data):

        if self.job.season == '':
            dir_path = self.config.TORRENT_SERIAL_PATH
        else:
            dir_path = self.config.TORRENT_FILM_PATH

        download_path = path.join(dir_path, '{}.torrent'.format(data['id']))
        with open(download_path, 'wb') as file:
            file.write(data['data'])

        self.returned_data.put(data)

    @property
    def result(self):
        if not self.ended:
            return []
        try:
            data = self.returned_data.get(False, timeout=2)
        except Empty:
            data = None

        messages = []
        clients = self.get_clients_for_notification()
        if self.job.season == '':
            message_text = 'Фильм {0} будет скачан, через несколько минут. \n {1}'.format(
                self.job.text_query,
                self.job.kinopoisk_url
            )
        else:
            message_text = 'Новая серия {0} () будет скачана, через несколько минут. \n {1}'.format(
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
        messages.append(
            crawler_message(
                ComponentType.CRAWLER,
                self.job.client_id,
                {
                    'torrent_id': data['id'],
                    'torrent_data': data['data'],
                    'media_id': self.job.media_id
                }
            )
        )

        return messages

    def get_clients_for_notification(self)->list:
        db_manager = DbManager(self.config)
        result = []
        if not self.job.client_id == '':
            result.append(self.job.client_id)
        session = db_manager.session
        for user in db_manager.get_users_for_notification(self.job.media_id, session):
            result.append(user.client_id)
        session.close()
        return list(set(result))


if __name__ == '__main__':

    from app import config
    from crawler.crawler_class import Job

    d = DownloadWorker(Job(**{
        'action_type': None,
        'client_id': 123109378,
        'media_id': 571884,
        'title': 'Гарри Поттер и философский камень',
        'year': 2001,
        'torrent_tracker': '',
        'theam_id': '',
        'kinopoisk_url': 'https://www.kinopoisk.ru/film/689/',
        'download_url': 'http://d.rutor.info/download/659488',
        'season': '',
        'text_query': 'Гарри Поттер и Орден Феникса',
        'max_series': 0,
    }), config)

    d.work()
