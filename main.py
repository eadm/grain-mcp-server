import argparse
import logging
import os
from pathlib import Path

from grain import Grain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grain-mcp-server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("grain-mcp-server")

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Grain meetings scraper")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with screenshots and detailed logging")
    parser.add_argument("--user-data-dir", type=str, help="Custom directory for user data")
    return parser.parse_args()

def main() -> None:
    """Main function to scrape Grain meetings.

    Command-line arguments:
        --debug: Enable debug mode with screenshots and detailed logging
        --user-data-dir: Custom directory for user data

    Examples:
        # Run with default settings
        python main.py

        # Run with debug mode enabled
        python main.py --debug

        # Run with custom user data directory
        python main.py --user-data-dir=/path/to/custom/user_data

        # Run with both debug mode and custom user data directory
        python main.py --debug --user-data-dir=/path/to/custom/user_data
    """
    args = parse_args()

    # Configure logging level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    # Use custom user data directory if provided
    user_data_dir = args.user_data_dir if args.user_data_dir else USER_DATA_DIR

    logger.debug(f"Using user data directory: {user_data_dir}")

    # Ensure the user data directory exists
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    logger.debug("Starting Grain meetings scraper")

    try:
        with Grain(user_data_dir) as grain:
            # Get all meetings
            meetings = grain.get_all_meetings()
            logger.debug(f"Found {len(meetings)} meetings")

            grain.download_transcript(
                save_path=os.path.join(BASE_DIR, "transcript.vtt"),
                meeting_id=meetings[0].id,
                transcription_type="vtt"
            )

    except Exception as e:
        logger.exception(f"Error running scraper: {str(e)}")

if __name__ == "__main__":
    main() 
