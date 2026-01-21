#!/usr/bin/env python3
"""UAE Corporate Intelligence Hub Entry Point"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligence_hub.ui.gradio_app import demo
from intelligence_hub.config.settings import config
from intelligence_hub.utils.helpers import setup_logging

logger = setup_logging()

def main():
    """Main entry point"""
    try:
        config.validate()
        logger.info("Starting UAE Corporate Intelligence Hub...")

        demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

