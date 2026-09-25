import logging

from ytkb.core import celery

logger = logging.getLogger(__name__)

@celery.app.task
def hello():
    print("hello")