from eggy.eggy import Eggy
from eggy import settings
import asyncore

if __name__ == "__main__":
    bot = Eggy()
    bot.connect(settings.SERVER)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        bot.logger.error("Keyboard interrupt")
    except Exception as exn:
        bot.logger.error("Unhandled exception "+str(type(exn)))
        bot.logger.error(str(exn))
