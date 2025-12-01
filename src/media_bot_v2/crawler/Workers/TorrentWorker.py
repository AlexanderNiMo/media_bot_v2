import logging
from typing import List
from queue import Empty
import time

from media_bot_v2.mediator import send_message, command_message, crawler_message
from media_bot_v2.app_enums import ComponentType, ClientCommands, LockingStatus, MediaType, ActionType
from media_bot_v2.crawler.Workers.WorkerABC import Worker
from media_bot_v2.crawler.Workers.TorrentTrackers import search, Torrent
from media_bot_v2.config import TorrentTrackersConfig

from .utils import add_media_keys, construct_upd_data

logger = logging.getLogger(__name__)


class TorrentSearchWorker(Worker):
    """
    Класс реализует логику поиска торрентов в трекерах

    """

    def __init__(self, job, config: TorrentTrackersConfig):
        super(TorrentSearchWorker, self).__init__(job, config)
        self.serial_torrents = 8

    def get_target(self):
        return self.work

    def work(self):
        logger.debug('Start torrent worker.')
        data = search(self.config, self.job.text_query)
        self.returned_data.put(self.get_best_match(data))
        logger.debug('Torrent worker ended.')

    def get_best_match(self, data: List[Torrent]):

        if len(data) == 0:
            return None

        f_list = [lambda x: not x.kinopoisk_id == '']
        f_data = filter(lambda x: not x.kinopoisk_id == '', data)

        if len(list(f_data)) > 5 or len(list(f_data)) >= len(data) / 2:
            if not self.job.media_id == -1:
                f_list.append(lambda x: x.kinopoisk_id == self.job.media_id)

        if self.job.season == '':
            f_list.append(lambda x: x.file_amount < 4)
            f_list.append(lambda x: x.size <= float(15))
            f_list.append(lambda x: x.size >= float(3.5))

        sound_f = lambda x: 'RUSSIAN' in x.sound
        if len(list(filter(sound_f, data))) != 0 or len(data) == 1:
            f_list.append(sound_f)

        f_list.append(lambda x: not x.with_advertising)

        result = data
        for filter_func in f_list:
            new_data = list(filter(filter_func, result))
            result = new_data

        if len(list(result)) == 0:
            current_year = int(time.asctime().split(' ')[-1])
            # Если это старый фильм\сериал возможно, что нет стандартного качества, будем предлагать выбор
            if self.job.year < current_year - 15:
                result = data
            else:
                return None

        s_data = sorted(list(result), key=lambda x: x.pier, reverse=True)
        res = list(s_data)

        return res[0:self.serial_torrents]

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
    if len(data) == 1:
        return film_success_message(data.pop(), job)
    else:
        return serial_success_message(data, job)


def film_success_message(data, job):

    dwld_data = {}
    add_media_keys(job, dwld_data)

    upd_data = {
        'download_url': data.url,
        'theam_id': data.theam_url,
        'torrent_tracker': data.tracker,
    }
    command_data = construct_upd_data(job, upd_data)

    command_data.update({
       'next_messages': [
        crawler_message(
            ComponentType.CRAWLER,
            job.client_id,
            dwld_data,
            ActionType.DOWNLOAD_TORRENT
        )
       ],
    })

    return command_message(
        ComponentType.CRAWLER,
        ClientCommands.UPDATE_MEDIA,
        command_data,
        job.client_id
    )


def serial_success_message(data, job):

    action_name = 'select_torrent'

    choice_list = []
    a = 0
    for elem in data:
        call_back_data = {}
        add_media_keys(job, call_back_data)
        call_back_data.update(
            {
                'action': action_name,
                'download_url': elem.url,
                'theam_id': elem.theam_url,
                'torrent_tracker': elem.tracker,
            }
        )

        choice_list.append(
            {
                'message_text': '{0}'.format(elem.theam_url),
                'button_text': str(a),
                'call_back_data': call_back_data
            }
        )
        a += 1

    choices = {
        'action': action_name,
        'data': choice_list
    }

    return send_message(
        ComponentType.PARSER,
        {
         'user_id': job.client_id,
         'message_text': f'Уточни какой именно торрент стоит скачать по запросу {job.text_query} '
                         f'(звук, качество и т.д.).',
         'choices': choices
        }
    )


if __name__ == '__main__':
    pass
