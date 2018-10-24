import logging
from typing import List
from queue import Empty

from scr.mediator import send_message, command_message
from scr.app_enums import ComponentType, ClientCommands, LockingStatus, MediaType, ActionType
from scr.crawler.Workers.WorkerABC import Worker
from scr.crawler.Workers.TorrentTrackers import search, download, Torrent

logger = logging.getLogger(__name__)


class TorrentSearchWorker(Worker):

    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')
        data = search(self.config, self.job.text_query)
        self.returned_data.put(self.get_best_match(data))
        logger.debug('Torrent worker ended.')

    def get_best_match(self, data: List[Torrent]):

        loc_data = filter(lambda x: not x.kinopoisk_id == '', data)

        if len(list(loc_data)) > 5 or len(list(loc_data)) >= len(data)/2:
            if not self.job.media_id == -1:
                loc_data = filter(lambda x: x.kinopoisk_id == self.job.media_id, data)
        else:
            loc_data = data

        if self.job.season == '':
            loc_data = filter(lambda x: x.file_amount < 4, loc_data)

        loc_data = sorted(loc_data, key=lambda x: x.pier)
        res = list(loc_data)
        if len(res) == 0:
            return None
        return res[0]

    @property
    def result(self):
        try:
            data = self.returned_data.get(False, timeout=2)
        except Empty:
            data = None
        if data is None:
            if not self.job.action_type.value == ActionType.FORCE_CHECK.value:
                return []
            message_text = '{0} по запросу {1} не найден, ' \
                           'но я буду искать его непрестанно.'.format(
                'Фильм' if self.job.season == '' else 'Сериал',
                self.job.text_query)
            return [send_message(
                ComponentType.CRAWLER,
                {
                    'user_id': self.job.client_id,
                    'message_text': message_text,
                    'choices': []
                }

            )]

        if self.job.season == '':
            status = LockingStatus.ENDED
        elif not self.job.max_series == 0 and data.file_amount == self.job.max_series:
            status = LockingStatus.ENDED
        else:
            status = LockingStatus.FIND_TORRENT

        messages = []
        cmd_message = command_message(
            ComponentType.CRAWLER,
            ClientCommands.UPDATE_MEDIA,
            {
                'media_id': self.job.media_id,
                'media_type': MediaType.FILMS if self.job.season == '' else MediaType.SERIALS,
                'start_download': True,
                'upd_data': {
                    'status': status,
                    'download_url': data.url,
                    'theam_id': data.theam_url,
                    'torrent_tracker': data.tracker,
                    'exsists_in_plex': True,
                    'current_series': 0 if self.job.season == '' else data.file_amount
                },
            },
            self.job.client_id
        )
        messages.append(cmd_message)
        return messages


if __name__ == '__main__':
    import time
    from app import config
    from crawler.crawler_class import Job
    import logging

    t = TorrentSearchWorker(
    Job(**{
        'action_type': None,
        'client_id': 123109378,
        'media_id': 571884,
        'title': 'Гарри Поттер и философский камень',
        'season': '',
        'year': 2001,
        'download_url': '',
        'torrent_tracker': '',
        'theam_id': '',
        'kinopoisk_url': 'https://www.kinopoisk.ru/film/571884/',
        'max_series':0
    }), config)

    t.start()
    while not t.ended:
        time.sleep(5)
    print(t.result)

