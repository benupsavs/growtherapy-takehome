# syntax=docker/dockerfile:1

FROM python:3.11.0-slim-buster

WORKDIR /python-docker
STOPSIGNAL SIGINT

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY app.py ./
COPY date date
COPY model model
COPY resource resource
COPY repo repo
COPY config.yml config.yml

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
