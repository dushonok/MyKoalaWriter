import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

from secret_env import (
    APP_TITLE_SUFFIX,
)


# App settings
APP_NAME = "MyKoalaWriter" + APP_TITLE_SUFFIX
APP_DESCR = f"{APP_NAME}: Generate WordPress posts from Notion URLs using AI"
APP_VERSION = "v3.1.0"
APP_WINDOW_SIZE = "900x600"

# Feature flags
ENABLE_ADD_WP_IMGS_BUTTON = True
