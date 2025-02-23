import logging
from rich.logging import RichHandler


def setup_logging(verbose=False):
    """Set up logging configuration with RichHandler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    logger = logging.getLogger("research_bot")
    logger.setLevel(level)
    return logger
