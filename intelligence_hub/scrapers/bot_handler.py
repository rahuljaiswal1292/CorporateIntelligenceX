"""
Bot Detection Handler for ADX/DFM Scrapers

Handles:
- Bot detection and challenges
- Rate limiting with exponential backoff
- Human-like delays
- Session rotation
"""

import asyncio
import random
import logging
from typing import Optional
from playwright.async_api import Page, Browser

logger = logging.getLogger(__name__)


class BotHandler:
    """
    Handles bot detection, rate limiting, and human-like behavior.
    """
    
    # Bot detection indicators
    BOT_INDICATORS = [
        'captcha',
        'robot',
        'automated',
        'unusual traffic',
        'verify you are human',
        'cloudflare',
        'access denied',
        'too many requests',
        'rate limit',
        'blocked',
        'suspicious activity'
    ]
    
    def __init__(self):
        self.rate_limit_count = 0
        self.bot_detected_count = 0
    
    async def add_human_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """
        Add random delay to mimic human behavior.
        
        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
    
    async def add_reading_delay(self, content_length: int = 1000):
        """
        Add delay proportional to content length (simulating reading time).
        
        Args:
            content_length: Length of content in characters
        """
        # Assume 200 words per minute reading speed
        # Average 5 characters per word
        words = content_length / 5
        reading_time = (words / 200) * 60  # seconds
        
        # Add some randomness (50-150% of calculated time)
        actual_delay = reading_time * random.uniform(0.5, 1.5)
        
        # Cap at reasonable maximum (30 seconds)
        actual_delay = min(actual_delay, 30)
        
        # Minimum 1 second
        actual_delay = max(actual_delay, 1)
        
        logger.debug(f"Adding reading delay: {actual_delay:.1f}s")
        await asyncio.sleep(actual_delay)
    
    async def detect_bot_challenge(self, page: Page) -> bool:
        """
        Detect if page shows bot detection challenge.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if bot challenge detected
        """
        try:
            content = await page.content()
            content_lower = content.lower()
            
            # Check for bot detection indicators
            for indicator in self.BOT_INDICATORS:
                if indicator in content_lower:
                    logger.warning(f"⚠ Bot detection indicator found: '{indicator}'")
                    self.bot_detected_count += 1
                    return True
            
            # Check for CAPTCHA elements
            captcha_selectors = [
                'iframe[src*="captcha"]',
                'iframe[src*="recaptcha"]',
                '[class*="captcha"]',
                '[id*="captcha"]'
            ]
            
            for selector in captcha_selectors:
                if await page.locator(selector).count() > 0:
                    logger.warning(f"⚠ CAPTCHA element detected: {selector}")
                    self.bot_detected_count += 1
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting bot challenge: {e}")
            return False
    
    async def handle_rate_limit(self, retry_count: int = 0):
        """
        Handle rate limiting with exponential backoff.
        
        Args:
            retry_count: Current retry attempt number
        """
        self.rate_limit_count += 1
        
        # Exponential backoff: 5s, 10s, 20s, 40s, capped at 60s
        base_delay = 5
        max_delay = 60
        
        delay = min(base_delay * (2 ** retry_count), max_delay)
        
        # Add some randomness (±20%)
        delay = delay * random.uniform(0.8, 1.2)
        
        logger.warning(f"⏳ Rate limit detected, waiting {delay:.1f}s (attempt {retry_count + 1})")
        await asyncio.sleep(delay)
    
    async def handle_bot_detection(self, page: Page, severity: str = 'medium'):
        """
        Handle bot detection with appropriate response.
        
        Args:
            page: Playwright page object
            severity: 'low', 'medium', or 'high'
        """
        if severity == 'low':
            # Short pause
            delay = random.uniform(5, 10)
            logger.info(f"Low severity bot detection, pausing {delay:.1f}s")
            await asyncio.sleep(delay)
            
        elif severity == 'medium':
            # Medium pause + page reload
            delay = random.uniform(15, 30)
            logger.warning(f"Medium severity bot detection, pausing {delay:.1f}s and reloading")
            await asyncio.sleep(delay)
            try:
                await page.reload(wait_until='networkidle', timeout=30000)
            except:
                pass
            
        elif severity == 'high':
            # Long pause + potential manual intervention needed
            delay = random.uniform(60, 120)
            logger.error(f"⛔ High severity bot detection! Pausing {delay:.1f}s")
            logger.error("Manual intervention may be required")
            await asyncio.sleep(delay)
    
    async def scroll_like_human(self, page: Page):
        """
        Scroll page in a human-like manner.
        
        Args:
            page: Playwright page object
        """
        try:
            # Get page height
            page_height = await page.evaluate('document.body.scrollHeight')
            
            # Scroll in chunks
            current_position = 0
            chunk_size = random.randint(300, 600)
            
            while current_position < page_height:
                # Scroll down
                current_position += chunk_size
                await page.evaluate(f'window.scrollTo(0, {current_position})')
                
                # Random pause (simulating reading)
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # Sometimes scroll back up a bit (human behavior)
                if random.random() < 0.2:
                    back_scroll = random.randint(50, 150)
                    current_position -= back_scroll
                    await page.evaluate(f'window.scrollTo(0, {current_position})')
                    await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Scroll back to top
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            logger.debug(f"Human scroll failed: {e}")
    
    async def move_mouse_randomly(self, page: Page):
        """
        Move mouse in random pattern (helps avoid detection).
        
        Args:
            page: Playwright page object
        """
        try:
            # Get viewport size
            viewport = page.viewport_size
            if not viewport:
                return
            
            # Move to random positions
            for _ in range(random.randint(2, 5)):
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
        except Exception as e:
            logger.debug(f"Mouse movement failed: {e}")
    
    async def rotate_session(self, browser: Browser, context):
        """
        Rotate browser session (close and create new context).
        
        Args:
            browser: Playwright browser object
            context: Current browser context
            
        Returns:
            New browser context
        """
        try:
            logger.info("Rotating browser session...")
            
            # Close old context
            await context.close()
            
            # Create new context with fresh session
            new_context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent=self._get_random_user_agent()
            )
            
            logger.info("Session rotated successfully")
            return new_context
            
        except Exception as e:
            logger.error(f"Session rotation failed: {e}")
            return context
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent string."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        return random.choice(user_agents)
    
    def get_stats(self) -> dict:
        """Get bot handling statistics."""
        return {
            'rate_limit_count': self.rate_limit_count,
            'bot_detected_count': self.bot_detected_count
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.rate_limit_count = 0
        self.bot_detected_count = 0
