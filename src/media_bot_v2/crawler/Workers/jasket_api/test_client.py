from media_bot_v2.crawler.Workers.jasket_api.client import Config, Client


def test_client():
    c = Client(Config(
        host='http://192.168.1.107',
        port=9118,
        token="ivnah9gej44e2e5e3jakari3dd9yat0n",
        indexer_name="all"
    ))
    return c


def test_search():
    c = test_client()
    c.search("Гарри Поттер")


if __name__ == '__main__':
    test_search()
