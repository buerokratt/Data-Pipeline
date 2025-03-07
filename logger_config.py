import logging

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("app.log", mode="a"),  # Save logs to file
    ],
)

# Create a reusable logger instance
def get_logger(name):
    return logging.getLogger(name)