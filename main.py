import sys
from os import path

sys.path.append(path.join(path.dirname(__file__), "src"))

if __name__ == "__main__":
    """
    Осуществляет тестовую сборку приложения
    """
    from media_bot_v2.app.App import start_app
    from media_bot_v2.config import parse_args, read_config

    args = parse_args()
    cfg = read_config(args.config)

    start_app(cfg)
