FROM python:3.12
WORKDIR /usr/src/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv
COPY ./backend .
RUN uv sync
EXPOSE 80
