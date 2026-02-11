import logging
import asyncio
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class PlaywrightConnector:
    """
    Unified Scraper using Playwright for dynamic interaction.
    Handles ADX, DFM, Wikipedia, and Official Sites.
    """
    def __init__(self):
        self.headless = True
        
    async def _get_page_content(self, url: str, wait_for: str = None) -> str:
        """Helper to navigate and extract HTML."""
        if not url: return ""
        
        content = ""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                # Use a realistic context to avoid bot detection
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                
                logger.info(f"Navigating to {url}...")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                if wait_for:
                    try:
                        await page.wait_for_selector(wait_for, timeout=15000)
                    except:
                        logger.warning(f"Selector {wait_for} not found, continuing with loaded content.")
                
                # Scroll to bottom to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2) # Grace period
                
                content = await page.content()
                await browser.close()
                
        except Exception as e:
            logger.error(f"Playwright Error: {e}")
            
        return content

    async def scrape_wiki_profile(self, url: str) -> Dict:
        """
        Scrapes Wikipedia for Company Profile, Sector, Established Date, Key People.
        """
        logger.info(f"Scraping Wiki: {url}")
        html = await self._get_page_content(url, wait_for="#mw-content-text")
        soup = BeautifulSoup(html, 'html.parser')
        
        profile = {
            "description": "",
            "sector": "",
            "est_date": "",
            "shareholders": [], # Or Key People
            "website": ""
        }
        
        # 1. Description: First 2 paragraphs
        paragraphs = soup.select("#mw-content-text > div.mw-parser-output > p")
        desc_text = []
        for p in paragraphs:
            if not p.get_text(strip=True): continue
            desc_text.append(p.get_text(strip=True))
            if len(desc_text) >= 2: break
        profile["description"] = "\n\n".join(desc_text)
        
        # 2. Infobox Parsing
        infobox = soup.select_one("table.infobox.vcard")
        if infobox:
            rows = infobox.find_all("tr")
            for row in rows:
                header = row.find("th")
                data = row.find("td")
                if header and data:
                    lbl = header.get_text(strip=True).lower()
                    val = data.get_text(strip=True)
                    
                    if "industry" in lbl or "sector" in lbl:
                        profile["sector"] = val
                    elif "founded" in lbl:
                        profile["est_date"] = val
                    elif "website" in lbl:
                        profile["website"] = data.get_text(strip=True)
                        
        return profile

    async def scrape_exchange_data(self, url: str, exchange: str) -> Dict:
        """
        Scrapes Financials from ADX/DFM pages.
        """
        logger.info(f"Scraping {exchange}: {url}")
        
        data = {
            "financials": {
                "current": {"period": f"TTM {datetime.now().year}", "rev": 0, "profit": 0, "price": 0, "trend": ""},
                "last_year": {"period": f"{datetime.now().year-1}", "rev": 0, "profit": 0},
                "last_quarter": {"period": "Q3", "rev": 0, "profit": 0, "rev_gro": "", "prof_gro": ""}
            },
            "risk": {},
            "sources": []
        }
        
        wait_selector = "table" # Generic
        if exchange == "ADX":
            wait_selector = ".adx-profile_details-listedHeader-left-details" 
            # ADX Specifics - Check the debug_adx_decoder if complex
            
        elif exchange == "DFM":
            wait_selector = ".financials-summary"
            
        html = await self._get_page_content(url, wait_for=wait_selector)
        soup = BeautifulSoup(html, 'html.parser')
        
        # --- Extraction Logic ---
        # NOTE: This parsing logic needs to be robust to specific site changes.
        # For now, implementing best-effort text extraction based on labels.
        
        # 1. Price (often near top)
        # Search for pattern "AED 12.34" or specific classes
        price_tag = soup.find(string=re.compile(r"AED\s*\d+\.\d+"))
        if price_tag:
            try:
                price_str = re.search(r"(\d+\.\d+)", price_tag).group(1)
                data["financials"]["current"]["price"] = float(price_str)
            except: pass
            
        # 2. Financial Tables
        tables = soup.find_all("table")
        for table in tables:
            # Simple heuristic: Look for Revenue/Profit keywords in table text
            txt = table.get_text().lower()
            if "revenue" in txt or "profit" in txt or "income" in txt:
                # Parse rows data
                pass 
        
        # 3. Document Links
        doc_links = self._extract_docs(soup, url)
        data["sources"] = doc_links
        
        return data

    def _extract_docs(self, soup, base_url) -> List[Dict]:
        """Finds PDF reports."""
        docs = []
        links = soup.find_all("a", href=True)
        for a in links:
            href = a['href']
            txt = a.get_text(strip=True).lower()
            if ".pdf" in href.lower() and ("report" in txt or "financial" in txt or "results" in txt):
                if not href.startswith("http"):
                    if href.startswith("/"):
                        parsed_uri = base_url.split("/")
                        root = f"{parsed_uri[0]}//{parsed_uri[2]}"
                        href = f"{root}{href}"
                    else:
                        continue 
                        
                docs.append({"title": txt.title() or "Financial Report", "url": href})
        return docs[:5] # Limit
