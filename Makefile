.PHONY=docker

docker:
    docker build -t media_bot -f ./docker/dockerfile .