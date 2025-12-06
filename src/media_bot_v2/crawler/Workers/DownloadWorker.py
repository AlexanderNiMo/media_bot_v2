import logging
from queue import Empty

from media_bot_v2.mediator import send_message, command_message, crawler_message
from media_bot_v2.app_enums import ComponentType, ClientCommands, MediaType, ActionType, LockingStatus
from media_bot_v2.crawler.Workers.WorkerABC import Worker
from media_bot_v2.crawler.Workers.TorrentTrackers import download

from .utils import construct_upd_data, add_media_keys

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
        try:
            media = self.job.media
            torrdata = download(self.config.tracker_cfg, media.download_url)

            if torrdata['file_amount'] == 0 or not (media.media_type.value == MediaType.SERIALS.value and (torrdata['file_amount'] == media.current_series)):
                torrent_data.append(torrdata)

            self.returned_data.put(torrent_data)
        except Exception:
            logger.exception('Error on worker!')
            return    
        logger.debug('Torrent worker ended.')

    @property
    def result(self):

        try:
            data = self.returned_data.get(block=False)
        except Empty:
            data = None

        if data is None:
            return []

        if not isinstance(data, list):
            return []

        logger.debug('Получен не пустой результат работы Worker {}'.format(self.__class__.__name__))

        messages = self.construct_messages(data)

        return messages

    def construct_messages(self, data):
        messages = []
        for torrent_data in data:
            media = self.job

            if media.media_type.value == MediaType.FILMS.value:
                message_text = 'Фильм "{0}" будет скачан, через несколько минут. \n {1}'.format(
                    media.text_query,
                    media.kinopoisk_url
                )
                status = LockingStatus.ENDED
            else:
                message_text = 'Новая серия "{0}" будет скачана, через несколько минут. \n {1}'.format(
                    media.text_query,
                    media.kinopoisk_url
                )

                if self.job.current_series == torrent_data['file_amount']:
                    return []

                if self.job.series != 0 and torrent_data['file_amount'] >= self.job.series:
                    status = LockingStatus.ENDED
                else:
                    status = LockingStatus.FIND_TORRENT

            upd_data = {
                'status': status,
                'exsists_in_plex': True,
                'current_series': 0 if media.season == '' else torrent_data['file_amount']
            }
            command_data = construct_upd_data(media, upd_data)

            send_data = {
                'choices': [],
                'message_text': message_text
            }
            add_media_keys(media, send_data)

            add_torrent_data = {
                'torrent_id': torrent_data['id'],
                'torrent_data': torrent_data['data'],
            }
            add_media_keys(media, add_torrent_data)

            messages += [
                command_message(
                    ComponentType.CRAWLER,
                    ClientCommands.UPDATE_MEDIA,
                    command_data,
                    self.job.client_id
                ),
                crawler_message(
                    ComponentType.CRAWLER,
                    media.client_id,
                    add_torrent_data,
                    ActionType.ADD_TORRENT_TO_TORRENT_CLIENT
                ),
                command_message(
                    ComponentType.CRAWLER,
                    ClientCommands.SEND_MESSAGES_BY_MEDIA,
                    send_data,
                    self.job.client_id
                )
            ]
        return messages

