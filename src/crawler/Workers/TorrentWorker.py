import logging
from typing import List
from queue import Empty

from src.mediator import send_message, command_message, crawler_message
from src.app_enums import ComponentType, ClientCommands, LockingStatus, MediaType, ActionType
from src.crawler.Workers.WorkerABC import Worker
from src.crawler.Workers.TorrentTrackers import search, Torrent

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

        f_list = [lambda x: not x.kinopoisk_id == '']
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
        return res

    @property
    def result(self):
        try:
            data = self.returned_data.get(block=False)
        except Empty:
            data = None
        if data is None:
            if self.ended:
                logger.debug('Поиск по задаче {0} не дал результата'.format(self.job))
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

        messages = []
        cmd_message = success_message(data, self.job)
        messages.append(cmd_message)
        return messages


def success_message(data, job):
    if job.media_type == MediaType.FILMS or len(data) == 1:
        return film_success_message(data.pop(), job)
    else:
        return serial_success_message(data, job)


def film_success_message(data, job):
    return command_message(
            ComponentType.CRAWLER,
            ClientCommands.UPDATE_MEDIA,
            {
                'media_id': job.media_id,
                'media_type': MediaType.FILMS if job.season == '' else MediaType.SERIALS,
                'upd_data': {
                    'download_url': data.url,
                    'theam_id': data.theam_url,
                    'torrent_tracker': data.tracker,
                    'exsists_in_plex': True,
                },
                'next_messages': [
                    crawler_message(
                        ComponentType.CRAWLER,
                        job.client_id,
                        {
                            'media_id': job.media_id
                        },
                        ActionType.DOWNLOAD_TORRENT
                    )
                ],
            },
            job.client_id
        )


def serial_success_message(data, job):

    choice_list = []
    a = 0
    for elem in data:
        choice_list.append(
            {
                'message_text': '{0}'.format(elem.theam_url),
                'button_text': str(a),
                'call_back_data': job.media_id
            }
        )
        a += 1

    choices = {
        'action': 'select_torrent',
        'data': choice_list
    }

    return [
        send_message(
            ComponentType.PARSER,
            {
             'user_id': data.client_id,
             'message_text': 'Выбери торрент для скачивания.',
             'choices': choices
            }
        )
    ]


if __name__ == '__main__':
    pass
