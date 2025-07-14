import logging
from dotenv import load_dotenv
from utils.util_functions import setup_defaults, get_logger

load_dotenv()
setup_defaults()

logger = get_logger()


def main():
    logger.info("Hello from dialogue-agent!")


if __name__ == "__main__":
    main()
