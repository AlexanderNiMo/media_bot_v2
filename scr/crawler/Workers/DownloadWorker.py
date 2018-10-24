import logging
from scr.crawler.Workers.WorkerABC import Worker
from scr.crawler.Workers.TorrentTrackers import download
from scr.mediator import send_message
from scr.app_enums import ComponentType
from scr.database import DbManager
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
        return messages

    def get_clients_for_notification(self)->list:
        db_manager = DbManager(self.config)
        result = []
        if not self.job.client_id == '':
            result.append(self.job.client_id)

        for user in db_manager.get_users_for_notification(self.job.media_id):
            result.append(user.client_id)

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
