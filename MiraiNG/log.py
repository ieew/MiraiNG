import logging


log: logging.Logger = logging.getLogger("MiraiNG")
log_hander = logging.StreamHandler()
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    fmt="{%(asctime)s} (%(levelname)s): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log_hander.setFormatter(formatter)
log.addHandler(log_hander)