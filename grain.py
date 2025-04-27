import logging
import time
from pathlib import Path
from typing import List

from playwright.sync_api import sync_playwright

from parser import Meeting, parse_meetings


class Grain:
    BASE_URL = "https://grain.com/"
    MEETINGS_ENDPOINT = "app/meetings/all"
    TRANSCRIPTIONS_ENDPOINT_TEMPLATE = "_/cc/recording/%s/transcript.%s"

    def __init__(self, pw_cache_dir: str):
        self.__pw_cache_dir = pw_cache_dir
        self.__context = None
        self.__playwright = None
        self.__logger = logging.getLogger("grain-mcp-server")

    def __login(self):
        page = self.__context.new_page()
        page.goto(Grain.BASE_URL + Grain.MEETINGS_ENDPOINT)
        # Wait for page load and possible redirects
        page.wait_for_load_state("load", timeout=60000)  # 30 seconds timeout
        time.sleep(2)  # Additional time for any dynamic redirects

        # Check if we need to log in
        if "login" in page.url:
            self.__logger.debug("Login page detected. Waiting for manual login.")

            # Display helpful message
            self.__logger.debug("Please sign in manually to your Grain account.")
            self.__logger.debug("The script will wait for you to complete the login process.")

            try:
                # Wait for navigation after login
                page.wait_for_url(f"**/{Grain.MEETINGS_ENDPOINT}", timeout=300000)  # 5 minutes timeout
                self.__logger.debug("Login successful!")
            except Exception as e:
                self.__logger.error(f"Login timeout or error: {str(e)}")
        else:
            self.__logger.debug("Already logged in.")

        page.close()

    def get_all_meetings(self) -> List[Meeting]:
        self.__login()
        self.__logger.debug(f"Navigating to {Grain.MEETINGS_ENDPOINT}")

        page = self.__context.new_page()
        page.goto(Grain.BASE_URL + Grain.MEETINGS_ENDPOINT)

        self.__logger.debug("Extracting meetings data...")
        page.wait_for_load_state("load")
        self.__logger.debug("Page reached network idle state")

        time.sleep(5)

        return parse_meetings(page.content())

    def download_transcript(self, save_path: str, meeting_id: str, transcription_type: str="vtt") -> None:
        self.__download_file(
            download_url=Grain.BASE_URL + Grain.TRANSCRIPTIONS_ENDPOINT_TEMPLATE % (meeting_id, transcription_type),
            save_path=save_path
        )

    def __download_file(self, download_url: str, save_path: str) -> None:
        self.__login()
        self.__logger.debug(f"Downloading file {download_url}...")
        page = self.__context.new_page()

        # Start waiting for the download
        with page.expect_download() as download_info:
            try:
                # Navigate to the transcript URL to initiate download
                # This may throw an error with "net::ERR_ABORTED" which is expected when a download starts
                page.goto(download_url)
            except Exception as nav_error:
                # Check if this is the expected "net::ERR_ABORTED" error
                if "net::ERR_ABORTED" in str(nav_error):
                    self.__logger.debug(
                        f"Navigation aborted as expected due to download starting")
                else:
                    # If it's a different error, re-raise it
                    raise nav_error

                    # Get the download object
        download = download_info.value

        # Wait for the download process to complete and save the file
        download.save_as(save_path)

        self.__logger.debug(f"Saved transcript to {save_path}")

    def __enter__(self):
        self.__playwright = sync_playwright().start()

        Path(self.__pw_cache_dir).mkdir(parents=True, exist_ok=True)
        self.__context = self.__playwright.chromium.launch_persistent_context(
            user_data_dir=self.__pw_cache_dir,
            headless=False,  # Set to True for production use
            slow_mo=100,  # Slow down operations for better viewing (remove for production)
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__context:
            self.__context.close()
            self.__context = None

        if self.__playwright:
            self.__playwright.stop()
            self.__playwright = None