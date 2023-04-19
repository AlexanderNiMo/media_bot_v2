import requests


def download_data(path: str):
    host = 'https://datasets.imdbws.com/'
    files = [
        'name.basics.tsv.gz',
        'title.akas.tsv.gz',
        'title.basics.tsv.gz',
        'title.crew.tsv.gz',
        'title.episode.tsv.gz',
        'title.principals.tsv.gz',
        'title.ratings.tsv.gz',
    ]
    for file in files:
        url = host+file
        r = requests.get(url)
        with open(path+file, r'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def main():
    download_data('/home/alex/scripts/mediabot/media_bot_v2/imdb_data/')


main()
