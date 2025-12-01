import dataclasses
import requests


@dataclasses.dataclass
class Config:
    host: str
    port: int
    token: str
    indexer_name: str


class Client:

    def __init__(self, config: Config, s: requests.Session = None):
        self.s = s if s is not None else requests.Session()
        self.config = config
        self._init_headers()

    def _init_headers(self):
        self.s.headers.update({
            "Accept": "*/*",
        })

    def _with_auth(self, params: dict) -> dict:
        data = {}
        data.update(params)
        data["apikey"] = self.config.token
        return data

    def search(self, query, **kwargs) -> list:
        rsp = self._get(self._search_endpoint(), params={
            "Query": query,
        }, **kwargs)
        data = rsp.json()
        return []

    def _api_endpoint(self):
        return "/api/v2.0/indexers"

    def _search_endpoint(self) -> str:
        return f"{self._api_endpoint()}/{self.config.indexer_name}/results"


    def _url(self, endpoint):
        return f"{self.config.host}:{self.config.port}/{endpoint}"

    def _get(self, endpoint: str, **kwargs):
        return self._do_req("GET", endpoint, **kwargs)

    def _post(self, endpoint: str, **kwargs):
        return self._do_req("POST", endpoint, **kwargs)

    def _do_req(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        p = self._with_auth(kwargs.pop('params', {}))
        return self.s.request(method, self._url(endpoint), params=p, **kwargs)