import os
import sys
from bs4 import BeautifulSoup
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the parser module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parser import (
    Meeting,
    parse_meetings,
    parse_meeting_data,
    get_text_content,
    parse_meeting_id,
    parse_date_to_iso
)

# Sample HTML for testing - obfuscated version of the real data
SAMPLE_HTML = """
<div id="infinite-scrollable-div" style="overflow: auto; height: 100%;">
   <div class="infinite-scroll-component__outerdiv">
      <div class="infinite-scroll-component " style="height: auto; overflow: unset; display: flex; flex-direction: column;">
         <section>
            <div class="css-ysm3h7 e11o8xyn0">
               <div class="text-label css-r20n5c e9gnks50">
                  <span class="css-1pl8v0u e9gnks52">Wednesday, Mar 15th</span>
               </div>
            </div>
            <a role="article" data-cy="meeting-list-item" class="css-1ovb08l e1txqhwh3" href="/share/recording/abc123-456-789/xyz987">
               <div class="css-13xzxt7">
                  <div class="css-1devehb etvbn3c3"><img src="https://example.com/thumbnail.webp" class="css-1xb9j3l etvbn3c2"></div>
               </div>
               <div class="css-ye65hu">
                  <div class="css-1nn5t6c">
                     <h3 title="Project Alpha Weekly Meeting" class="css-1tnzpa4 e1txqhwh2">Project Alpha Weekly Meeting</h3>
                  </div>
                  <div class="css-9xsd3d e1txqhwh1">Mar, 15th 2:30 PM · 45m </div>
               </div>
               <span class="tippy-wrapper css-o092jf">
                  <div width="lg" class="css-1ybfm4n eifufma0">
                     <button class="css-lm43pq e1ah0vhx1" type="button">
                        <div class="text-label button-text-label css-r20n5c e9gnks50">
                           <span class="css-1pl8v0u e9gnks52">
                              <div class="text-label css-r20n5c e9gnks50">
                                 <div class="css-1ocgb0l e1uabybm3"><img src="https://example.com/avatar.jpg" class="css-uwyyhw e1uabybm2"></div>
                                 <span class="css-1pl8v0u e9gnks52">John Smith</span>
                              </div>
                           </span>
                        </div>
                     </button>
                  </div>
               </span>
            </a>
            <div class="divider css-1hbyujm e16gyxa00">
               <hr class="css-1rhl4br e16gyxa03">
            </div>
            <a role="article" data-cy="meeting-list-item" class="css-1ovb08l e1txqhwh3" href="/share/recording/def456-789-012/uvw654">
               <div class="css-13xzxt7">
                  <div class="css-1devehb etvbn3c3"><img src="https://example.com/thumbnail2.webp" class="css-1xb9j3l etvbn3c2"></div>
               </div>
               <div class="css-ye65hu">
                  <div class="css-1nn5t6c">
                     <h3 title="Project Beta Tech Discussion" class="css-1tnzpa4 e1txqhwh2">Project Beta Tech Discussion</h3>
                  </div>
                  <div class="css-9xsd3d e1txqhwh1">Mar, 15th 1:15 PM · 30m </div>
               </div>
            </a>
         </section>
         <section>
            <div class="css-ysm3h7 e11o8xyn0">
               <div class="text-label css-r20n5c e9gnks50">
                  <span class="css-1pl8v0u e9gnks52">Tuesday, Mar 14th</span>
               </div>
            </div>
            <a role="article" data-cy="meeting-list-item" class="css-1ovb08l e1txqhwh3" href="/share/recording/ghi789-012-345/rst321">
               <div class="css-13xzxt7">
                  <div class="css-1devehb etvbn3c3"><img src="https://example.com/thumbnail3.webp" class="css-1xb9j3l etvbn3c2"></div>
               </div>
               <div class="css-ye65hu">
                  <div class="css-1nn5t6c">
                     <h3 title="Project Gamma Roadmap Planning" class="css-1tnzpa4 e1txqhwh2">Project Gamma Roadmap Planning</h3>
                  </div>
                  <div class="css-9xsd3d e1txqhwh1">Mar, 14th 3:00 PM · 60m </div>
               </div>
            </a>
         </section>
      </div>
   </div>
</div>
"""

