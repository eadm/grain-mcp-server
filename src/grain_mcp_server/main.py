import argparse
import logging
import os
import typing
from dataclasses import asdict

from fastmcp import FastMCP

from grain_mcp_server.grain import Grain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("grain-mcp-server")

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")

mcp = FastMCP("Grain")

@mcp.tool()
async def get_all_meetings() -> typing.List[typing.Dict[str, typing.Any]]:
    """Retrieve all meeting from Grain.

    Fetches a list of all meetings stored in the Grain system, including their
    details and metadata.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing meeting information.
            Each dictionary represents a meeting with its properties.
    """

    try:
        async with Grain(os.getenv("USER_DATA_DIR", USER_DATA_DIR)) as grain:
            # Get all meetings
            return [asdict(meeting) for meeting in await grain.get_all_meetings()]
    except Exception as e:
        logger.exception(f"Error running scraper: {str(e)}")
    return []

@mcp.tool()
async def download_meeting_transcript(
    absolute_save_path: str,
    meeting_id: str,
    transcription_type: typing.Literal["vtt", "srt"]
) -> bool:
    """Download a meeting transcript from Grain.

    Downloads the transcript for a specific meeting in either VTT or SRT format
    and saves it to the specified location.

    Args:
        absolute_save_path (str): The file path where the transcript will be saved
        meeting_id (str): The unique identifier of the meeting
        transcription_type (Literal["vtt", "srt"]): The format of the transcript file (VTT or SRT)

    Returns:
        bool: True if the download was successful, False otherwise
    """

    try:
        async with Grain(os.getenv("USER_DATA_DIR", USER_DATA_DIR)) as grain:
            # Download transcript
            await grain.download_meeting_transcript(
                save_path=absolute_save_path,
                meeting_id=meeting_id,
                transcription_type=transcription_type
            )

            return True
    except Exception as e:
        logger.exception(f"Error running scraper: {str(e)}")
    return False

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
        logger.addHandler(logging.FileHandler("../../grain-mcp-server.log"))
        logger.addHandler(logging.StreamHandler())
        logger.debug("Debug mode enabled")
    #
    # Use custom user data directory if provided
    global USER_DATA_DIR
    USER_DATA_DIR = args.user_data_dir if args.user_data_dir else USER_DATA_DIR

    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()