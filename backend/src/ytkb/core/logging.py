import logging
import sys

from ytkb.core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
        ],
        level=getattr(logging, settings.log_level.upper()),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )
