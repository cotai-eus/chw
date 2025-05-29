import logging
import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings

# Remover handler padrão do loguru
logger.remove()

# Configurar formato de log
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Handler para console
logger.add(
    sys.stdout,
    format=log_format,
    level="DEBUG" if settings.DEBUG else "INFO",
    colorize=True,
)

# Handler para arquivo (apenas em produção)
if settings.ENVIRONMENT == "production":
    log_file = Path("logs/app.log")
    log_file.parent.mkdir(exist_ok=True)
    
    logger.add(
        str(log_file),
        format=log_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

# Interceptar logs do uvicorn, sqlalchemy, etc.
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging():
    # Lista de loggers para interceptar
    loggers = (
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict
        if name.startswith("uvicorn") or name.startswith("sqlalchemy")
    )
    
    for uvicorn_logger in loggers:
        uvicorn_logger.handlers = [InterceptHandler()]
        uvicorn_logger.propagate = False

    # Configurar logger raiz
    logging.getLogger().handlers = [InterceptHandler()]
    logging.getLogger().setLevel(logging.INFO)

# Configurar logging ao importar
setup_logging()
