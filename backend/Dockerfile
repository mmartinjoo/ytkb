FROM python:3.12
WORKDIR /usr/src/app
RUN pip install uv
COPY ./backend .
RUN uv sync
EXPOSE 80
