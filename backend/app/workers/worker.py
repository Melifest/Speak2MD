import os
import time
import logging

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")

POLL = float(os.getenv("POLL_INTERVAL_SEC", "2.0"))

def main():
    logger.info("Worker started (skeleton). Implement real job processing here.")
    try:
        while True:
            logger.debug("Worker idle... (poll=%ss)", POLL)
            time.sleep(POLL)
    except KeyboardInterrupt:
        logger.info("Worker stopped by KeyboardInterrupt")

if __name__ == "__main__":
    main()
