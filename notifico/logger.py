import logging
from rich.logging import RichHandler

log = logging.getLogger('notifico')
log.addHandler(RichHandler(markup=True))
log.setLevel(logging.INFO)
