import logging
from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
from intelligence_hub.utils.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class WikiScraper:
    """
    Scraper for Wikipedia.
    Fetches Company Profile, History, and Subs.
    """

    def __init__(self, connector: WebScraperConnector):
        self.connector = connector
        self.base_url = "https://en.wikipedia.org/wiki"

    def scrape_profile(self, company_name: str) -> dict:
        """
        Scrapes Wikipedia for Company Profile.
        Tries multiple URL variations.
        """
        # Clean name
        clean_name = company_name.replace("PJSC", "").replace("LLC", "").strip()
        variations = [
            clean_name.replace(" ", "_"),
            clean_name.replace(" ", "_") + "_(company)",
            clean_name.replace(" ", "_")
            + "_(insurance)",  # Specific for Sukoon/Insurance cases
        ]

        html = None
        used_url = None

        for variant in variations:
            url = f"{self.base_url}/{variant}"
            logger.info(f"Wiki: Scraping {url}...")
            html = self.connector.scrape(url)
            if (
                html
                and "Wikipedia does not have an article with this exact name"
                not in html
            ):
                used_url = url
                break

        if (
            not html
            or "Wikipedia does not have an article with this exact name" in html
        ):
            logger.warning(f"Wiki: No article found for {company_name}")
            return {}

        # Use clean name as the identifier for saving
        file_id = clean_name.replace(" ", "_")
        StorageManager.save_raw(html, "wiki", file_id)

        data = {
            "source": "Wikipedia",
            "url": used_url,
            "raw_html_snippet": html[:10000],
        }

        StorageManager.save_structured(data, "wiki", file_id)
        return data
