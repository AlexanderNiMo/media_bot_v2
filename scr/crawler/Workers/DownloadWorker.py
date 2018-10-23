import logging
from crawler.Workers.WorkerABC import Worker
from crawler.Workers.TorrentTrackers import download
from mediator import send_message
from app_enums import ComponentType
from database import DbManager
from os import path

logger = logging.getLogger(__name__)


class DownloadWorker(Worker):
    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start download worker.')
        data = download(self.config, self.job.download_url)

        if self.job.season == '':
            dir_path = self.config.TORRENT_SERIAL_PATH
        else:
            dir_path = self.config.TORRENT_FILM_PATH

        download_path = path.join(dir_path, '{}.torrent'.format(data['id']))
        with open(download_path, 'wb') as file:
            file.write(data['data'])
        logger.debug('End download worker.')

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
        if not self.job.client_id == '':
            result.append(self.job.client_id)

        for user in db_manager.get_users_for_notification():
            result.append(user.client_id)

        return result


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
    }), config)

    d.work()
