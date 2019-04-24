import logging
from queue import Empty

from src.mediator import send_message, command_message, crawler_message
from src.app_enums import ComponentType, ClientCommands, MediaType, ActionType, LockingStatus
from src.crawler.Workers.WorkerABC import Worker
from src.crawler.Workers.TorrentTrackers import download

logger = logging.getLogger(__name__)


class DownloadWorker(Worker):
    """
    Реализует логику скачивания уже известных торрентов

    """

    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')
        torrent_data = []

        media = self.job.media
        torrdata = download(self.config, media.download_url)

        if not (media.media_type == MediaType.SERIALS and torrdata.data.file_amount == media.series):
            torrent_data.append(torrdata)

        self.returned_data.put(torrent_data)
        logger.debug('Torrent worker ended.')

    @property
    def result(self):

        try:
            data = self.returned_data.get(block=False)
        except Empty:
            data = None

        if data is None:
            return []

        messages = []

        logger.debug('Получен не пустой результат работы Worker {}'.format(self.__class__.__name__))

        for torrent_data in data:
            media = self.job
            if media.media_type == MediaType.FILMS:
                message_text = 'Фильм {0} будет скачан, через несколько минут. \n {1}'.format(
                    media.text_query,
                    media.kinopoisk_url
                )
            else:
                message_text = 'Новая серия {0} () будет скачана, через несколько минут. \n {1}'.format(
                    media.text_query,
                    media.kinopoisk_url
                )
            if self.job.season == '':
                status = LockingStatus.ENDED
            elif not self.job.max_series == 0 and data.file_amount == self.job.max_series:
                status = LockingStatus.ENDED
            else:
                status = LockingStatus.FIND_TORRENT

            messages.extend([
                command_message(
                    ComponentType.CRAWLER,
                    ClientCommands.UPDATE_MEDIA,
                    {
                        'media_id': media.media_id,
                        'media_type': MediaType.FILMS if media.season == '' else MediaType.SERIALS,
                        'upd_data': {
                            'status': status,
                            'exsists_in_plex': True,
                            'current_series': 0 if media.season == '' else torrent_data.file_amount
                        }
                    },
                    self.job.client_id
                ),
                crawler_message(
                    ComponentType.CRAWLER,
                    media.client_id,
                    {
                        'torrent_id': torrent_data['id'],
                        'torrent_data': torrent_data['data'],
                        'media_id': media.media_id
                    },
                    ActionType.ADD_TORRENT_TO_TORRENT_CLIENT
                ),
                command_message(
                    ComponentType.CRAWLER,
                    ClientCommands.SEND_MESSAGES_BY_MEDIA,
                    {
                        'media_id': media.media_id,
                        'message_text': message_text,
                        'choices': []
                    },
                    self.job.client_id
                )
            ])

        return messages


