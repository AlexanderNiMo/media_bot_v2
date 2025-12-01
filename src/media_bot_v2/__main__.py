from media_bot_v2.app.App import start_app
from media_bot_v2.config import parse_args, read_config

if __name__ == "__main__":
    args = parse_args()
    cfg = read_config(args.config)
    start_app(cfg)
