import deluge_client
import logging
import time
import base64
from queue import Empty


from src.app import config
from src.app_enums import ComponentType, ClientCommands,MediaType,ActionType
from src.mediator import command_message, crawler_message, send_message
from src.crawler.Workers.WorkerABC import Worker

logger = logging.getLogger(__name__)


class DelugeWorker(Worker):

    def get_target(self):
        if self.job.action_type.value == ActionType.ADD_TORRENT_TO_TORRENT_CLIENT:
            return self.add_torrent
        elif self.job.action_type.value == ActionType.ADD_TORRENT_WATCHER:
            return self.work

    def get_deluge_client(self)->deluge_client.DelugeRPCClient:
        try:
            deluge = deluge_client.DelugeRPCClient(
                config.DELUGE_HOST,
                config.DELUGE_PORT,
                config.DELUGE_USER,
                config.DELUGE_PASS)
            deluge.connect()
            if not deluge.connected:
                raise deluge_client.FailedToReconnectException
        except deluge_client.FailedToReconnectException:
            logger.error('Не удалось соединиться с торрент торрент клиентом')
            return None
        return deluge

    def add_torrent(self):
        deluge = self.get_deluge_client()
        if deluge is None:
            return
        if self.job.season == '':
            dir_path = self.config.TORRENT_SERIAL_PATH
        else:
            dir_path = self.config.TORRENT_FILM_PATH
        torrent_options = {'download_location': dir_path}

        torrend_data = base64.b64decode(self.job.torren_data)
        torrent_file_name = '{}.torrent'.format(self.job.torrent_id)
        torrent_id = deluge.call('core.add_torrent_file', torrent_file_name, torrend_data, torrent_options)
        self.returned_data.put({'torrent_id': torrent_id})

    def work(self):
        deluge = self.get_deluge_client()
        if deluge is None:
            return
        do = True
        start_time = time.time()
        while do:
            if time.time() - start_time == 60*60:
                break
            time.sleep(60*5)
            data = deluge.call('core.get_torrents_status', {'id': self.job.torrent_id}, ['progress'])
            self.returned_data.put({'progress': data})

    @property
    def result(self):
        messages = []
        try:
            data = self.returned_data.get(False, timeout=2)
        except Empty:
            data = None
        if data is None:
            return []

        if 'torrent_id' in data.keys():
            cmd_message = command_message(
                ComponentType.CRAWLER,
                ClientCommands.UPDATE_MEDIA,
                {
                    'media_id': self.job.media_id,
                    'media_type': MediaType.FILMS if self.job.season == '' else MediaType.SERIALS,
                    'next_message': crawler_message(
                        ComponentType.COMMAND_HANDLER,
                        self.job.client_id,
                        {'media_id': self.job.media_id},
                        ActionType.ADD_TORRENT_WATCHER
                    ),
                    'upd_data': {
                        'torrent_id': data['torrent_id'],
                    },
                },
                self.job.client_id
            )
            messages.append(cmd_message)
        if 'progress' in data.keys():
            if data['progress'] == 100:
                message_text = 'Скачивание {} завершено, беги скорей на плекс.'.format(self.job.text_query)
            else:
                message_text = 'Прогресс скачивания {0}: {1}%'.format(self.job.text_query, data['progress'])
            messages.append(
                send_message(
                    ComponentType.CRAWLER,
                    {
                        'user_id': self.job.client_id,
                        'message_text': message_text,
                        'choices': []
                    }
                )
            )

        return messages
