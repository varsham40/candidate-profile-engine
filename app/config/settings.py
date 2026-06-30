import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG")
LOG_LEVEL = os.getenv("LOG_LEVEL")
APP_NAME = os.getenv("APP_NAME")
