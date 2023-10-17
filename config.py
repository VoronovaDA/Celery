import os

BACKEND = os.getenv("BACKEND", "redis://127.0.0.1:6379/1")
BROKER = os.getenv("BROKER", "redis://127.0.0.1:6379/2")