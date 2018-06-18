import logging
from eplitefrontend import app


formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
)

handler = logging.FileHandler("../../var/log/eplitefrontend.log")
handler.setLevel(logging.WARN)
handler.setFormatter(formatter)

app.logger.addHandler(handler)
