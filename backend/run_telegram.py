import sys
import logging
from dotenv import load_dotenv

from backend.telegram_bot import create_bot_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("aura.run_telegram")


def main():
    load_dotenv(override=True)
    app = create_bot_app()
    if app is None:
        # Exit cleanly if token is not set, as required by the spec
        sys.exit(0)

    print("Starting AURA Telegram Bot (polling mode)... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
