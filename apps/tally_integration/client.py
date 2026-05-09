"""
Tally HTTP Client.

Provides a resilient interface for communicating with Tally's XML over HTTP API.
Includes retry logic, logging, and error handling.
"""

import time
import requests
import logging
from django.conf import settings

logger = logging.getLogger('apps.tally_integration')


class TallyClientError(Exception):
    """Base exception for Tally client errors."""
    pass


class TallyClient:
    """
    Client for interacting with Tally Prime/ERP 9 via XML-over-HTTP.
    """

    def __init__(self, url=None, timeout=None):
        self.url = str(url or getattr(settings, 'TALLY_URL', 'http://localhost:9000'))
        self.timeout = float(timeout or getattr(settings, 'TALLY_TIMEOUT', 15))
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/xml',
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def post_with_retry(self, xml_payload):
        """
        Sends a POST request to Tally with exponential backoff on failure.
        
        Args:
            xml_payload (str): The Tally-compliant XML string to send.
            
        Returns:
            str: The raw XML response content.
            
        Raises:
            TallyClientError: If all retries fail.
        """
        max_retries = int(getattr(settings, 'TALLY_RETRY_COUNT', 3))
        
        logger.debug(f"Tally Request XML:\n{xml_payload}")

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.url,
                    data=xml_payload,
                    timeout=self.timeout
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Capture and log response
                # Tally responses can sometimes be in UTF-16, 
                # we decode manually to be safe.
                content = response.content.decode(response.encoding or 'utf-8', errors='replace')
                logger.debug(f"Tally Response XML:\n{content}")
                
                return content

            except (requests.ConnectionError, requests.Timeout) as e:
                wait_time = 2 ** attempt
                logger.warning(
                    f"Tally connection failed (Attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {wait_time}s... Error: {str(e)}"
                )
                
                if attempt == max_retries - 1:
                    logger.error(f"Tally communication failed after {max_retries} attempts.")
                    raise TallyClientError(f"Connection to Tally at {self.url} failed: {str(e)}")
                
                time.sleep(wait_time)
                
            except requests.RequestException as e:
                logger.error(f"Unexpected Tally request error: {str(e)}")
                raise TallyClientError(f"Tally request failed: {str(e)}")

        return None
