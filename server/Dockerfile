FROM python:3.14-slim
WORKDIR /srv/repaintko
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --create-home repaintko
COPY app /srv/repaintko/app
COPY server /srv/repaintko/server
USER repaintko
ENV HOST=0.0.0.0 PORT=8765 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "-m", "server.main"]
