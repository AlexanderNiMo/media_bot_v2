import logging
from typing import List
from queue import Empty

from src.mediator import send_message, command_message, crawler_message
from src.app_enums import ComponentType, ClientCommands, LockingStatus, MediaType, ActionType
from src.crawler.Workers.WorkerABC import Worker
from src.crawler.Workers.TorrentTrackers import search, download, Torrent

logger = logging.getLogger(__name__)


class TorrentSearchWorker(Worker):
    """
    Класс реализует логику поиска торрентов в трекерах

    """

    def get_target(self):

        return self.work

    def work(self):
        logger.debug('Start torrent worker.')
        data = search(self.config, self.job.text_query)
        self.returned_data.put(self.get_best_match(data))
        logger.debug('Torrent worker ended.')

    def get_best_match(self, data: List[Torrent]):

        f_list = []
        f_list.append(lambda x: not x.kinopoisk_id == '')
        f_data = filter(lambda x: not x.kinopoisk_id == '', data)

        if len(list(f_data)) > 5 or len(list(f_data)) >= len(data) / 2:
            if not self.job.media_id == -1:
                f_list.append(lambda x: x.kinopoisk_id == self.job.media_id)

        if self.job.season == '':
            f_list.append(lambda x: x.file_amount < 4)
            f_list.append(lambda x: x.size <= float(15))

        result = data
        for filter_func in f_list:
            new_data = list(filter(filter_func, result))
            result = new_data

        s_data = sorted(list(result), key=lambda x: x.pier, reverse=True)
        res = list(s_data)
        if len(res) == 0:
            return None
        return res[0]

    @property
    def result(self):
        try:
            data = self.returned_data.get(block=False)
        except Empty:
            data = None
        if data is None:
            if self.ended:
                if not self.job.action_type.value == ActionType.FORCE_CHECK.value:
                    return []
                message_text = '{0} по запросу {1} не найден, ' \
                               'но я буду искать его непрестанно.'\
                    .format('Фильм' if self.job.season == '' else 'Сериал',
                            self.job.text_query)
                return [send_message(
                    ComponentType.CRAWLER,
                    {
                        'user_id': self.job.client_id,
                        'message_text': message_text,
                        'choices': []
                    }

                )]
            else:
                return []

        if self.job.season == '':
            status = LockingStatus.ENDED
        elif not self.job.max_series == 0 and data.file_amount == self.job.max_series:
            status = LockingStatus.ENDED
        else:
            status = LockingStatus.FIND_TORRENT

        if self.job.media.media_type == MediaType.FILMS:
            message_text = 'Фильм {0} будет скачан, через несколько минут. \n {1}'.format(
                self.job.text_query,
                self.job.kinopoisk_url
            )
        else:
            message_text = 'Новая серия {0} () будет скачана, через несколько минут. \n {1}'.format(
                self.job.text_query,
                self.job.kinopoisk_url
            )

        messages = []
        cmd_message = command_message(
            ComponentType.CRAWLER,
            ClientCommands.UPDATE_MEDIA,
            {
                'media_id': self.job.media_id,
                'media_type': MediaType.FILMS if self.job.season == '' else MediaType.SERIALS,
                'upd_data': {
                    'status': status,
                    'download_url': data.url,
                    'theam_id': data.theam_url,
                    'torrent_tracker': data.tracker,
                    'exsists_in_plex': True,
                    'current_series': 0 if self.job.season == '' else data.file_amount
                },
                'next_messages': [
                    crawler_message(
                        ComponentType.CRAWLER,
                        self.job.client_id,
                        {
                            'torrent_id': data.data['id'],
                            'torrent_data': data.data['data'],
                            'media_id': self.job.media_id
                        },
                        ActionType.ADD_TORRENT_TO_TORRENT_CLIENT
                    ),
                    send_message(
                        ComponentType.CRAWLER,
                        {
                            'user_id': self.job.client_id,
                            'message_text': message_text,
                            'choices': []
                        }
                    )
                ],
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
            'max_series': 0
        }), config)

    t.start()
    while not t.ended:
        time.sleep(5)
    print(t.result)