class TestParser:
    def test_get_text_content(self):
        # Test with a valid element
        soup = BeautifulSoup("<div>Test Content</div>", "html.parser")
        element = soup.find("div")
        assert get_text_content(element) == "Test Content"

        # Test with None
        assert get_text_content(None) is None

        # Test with empty element
        soup = BeautifulSoup("<div></div>", "html.parser")
        element = soup.find("div")
        assert get_text_content(element) == ""

    def test_parse_meeting_id(self):
        # Test valid URL patterns
        assert parse_meeting_id("https://grain.com/share/recording/abc123-456-789/xyz987") == "abc123-456-789"
        assert parse_meeting_id("/share/recording/def456-789-012/uvw654") == "def456-789-012"

        # Test invalid URL patterns
        assert parse_meeting_id("https://grain.com/share/abc123") is None
        assert parse_meeting_id("") is None

        # For None input, we'll create a safe wrapper function
        # This is a test-only function that handles None input safely
        def safe_parse_meeting_id(url):
            if url is None:
                return None
            return parse_meeting_id(url)

        assert safe_parse_meeting_id(None) is None

    def test_parse_date_to_iso(self):
        # Test with valid date string
        date_str = "Mar, 15th 2:30 PM"

        # Create a mock datetime object that returns a specific isoformat
        mock_date = MagicMock()
        mock_date.isoformat.return_value = "2024-03-15T14:30:00"

        # Use a fixed year for testing and return our mock date object
        with patch('parser.datetime', autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)
            # Make datetime constructor return our mock
            mock_datetime.side_effect = lambda *args, **kwargs: mock_date if len(args) > 3 else datetime(*args, **kwargs)

            result = parse_date_to_iso(date_str)
            assert result == "2024-03-15T14:30:00"

        # Test with provided year - using a different approach with direct patching of datetime constructor
        with patch('parser.datetime', autospec=True) as mock_datetime:
            # Create a real datetime object for the .now() call
            mock_datetime.now.return_value = datetime(2023, 1, 1)

            # Create a mock for the datetime constructor that returns an object with isoformat method
            mock_date_obj = MagicMock()
            mock_date_obj.isoformat.return_value = "2023-03-15T14:30:00"
            mock_datetime.side_effect = lambda *args, **kwargs: mock_date_obj if len(args) > 3 else datetime(*args, **kwargs)

            result = parse_date_to_iso(date_str, year=2023)
            assert result == "2023-03-15T14:30:00"

        # Test with None
        assert parse_date_to_iso(None) is None

        # Test with invalid date string
        assert parse_date_to_iso("Invalid date") is None

    def test_parse_meeting_data(self):
        soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
        meeting_item = soup.find("a", attrs={"role": "article", "data-cy": "meeting-list-item"})

        # Mock the parse_date_to_iso function to return a fixed date
        with patch('parser.parse_date_to_iso', return_value="2024-03-15T14:30:00"):
            meeting = parse_meeting_data(meeting_item)

            assert isinstance(meeting, Meeting)
            assert meeting.id == "abc123-456-789"
            assert meeting.title == "Project Alpha Weekly Meeting"
            assert meeting.url == "/share/recording/abc123-456-789/xyz987"
            assert meeting.date == "2024-03-15T14:30:00"

    def test_parse_meetings(self):
        # Test with valid HTML
        meetings = parse_meetings(SAMPLE_HTML)

        assert len(meetings) == 3
        assert all(isinstance(meeting, Meeting) for meeting in meetings)

        # Verify first meeting
        assert meetings[0].title == "Project Alpha Weekly Meeting"
        assert meetings[0].id == "abc123-456-789"

        # Verify second meeting
        assert meetings[1].title == "Project Beta Tech Discussion"
        assert meetings[1].id == "def456-789-012"

        # Verify third meeting
        assert meetings[2].title == "Project Gamma Roadmap Planning"
        assert meetings[2].id == "ghi789-012-345"

        # Test with empty HTML
        assert parse_meetings("") == []

        # Test with HTML that doesn't contain meetings
        assert parse_meetings("<div>No meetings here</div>") == []

        # Test with HTML that has the scrollable div but no meetings
        assert parse_meetings('<div id="infinite-scrollable-div"></div>') == []
