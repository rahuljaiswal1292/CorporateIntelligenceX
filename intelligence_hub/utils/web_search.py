import logging
import time
import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class WebSearch:
    """
    Utility for Web Search.
    Uses 'curl_cffi' to scrape html.duckduckgo.com directly, avoiding library issues.
    """
    
    @staticmethod
    def search(query: str, max_results: int = 5) -> List[Dict]:
        """
        Searches DDG HTML version.
        """
        logger.info(f"Searching DDG (HTML) for: '{query}'")
        results = []
        
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://html.duckduckgo.com/"
        }
        
        try:
            # Impersonate generic boolean to avoid heavy fingerprinting
            response = requests.post(url, data=data, headers=headers, impersonate="chrome110", timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Parse Results
                # Structure: div.result -> a.result__a (title/link) / a.result__snippet (body)
                items = soup.select(".result")
                
                for item in items[:max_results]:
                    try:
                        a_tag = item.select_one("a.result__a")
                        if not a_tag: continue
                        
                        raw_href = a_tag.get("href", "")
                        title = a_tag.get_text(strip=True)
                        
                        # Snippet
                        snippet_tag = item.select_one(".result__snippet")
                        body = snippet_tag.get_text(strip=True) if snippet_tag else ""
                        
                        # Defuse DDG Redirect if present (/l/?uddg=...)
                        href = raw_href
                        if "/l/?uddg=" in raw_href:
                            try:
                                parsed = urllib.parse.urlparse(raw_href)
                                qs = urllib.parse.parse_qs(parsed.query)
                                if "uddg" in qs:
                                    href = qs["uddg"][0]
                            except:
                                pass
                                
                        results.append({"title": title, "href": href, "body": body})
                        logger.info(f"Found: {title} -> {href}")
                        
                    except Exception as parse_err:
                        logger.warning(f"Error parsing result item: {parse_err}")

            else:
                logger.error(f"DDG HTTP Error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"DDG Search failed for '{query}': {e}")
            
        return results

    @staticmethod
    def find_company_links(company_name: str) -> Dict[str, str]:
        """
        Smart search to find specific profile links using targeted queries.
        Returns: {exchange_url, wiki_url, official_url, ticker_hint}
        """
        links = {
            "exchange_url": None,
            "wiki_url": None,
            "official_url": None,
            "ticker_hint": None,
            "exchange_name": None
        }
        
        # 1. Targeted Search for Exchange (ADX)
        q_adx = f"{company_name} ADX"
        adx_results = WebSearch.search(q_adx, max_results=8)
        
        for r in adx_results:
            url = r.get("href", "").lower()
            if "adx.ae" in url:
                links["exchange_url"] = r["href"]
                links["exchange_name"] = "ADX"
                if "symbols=" in url:
                    try:
                         # Extract Ticker from URL (e.g. symbols=ADNOCGAS)
                         links["ticker_hint"] = url.split("symbols=")[1].split("&")[0].upper()
                    except: pass
                break
        
        # 2. Targeted Search for Exchange (DFM) - If ADX not found
        if not links["exchange_url"]:
             q_dfm = f"{company_name} DFM"
             dfm_results = WebSearch.search(q_dfm, max_results=8)
             for r in dfm_results:
                 url = r.get("href", "").lower()
                 if "dfm.ae" in url:
                     links["exchange_url"] = r["href"]
                     links["exchange_name"] = "DFM"
                     if "/company/" in url:
                         try:
                             parts = url.split("/company/")
                             if len(parts) > 1:
                                 links["ticker_hint"] = parts[1].split("/")[0].upper()
                         except: pass
                     break

        # 3. Targeted Search for Wikipedia
        if not links["wiki_url"]:
            q_wiki = f"{company_name} Wikipedia"
            wiki_results = WebSearch.search(q_wiki, max_results=3)
            for r in wiki_results:
                url = r.get("href", "").lower()
                if "wikipedia.org" in url and "en.wikipedia" in url:
                     links["wiki_url"] = r["href"]
                     break

        # 4. Targeted Search for Official / IR
        if not links["official_url"]:
            q_official = f"{company_name} investor relations official site"
            off_results = WebSearch.search(q_official, max_results=5)
            
            aggregators = ["bloomberg", "reuters", "yahoo", "finance", "wikipedia", "adx", "dfm", "zawya", "mubasher", "tradingview", "linkedin", "facebook", "youtube"]
            
            for r in off_results:
                 url = r.get("href", "").lower()
                 if not any(agg in url for agg in aggregators):
                     links["official_url"] = r["href"]
                     break
                     
        return links
