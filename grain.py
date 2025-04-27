import asyncio
import logging
import time
from pathlib import Path
from typing import List

from playwright.async_api import async_playwright

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

    async def __login(self):
        page = await self.__context.new_page()
        await page.goto(Grain.BASE_URL + Grain.MEETINGS_ENDPOINT)
        # Wait for page load and possible redirects
        await page.wait_for_load_state("load", timeout=60000)  # 30 seconds timeout
        await asyncio.sleep(2)  # Additional time for any dynamic redirects

        # Check if we need to log in
        if "login" in page.url:
            self.__logger.debug("Login page detected. Waiting for manual login.")

            # Display helpful message
            self.__logger.debug("Please sign in manually to your Grain account.")
            self.__logger.debug("The script will wait for you to complete the login process.")

            try:
                # Wait for navigation after login
                await page.wait_for_url(f"**/{Grain.MEETINGS_ENDPOINT}", timeout=300000)  # 5 minutes timeout
                self.__logger.debug("Login successful!")
            except Exception as e:
                self.__logger.error(f"Login timeout or error: {str(e)}")
        else:
            self.__logger.debug("Already logged in.")

        await page.close()

    async def get_all_meetings(self) -> List[Meeting]:
        await self.__login()
        self.__logger.debug(f"Navigating to {Grain.MEETINGS_ENDPOINT}")

        page = await self.__context.new_page()
        await page.goto(Grain.BASE_URL + Grain.MEETINGS_ENDPOINT)

        self.__logger.debug("Extracting meetings data...")
        await page.wait_for_load_state("load")
        self.__logger.debug("Page reached network idle state")

        time.sleep(5)
        page_content = await page.content()

        return parse_meetings(page_content)

    async def download_meeting_transcript(self, save_path: str, meeting_id: str, transcription_type: str="vtt") -> None:
        await self.__download_file(
            download_url=Grain.BASE_URL + Grain.TRANSCRIPTIONS_ENDPOINT_TEMPLATE % (meeting_id, transcription_type),
            save_path=save_path
        )

    async def __download_file(self, download_url: str, save_path: str) -> None:
        await self.__login()
        self.__logger.debug(f"Downloading file {download_url}...")
        page = await self.__context.new_page()

        # Start waiting for the download
        async with page.expect_download() as download_info:
            try:
                # Navigate to the transcript URL to initiate download
                # This may throw an error with "net::ERR_ABORTED" which is expected when a download starts
                await page.goto(download_url)
            except Exception as nav_error:
                # Check if this is the expected "net::ERR_ABORTED" error
                if "net::ERR_ABORTED" in str(nav_error):
                    self.__logger.debug(
                        f"Navigation aborted as expected due to download starting")
                else:
                    # If it's a different error, re-raise it
                    raise nav_error

                    # Get the download object
        download = await download_info.value

        # Wait for the download process to complete and save the file
        await download.save_as(save_path)

        self.__logger.debug(f"Saved transcript to {save_path}")

    async def __aenter__(self):
        self.__playwright = await async_playwright().start()

        Path(self.__pw_cache_dir).mkdir(parents=True, exist_ok=True)
        self.__context = await self.__playwright.chromium.launch_persistent_context(
            user_data_dir=self.__pw_cache_dir,
            headless=False,  # Set to True for production use
            slow_mo=100,  # Slow down operations for better viewing (remove for production)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.__context:
            await self.__context.close()
            self.__context = None

        if self.__playwright:
            await self.__playwright.stop()
            self.__playwright = None