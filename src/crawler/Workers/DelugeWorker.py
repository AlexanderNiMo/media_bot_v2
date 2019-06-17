import logging
import time
import base64
import math
from queue import Empty

from src.app.app_config import default_conf as config
from src.app_enums import ComponentType, ClientCommands, ActionType
from src.mediator import command_message, crawler_message, send_message, MediatorMessage
from src.crawler.Workers.WorkerABC import Worker

from .utils import add_media_keys, construct_upd_data

logger = logging.getLogger(__name__)


class TorrentWorker(Worker):

    def get_target(self):
        if self.job.action_type.value == ActionType.ADD_TORRENT_TO_TORRENT_CLIENT.value:
            return self.add_torrent
        elif self.job.action_type.value == ActionType.ADD_TORRENT_WATCHER.value:
            return self.work

    @property
    def result(self):
        messages = []
        try:
            data = self.returned_data.get(block=False)
        except Empty:
            data = None
        if data is None:
            return []

        logger.debug('Получен не пустой результат работы Worker {}'.format(self.__class__.__name__))

        if 'torrent_id' in data.keys():
            messages.append(start_torrent_watcher_message(self.job, data))
        if 'torrent_information' in data.keys():
            messages += watcher_messages(self.job, data)

        return messages

    def add_torrent(self):
        pass

    def work(self):
        pass


class DelugeWorker(TorrentWorker):

    @staticmethod
    def get_deluge_client():
        from deluge_client import DelugeRPCClient, FailedToReconnectException
        try:
            deluge = DelugeRPCClient(
                config.DELUGE_HOST,
                int(config.DELUGE_PORT),
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


class TransmissionWorker(TorrentWorker):

    def get_transmission_client(self):
        import transmissionrpc

        try:
            transmission = transmissionrpc.Client(
                config.DELUGE_HOST,
                int(config.DELUGE_PORT),
                config.DELUGE_USER,
                config.DELUGE_PASS)
        except transmissionrpc.TransmissionError:
            logger.error('Не удалось соединиться с торрент торрент клиентом')
            return None
        return transmission

    def add_torrent(self):
        transmission = self.get_transmission_client()
        if transmission is None:
            return

        if self.job.season == '':
            dir_path = self.config.TORRENT_FILM_PATH
        else:
            dir_path = self.config.TORRENT_SERIAL_PATH

        torrent_options = {'download_dir': dir_path}

        torrent = transmission.add_torrent(base64.encodebytes(self.job.crawler_data.torrent_data), *torrent_options)
        torrent.update()

        self.returned_data.put({'torrent_id': torrent.id})

    def work(self):

        transmission = self.get_transmission_client()
        if transmission is None:
            return
        do = True
        start_time = time.time()
        first_time = True
        while do:
            torrent = transmission.get_torrent(self.job.torrent_id)
            torrent.update()

            torrent_information = {
                'progress': int(torrent.id),
                'total_done': torrent._fields['sizeWhenDone'].value,
                'total_size': torrent._fields['leftUntilDone'].value,
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


def watcher_messages(job, data):
    messages = []
    torrent_inform = data['torrent_information']
    if torrent_inform['progress'] == 100:
        message_text = 'Скачивание {} завершено, беги скорей на плекс.'.format(job.text_query)
        choices = []
        messages += [
            command_message(
                ComponentType.CRAWLER,
                ClientCommands.UPDATE_PLEX_LIB,
                {},
                job.client_id
            )
        ]
    else:
        message_text = 'Прогресс скачивания {0}: {1}% {2}/{3}'.format(
            job.text_query,
            torrent_inform['progress'],
            convert_size(torrent_inform['total_done']),
            convert_size(torrent_inform['total_size']),
        )
        if 'key_board' in job.crawler_data.data.keys() and not job.crawler_data.data['key_board']:
            choices = []
        else:
            data = {}
            add_media_keys(job, data)
            data.update({
                    'force': True,
            })
            choices = {
                'action': 'download_callback',
                'data': data
            }
    messages.append(
        send_message(
            ComponentType.CRAWLER,
            {
                'user_id': job.client_id,
                'message_text': message_text,
                'choices': choices
            }
        )
    )
    return messages


def start_torrent_watcher_message(job, data)->MediatorMessage:

    upd_data ={'torrent_id': data['torrent_id']}
    command_data = construct_upd_data(job, upd_data)
    data = {}
    add_media_keys(job, data)
    command_data.update({
        'next_messages': [
            crawler_message(
                ComponentType.COMMAND_HANDLER,
                job.client_id,
                data,
                ActionType.ADD_TORRENT_WATCHER
            )
            ]
    })
    return command_message(
            ComponentType.CRAWLER,
            ClientCommands.UPDATE_MEDIA,
            command_data,
            job.client_id
    )


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
