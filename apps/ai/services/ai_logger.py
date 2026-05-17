import logging
import os

ai_logger = logging.getLogger('apps.ai.providers')

if not ai_logger.handlers:
    log_path = r'C:\Users\Ankit\OneDrive\Desktop\Major Project\logs\ai_debug.log'
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - AI Router: %(message)s')
    handler.setFormatter(formatter)
    ai_logger.addHandler(handler)
    ai_logger.setLevel(logging.DEBUG)
