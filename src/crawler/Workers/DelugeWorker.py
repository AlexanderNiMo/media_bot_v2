from deluge_client import DelugeRPCClient, FailedToReconnectException
import logging
import time
import base64
import math
from queue import Empty

from src.app import config
from src.app_enums import ComponentType, ClientCommands, MediaType, ActionType
from src.mediator import command_message, crawler_message, send_message, MediatorMessage
from src.crawler.Workers.WorkerABC import Worker

logger = logging.getLogger(__name__)


class DelugeWorker(Worker):

    def get_target(self):
        if self.job.action_type.value == ActionType.ADD_TORRENT_TO_TORRENT_CLIENT.value:
            return self.add_torrent
        elif self.job.action_type.value == ActionType.ADD_TORRENT_WATCHER.value:
            return self.work

    @staticmethod
    def get_deluge_client():
        try:
            deluge = DelugeRPCClient(
                config.DELUGE_HOST,
                config.DELUGE_PORT,
                config.DELUGE_USER,
                config.DELUGE_PASS)
            deluge.connect()
            if not deluge.connected:
                raise FailedToReconnectException
        except FailedToReconnectException:
            logger.error('Не удалось соединиться с торрент торрент клиентом')
            return None
        return deluge

    def add_torrent(self):
        deluge = self.get_deluge_client()
        if deluge is None:
            return
        if self.job.season == '':
            dir_path = self.config.TORRENT_FILM_PATH
        else:
            dir_path = self.config.TORRENT_SERIAL_PATH
        torrent_options = {'download_location': dir_path}

        torrend_data = base64.encodebytes(self.job.crawler_data.torrent_data)
        torrent_file_name = '{}.torrent'.format(self.job.torrent_id)
        torrent_id = deluge.call('core.add_torrent_file', torrent_file_name, torrend_data, torrent_options)
        self.returned_data.put({'torrent_id': torrent_id})

    def work(self):
        deluge = self.get_deluge_client()
        if deluge is None:
            return
        do = True
        start_time = time.time()
        first_time = True
        while do:
            data = deluge.call('core.get_torrents_status', {'id': self.job.torrent_id}, [
                'progress',
                'total_done',
                'total_size'
            ])
            torr_dict = data[bytes(self.job.torrent_id, 'utf-8')]
            torrent_information = {
                'progress': int(torr_dict[b'progress']),
                'total_done': torr_dict[b'total_done'],
                'total_size': torr_dict[b'total_size'],
            }
            if self.job.crawler_data.force:
                self.returned_data.put({'torrent_information': torrent_information})
                break
            if first_time:
                self.returned_data.put({'torrent_information': torrent_information})
                first_time = False
            if torrent_information['progress'] == 100:
                self.returned_data.put({'torrent_information': torrent_information})
                break
            if time.time() - start_time == 60 * 60:
                break
            time.sleep(60 * 5)

    @property
    def result(self):
        messages = []
        try:
            data = self.returned_data.get(block=False)
        except Empty:
            data = None
        if data is None:
            return []

        if 'torrent_id' in data.keys():
            messages.append(self.start_torrent_watcher_message(data))
        if 'torrent_information' in data.keys():
            messages += self.watcher_messages(data)

        return messages

    def watcher_messages(self, data):
        messages = []
        torrent_inform = data['torrent_information']
        if torrent_inform['progress'] == 100:
            message_text = 'Скачивание {} завершено, беги скорей на плекс.'.format(self.job.text_query)
            choices = []
            messages += [
                command_message(
                    ComponentType.CRAWLER,
                    ClientCommands.UPDATE_PLEX_LIB,
                    {},
                    self.job.client_id
                )
            ]
        else:
            message_text = 'Прогресс скачивания {0}: {1}% {2}/{3}'.format(
                self.job.text_query,
                torrent_inform['progress'],
                convert_size(torrent_inform['total_done']),
                convert_size(torrent_inform['total_size']),
            )
            if 'key_board' in self.job.crawler_data.data.keys() and not self.job.crawler_data.data['key_board']:
                choices = []
            else:
                choices = {
                    'action': 'download_callback',
                    'data': {
                        'force': True,
                        'media_id': self.job.media_id
                    }
                }
        messages.append(
            send_message(
                ComponentType.CRAWLER,
                {
                    'user_id': self.job.client_id,
                    'message_text': message_text,
                    'choices': choices
                }
            )
        )
        return messages

    def start_torrent_watcher_message(self, data)->MediatorMessage:
        return command_message(
                ComponentType.CRAWLER,
                ClientCommands.UPDATE_MEDIA,
                {
                    'media_id': self.job.media_id,
                    'media_type': MediaType.FILMS if self.job.season == '' else MediaType.SERIALS,
                    'next_messages': [
                        crawler_message(
                            ComponentType.COMMAND_HANDLER,
                            self.job.client_id,
                            {'media_id': self.job.media_id},
                            ActionType.ADD_TORRENT_WATCHER
                        )
                    ],
                    'upd_data': {
                        'torrent_id': data['torrent_id'],
                    },
                },
                self.job.client_id
            )


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
