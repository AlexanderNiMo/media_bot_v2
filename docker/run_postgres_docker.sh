docker run --rm -d --name pg_imdb \
                             -e POSTGRES_PASSWORD=pg_password \
                             -e POSTGRES_USER=imdb_user \
                             -e POSTGRES_DB=imdb \
                             -p 6432:5432 \
                             -v /home/alex/scripts/mediabot/pg_data:/var/lib/postgresql/data \
                             postgres:17
