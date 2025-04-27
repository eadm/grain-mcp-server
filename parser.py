from dataclasses import dataclass
import re
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger("grain-mcp-server")

@dataclass
class Meeting:
    id: str
    title: str
    url: str
    date: Optional[str] # ISO format

def parse_meetings(html_content: str) -> List[Meeting]:
    """Extract meeting data from HTML content using BeautifulSoup.

    Args:
        html_content: HTML content of the page

    Returns:
        List of meeting dictionaries with title, date, id, and url
    """

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the div with id=infinite-scrollable-div
    scrollable_div = soup.find(id='infinite-scrollable-div')

    if not scrollable_div:
        return []

    # Try to find meeting items with specific attributes based on the HTML example
    meeting_items = scrollable_div.find_all('a', attrs={'role': 'article', 'data-cy': 'meeting-list-item'})

    logger.info(f"Found {len(meeting_items)} meeting items")

    # Extract data from each meeting item
    meetings = []
    for item in meeting_items:
        try:
            meetings.append(parse_meeting_data(item))
        except ValueError as e:
            logger.error(f"Error parsing meeting data: {e}")

    return meetings

def parse_meeting_data(item) -> Meeting:
    """Extract data from a meeting item."""
    # Based on the HTML example, look for specific classes first
    title_el = item.find('h3')
    meeting_title = get_text_content(title_el)
    if meeting_title is None:
        raise ValueError("No title found for meeting")

    # Get the URL from the link element
    meeting_url: Optional[str] = item.get('href')
    if meeting_url is None:
        raise ValueError("No URL found for meeting")

    meeting_id = parse_meeting_id(meeting_url)
    if meeting_id is None:
        raise ValueError("No ID found for meeting")

    # Look for year information in sibling elements
    year = None

    # Check previous sibling elements for year information
    sibling = item.find_previous_sibling(name='div')
    while sibling and not year:
        sibling_text = get_text_content(sibling)
        if sibling_text:
            year_match = re.search(r'\b(20\d{2})\b', sibling_text)
            if year_match:
                year = int(year_match.group(1))
                logger.info(f"Found year {year} in sibling element")
                break
        sibling = sibling.find_previous_sibling(name='div')

    meeting_date = parse_date_to_iso(
        date_str=get_text_content(title_el.parent.find_next_sibling()),
        year=year
    )

    return Meeting(
        id=meeting_id,
        title=meeting_title,
        date=meeting_date,
        url=meeting_url
    )

def get_text_content(element) -> Optional[str]:
    """Extract text content from a BeautifulSoup element."""
    if element is None:
        return None
    return element.get_text(strip=True)

def parse_meeting_id(url: str) -> Optional[str]:
    """Extract meeting ID from URL."""

    # Extract meeting ID from URL pattern: https://grain.com/share/recording/{meeting_id}/...
    recording_pattern = r'recordings?/([^/]+)'
    match = re.search(recording_pattern, url)

    if match and match.group(1):
        return match.group(1)
    else:
        return None

def parse_date_to_iso(date_str: Optional[str], year: Optional[int] = None) -> Optional[str]:
    """Convert various date formats to ISO format.

    Handles formats like:
    - "Apr, 23rd 3:03 PM"

    Args:
        date_str (str): The date string to convert
        year (int, optional): The year to use when parsing dates that don't include a year.
                             If not provided, the current year will be used.

    Returns:
        str: Date in ISO format, or original string if parsing fails
    """
    if not date_str:
        return None

    try:
        # Clean up the date string
        clean_date_str = date_str.strip()

        # Handle format like "Apr, 23rd 3:03 PM \u00b7 1h 37m"
        grain_date_pattern = (
            r'([A-Za-z]+),\s+(\d+)(?:st|nd|rd|th)?\s+(\d+):(\d+)\s+(AM|PM)'
        )
        grain_date_match = re.match(grain_date_pattern, clean_date_str, re.IGNORECASE)
        if grain_date_match:
            month_str = grain_date_match.group(1)
            day = int(grain_date_match.group(2))
            hours = int(grain_date_match.group(3))
            minutes = int(grain_date_match.group(4))
            ampm = grain_date_match.group(5).upper()

            # Convert month name to month number (1-12)
            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }

            month_key = month_str.lower()[:3]
            month = months.get(month_key, 1)  # Default to January if not found

            # Adjust hours for PM
            if ampm == 'PM' and hours < 12:
                hours += 12
            if ampm == 'AM' and hours == 12:
                hours = 0

            # Use the provided year if available, otherwise use current year
            use_year = year if year is not None else datetime.now().year
            date_obj = datetime(use_year, month, day, hours, minutes, 0)

            return date_obj.isoformat()

    except Exception as e:
        logger.error(f"Error parsing date: {str(e)}")
        return None

    return None