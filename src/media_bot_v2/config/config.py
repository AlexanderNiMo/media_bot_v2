import argparse
import json
import pathlib

from pydantic import BaseModel, Field


class ProxyConfig(BaseModel):
    url: str
    user: str | None
    password: str | None

    def build_proxy_str(self) -> str:
        if self.user is None:
            return self.url
        p_type = self.url.split("//")[0]
        p_url = self.url.split("//")[1]
        return f"{p_type}//{self.user}:{self.password}@{p_url}"


class DbConfig(BaseModel):
    dns: str
    db_name: str
    admin_id: str


class TMDBConfig(BaseModel):
    api_key: str
    proxy_cfg: ProxyConfig | None = Field(default=None)


class TelegrammConfig(BaseModel):
    admin_user: str
    bot_token: str
    mode: str
    cache_db_path: str
    proxy_cfg: ProxyConfig | None = Field(default=None)


class PlexConfig(BaseModel):
    host: str
    port: int
    token: str


class DownloadConfig(BaseModel):
    proxy_cfg: ProxyConfig | None = Field(default=None)


class AuthCfg(BaseModel):
    user_name: str
    password: str
    api_key: str|None = None


class TorrentTrackersConfig(BaseModel):
    tmp_path: pathlib.Path
    credentials: dict[str, AuthCfg]
    proxy_cfg: ProxyConfig | None = None


class TorrentClientConfig(BaseModel): ...


class Config(BaseModel):
    log_level: str
    db_cfg: DbConfig
    tg_cfg: TelegrammConfig
    download_cfg: DownloadConfig
    tracker_cfg: TorrentTrackersConfig
    tmdb_cfg: TMDBConfig
    plex_cfg: PlexConfig
    proxy_cfg: ProxyConfig


def read_config(path: pathlib.Path):
    with path.absolute().open("r") as f:
        data = json.load(f)
    c = Config(**data)
    c.tg_cfg.proxy_cfg = c.proxy_cfg
    c.download_cfg.proxy_cfg = c.proxy_cfg
    c.tracker_cfg.proxy_cfg = c.proxy_cfg

    return c


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, type=pathlib.Path)
    return parser.parse_args()
