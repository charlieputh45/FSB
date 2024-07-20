FROM python:3.10.13
WORKDIR /app

RUN apt-get update && apt-get install -y git ffmpeg

RUN mv /usr/bin/ffmpeg /usr/bin/zender

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD sh start.sh
