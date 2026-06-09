import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Uncomment next to save logs to file...
        # logging.FileHandler("app.log", mode="a"),
    ],
)

def get_logger(name):
    return logging.getLogger(name)