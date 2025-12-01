#! /bin/fish
export imdb_data_path=/home/alex/scripts/mediabot/imdb_data/

for f_name in (cat $imdb_data_path/file_names); curl https://datasets.imdbws.com/$f_name -o $imdb_data_path/$f_name; end;
s32cinemagoer.py $imdb_data_path postgres://imdb_user:pg_password@localhost:6432/imdb
