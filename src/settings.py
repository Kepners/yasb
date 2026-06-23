import os
import sys

# Application Settings
APP_NAME = "LayoutForge"
APP_NAME_FULL = "LayoutForge Status Bar"
APP_BAR_TITLE = "LFStatusBar"
APP_ID = "LF.StatusBar"
SCRIPT_PATH = (
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
)
GITHUB_URL = "https://github.com/Kepners/yasb"
GITHUB_THEME_URL = "https://github.com/amnweb/yasb-themes"
BUILD_VERSION = "1.8.7"
CLI_VERSION = "1.1.5"
RELEASE_CHANNEL = "stable"
# Development Settings
DEBUG = False
# Configuration Settings
DEFAULT_CONFIG_DIRECTORY = os.getenv("YASB_CONFIG_HOME", os.getenv("LFBAR_CONFIG_HOME", ".config\\yasb"))
DEFAULT_STYLES_FILENAME = "styles.css"
DEFAULT_CONFIG_FILENAME = "config.yaml"
DEFAULT_LOG_FILENAME = "lfstatusbar.log"
