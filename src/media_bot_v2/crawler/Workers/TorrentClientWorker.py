import logging
import time
import base64
import math
from queue import Empty

from media_bot_v2.app.app_config import default_conf as config
from media_bot_v2.app_enums import ComponentType, ClientCommands, ActionType, MediaType
from media_bot_v2.mediator import command_message, crawler_message, send_message, MediatorMessage
from media_bot_v2.crawler.Workers.WorkerABC import Worker

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
        client = self.get_client()
        if client is None:
            self.save_file_to_folder()
            return
        if self.job.season == '':
            dir_path = self.config.TORRENT_FILM_PATH
        else:
            dir_path = self.config.TORRENT_SERIAL_PATH

        torrent_id = self._add_torrent(client, dir_path)

        self.returned_data.put({'torrent_id': torrent_id})

    def work(self):
        client = self.get_client()
        if client is None:
            return
        do = True
        start_time = time.time()
        first_time = True
        while do:

            torrent_information = self._get_torrent_information(client)

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

    def save_file_to_folder(self):

        dir_path = self.config.TORRENT_DOWNLOAD_FILM_PATH
        if self.job.media.media_type == MediaType.SERIALS:
            dir_path = self.config.TORRENT_DOWNLOAD_SERIAL_PATH

        with open(f'{dir_path}{self.job.torrent_id}', 'wb') as file:
            file.write(self.job.crawler_data.torrent_data)

    def _get_torrent_information(self, client):
        pass

    @staticmethod
    def get_client():
        pass

    def _add_torrent(self, client, dir_path):
        pass


class DelugeWorker(TorrentWorker):

    @staticmethod
    def get_client():
        from deluge_client import DelugeRPCClient, FailedToReconnectException
        try:
            deluge = DelugeRPCClient(
                config.TORRENT_HOST,
                int(config.TORRENT_PORT),
                config.TORRENT_USER,
                config.TORRENT_PASS)
            deluge.connect()
            if not deluge.connected:
                raise FailedToReconnectException
        except FailedToReconnectException:
            logger.error('Не удалось соединиться с торрент торрент клиентом')
            return None
        return deluge

    def _add_torrent(self, client, dir_path):

        torrent_options = {'download_location': dir_path}

        torrend_data = base64.encodebytes(self.job.crawler_data.torrent_data)
        torrent_file_name = '{}.torrent'.format(self.job.torrent_id)
        torrent_id = client.call('core.add_torrent_file', torrent_file_name, torrend_data, torrent_options)
        return torrent_id

    def _get_torrent_information(self, client):
        data = client.call('core.get_torrents_status', {'id': self.job.torrent_id}, [
                'progress',
                'total_done',
                'total_size'
            ])
        torr_dict = data[bytes(self.job.torrent_id, 'utf-8')]
        return {
            'progress': int(torr_dict[b'progress']),
            'total_done': torr_dict[b'total_done'],
            'total_size': torr_dict[b'total_size'],
        }


class TransmissionWorker(TorrentWorker):

    def get_client(self):
        import transmissionrpc

        try:
            transmission = transmissionrpc.Client(
                config.TORRENT_HOST,
                int(config.TORRENT_PORT),
                config.TORRENT_USER,
                config.TORRENT_PASS)
        except transmissionrpc.TransmissionError:
            logger.error('Не удалось соединиться с торрент торрент клиентом')
            return None
        return transmission

    def _add_torrent(self, client, dir_path):

        torrent_options = {'download_dir': dir_path}

        torrent = client.add_torrent(base64.encodebytes(self.job.crawler_data.torrent_data), *torrent_options)
        torrent.update()

        return torrent.id

    def _get_torrent_information(self, client):
        torrent = client.get_torrent(self.job.torrent_id)
        torrent.update()

        return {
            'progress': int(torrent.progress),
            'total_done': torrent._fields['sizeWhenDone'].value,
            'total_size': torrent._fields['leftUntilDone'].value,
        }


class QBitTorrent(TorrentWorker):

    def get_client(self):
        from qbittorrent import Client
        from requests import ConnectionError

        try:
            q_bit = Client(f'http://{config.TORRENT_HOST}:{int(config.TORRENT_PORT)}')
            res = q_bit.login(username=config.TORRENT_USER, password=config.TORRENT_PASS)
            if res == 'Fails.':
                logger.error('Неверный пароль или логин для подключения к qBitTorrent')
                raise ConnectionError
        except ConnectionError:
            logger.error('Ошибка подключения к qBitTorrent')
            return None

        return q_bit

    def _add_torrent(self, client, dir_path):
        import io

        torrent_hash = self.get_torr_info_hash(self.job.crawler_data.torrent_data)
        torrent_io = io.BytesIO(self.job.crawler_data.torrent_data)

        client.download_from_file(torrent_io, savepath=dir_path)

        return torrent_hash

    def _get_torrent_information(self, client):
        torrent = client.get_torrent(self.job.torrent_id)

        total_downloaded = torrent['total_downloaded']
        size = torrent['total_size']
        left = size - total_downloaded

        progress = 100.0 * (size - left) / float(size)

        return {
            'progress': int(progress),
            'total_done': total_downloaded,
            'total_size': size,
        }

    @staticmethod
    def get_torr_info_hash(data):
        import hashlib, bencoding
        bencode_dict = bencoding.bdecode(data)
        return hashlib.sha1(bencoding.bencode(bencode_dict[b"info"])).hexdigest()


def get_torrent_worker(job, data_config)-> TorrentWorker:

    torrent_client_type = int(data_config.TORRENT_TYPE)

    if torrent_client_type == 0:
        return DelugeWorker(job, data_config)
    elif torrent_client_type == 1:
        return TransmissionWorker(job, data_config)
    elif torrent_client_type == 2:
        return QBitTorrent(job, data_config)
    else:
        logger.error('Не удалось определить тип торрент клиента.')
        raise ValueError


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
