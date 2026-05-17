import logging
import os
import tempfile

ai_logger = logging.getLogger('apps.ai.providers')

if not ai_logger.handlers:
    # 1. Dynamically resolve the absolute project root directory
    # apps/ai/services/ai_logger.py -> apps/ai/services -> apps/ai -> apps -> project_root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    logs_dir = os.path.join(base_dir, 'logs')
    
    log_path = os.path.join(logs_dir, 'ai_debug.log')
    
    # 2. Production fallback handling
    # If base logs directory is not writable, fall back to the system temp directory (highly useful on read-only container deploys like Render)
    try:
        os.makedirs(logs_dir, exist_ok=True)
        # Test write permission
        test_file = os.path.join(logs_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception:
        logs_dir = tempfile.gettempdir()
        log_path = os.path.join(logs_dir, 'ai_debug.log')

    # Double check that the directory exists before making log file
    dir_name = os.path.dirname(log_path)
    if dir_name:
        try:
            os.makedirs(dir_name, exist_ok=True)
        except Exception:
            pass

    try:
        handler = logging.FileHandler(log_path, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - AI Router: %(message)s')
        handler.setFormatter(formatter)
        ai_logger.addHandler(handler)
        ai_logger.setLevel(logging.DEBUG)
    except Exception as e:
        # Graceful fallback to console output if both logs directory and temp files are not writable
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - AI Router: (Fallback Console) %(message)s')
        handler.setFormatter(formatter)
        ai_logger.addHandler(handler)
        ai_logger.setLevel(logging.DEBUG)
        ai_logger.warning(f"Could not create FileHandler at {log_path} due to error: {e}. Stream fallback initialized.")
