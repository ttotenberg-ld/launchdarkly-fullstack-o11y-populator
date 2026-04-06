B"""
Traffic Generator - Generates realistic browser-based traffic for LaunchDarkly observability demo.
Uses Playwright for headless browser automation to generate real frontend sessions.

Sessions are designed to be ~60 seconds long with human-like behavior:
- Hesitating before actions
- Typing slowly with occasional typos and corrections
- Clicking around and exploring pages
- Ensuring all backend endpoints are hit during each session
"""

import os
import sys
import random
import asyncio
import uuid
import json
import gzip
import string
from datetime import datetime
from typing import Dict, Any, Optional, List

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Add backend directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from shared.users import USER_PERSONAS, get_random_user

# Configuration
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
SESSIONS_PER_MINUTE = int(os.getenv('SESSIONS_PER_MINUTE', '2'))  # Fewer sessions since they're longer
MAX_CONCURRENT_BROWSERS = int(os.getenv('MAX_CONCURRENT_BROWSERS', '3'))
TARGET_SESSION_DURATION = int(os.getenv('TARGET_SESSION_DURATION', '60'))  # seconds
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '90'))  # hard cap per session

# Log file that records every user key that should have both a session
# and flag evaluations.  Check this file to verify overlap in the LD dashboard.
SESSION_LOG_FILE = os.getenv('SESSION_LOG_FILE', '/app/logs/session_keys.log')
EVENT_LOG_FILE = os.getenv('EVENT_LOG_FILE', '/app/logs/ld_events.log')

# Sample search queries with intentional typos for realistic typing
SEARCH_QUERIES = [
    ('feature flags', ['featuer flags', 'featur flags', 'feature falgs']),
    ('rollout', ['rolout', 'rollotu', 'roolout']),
    ('testing', ['testnig', 'testign', 'tesitng']),
    ('targeting', ['targteing', 'targetign', 'targetting']),
    ('sdk', ['skd', 'sdd', 'sdk']),
    ('experiment', ['experiemnt', 'expirement', 'experimetn']),
    ('deployment', ['deploymnet', 'deplyoment', 'deployemnt']),
    ('configuration', ['configuraiton', 'configration', 'configuraton']),
]


# Flag keys the feedback widget can target
FEEDBACK_FLAG_KEYS = [
    'releaseNewUI',
    'showNewHero',
    'showNewFeatures',
    'migrate-warehouse-api',
]

# Feedback text pools — sentiment is weighted by whether errors occurred
FEEDBACK_POSITIVE = [
    "Everything is running smoothly, really impressed with the speed!",
    "Love the new UI, it feels very intuitive and fast.",
    "Products loaded instantly, great improvement over last week.",
    "The checkout flow was seamless, no issues at all.",
    "Searching for products is super fast now, nice work!",
    "Page loads are noticeably faster, the new version is solid.",
    "Clean layout, easy to navigate. Keep it up!",
    "No complaints — everything just works.",
    "Really happy with the new features, makes my workflow easier.",
    "The site feels snappy and responsive, great experience overall.",
    "This update is a huge improvement, well done!",
    "Feature flags seem to be working perfectly on my end.",
    "Smooth browsing experience today, nothing broken.",
    "The product pages look great and load quickly.",
    "Best experience I've had on this site in a while.",
]

FEEDBACK_NEUTRAL = [
    "It's okay, nothing special. Works as expected.",
    "Some pages load a bit slow but nothing terrible.",
    "The layout is fine, could use some polish though.",
    "Didn't notice much difference from before.",
    "Average experience, gets the job done.",
    "A few minor hiccups but overall functional.",
    "The new features are alright, still getting used to them.",
    "Not bad, not great. Just okay.",
    "Some things improved, others feel the same.",
    "Works fine for what I need, no strong opinions.",
]

FEEDBACK_NEGATIVE = [
    "Getting constant errors when trying to view products. Very frustrating.",
    "The site keeps timing out, I can't complete my checkout!",
    "Something is broken — I keep seeing 500 errors on every page.",
    "Product pages fail to load half the time, this is unusable.",
    "Checkout failed with a server error. Lost my entire cart.",
    "The new version is extremely unreliable, please fix this.",
    "Pages are crashing left and right, worst experience ever.",
    "I keep getting gateway timeout errors, can't browse anything.",
    "Seriously broken — error after error. Rolling back would be better.",
    "The warehouse API errors are killing my experience. Nothing works.",
    "Can't even add items to cart without hitting an error.",
    "Every other page load fails. This is not production-ready.",
    "Rate limit errors everywhere, the site is barely functional.",
    "Authentication keeps failing randomly, very unreliable.",
    "I've encountered more errors today than in the past month combined.",
]

# Realistic support chat questions for the AI chatbot
CHAT_QUESTIONS = [
    "What's your return policy?",
    "How long does shipping usually take?",
    "Can I cancel my order?",
    "Do you ship internationally?",
    "What payment methods do you accept?",
    "How do I track my order?",
    "Is this item in stock?",
    "Can I change my shipping address after placing an order?",
    "Do you offer any discounts for bulk purchases?",
    "How do I reset my password?",
    "What's the difference between the free and premium plans?",
    "I'm having trouble checking out, can you help?",
    "Are there any current promotions or sales?",
    "How do I contact customer support by phone?",
    "Can I get a refund if I'm not satisfied?",
]


class HumanTypist:
    """Simulates human-like typing behavior with mistakes and corrections."""
    
    @staticmethod
    async def type_like_human(page: Page, selector: str, text: str, 
                              make_typos: bool = True, wpm: int = 40):
        """Type text with human-like delays, occasional typos, and corrections."""
        element = page.locator(selector)
        if await element.count() == 0:
            return False
        
        await element.click()
        await asyncio.sleep(random.uniform(0.2, 0.5))  # Pause after clicking
        
        # Calculate base delay between keystrokes (average typing speed)
        base_delay = 60 / (wpm * 5)  # 5 chars per word average
        
        chars_typed = []
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Occasionally make a typo (10% chance per character)
            if make_typos and random.random() < 0.10 and char.isalpha():
                # Type wrong character
                wrong_char = random.choice(string.ascii_lowercase)
                await element.press(wrong_char)
                chars_typed.append(wrong_char)
                await asyncio.sleep(random.uniform(base_delay * 0.5, base_delay * 1.5))
                
                # Pause to "notice" the mistake
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # Backspace to fix it
                await element.press('Backspace')
                chars_typed.pop()
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Type the correct character
            await element.press(char)
            chars_typed.append(char)
            
            # Variable delay between keystrokes
            delay = random.uniform(base_delay * 0.5, base_delay * 2.0)
            
            # Longer pauses at spaces and punctuation
            if char in ' .,!?':
                delay *= random.uniform(1.5, 3.0)
            
            await asyncio.sleep(delay)
            i += 1
        
        return True
    
    @staticmethod
    async def hesitate(min_sec: float = 0.5, max_sec: float = 2.0):
        """Simulate human hesitation/thinking."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    async def read_page(min_sec: float = 2.0, max_sec: float = 5.0):
        """Simulate time spent reading/looking at a page."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    async def quick_glance(min_sec: float = 0.5, max_sec: float = 1.5):
        """Quick look at something before acting."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))


class HumanClicker:
    """Simulates human-like clicking and navigation behavior."""
    
    @staticmethod
    async def click_with_hesitation(page: Page, selector: str, 
                                     hesitate_before: bool = True,
                                     hesitate_after: bool = False):
        """Click an element with optional hesitation before/after."""
        element = page.locator(selector)
        if await element.count() == 0:
            return False
        
        if hesitate_before:
            await HumanTypist.hesitate(0.3, 1.0)
        
        await element.click()
        
        if hesitate_after:
            await HumanTypist.hesitate(0.2, 0.5)
        
        return True
    
    @staticmethod
    async def scroll_randomly(page: Page, times: int = None):
        """Scroll the page randomly like a human browsing."""
        if times is None:
            times = random.randint(1, 3)
        
        for _ in range(times):
            # Random scroll direction and amount
            scroll_y = random.randint(100, 400) * random.choice([1, -1, 1, 1])  # Bias toward scrolling down
            await page.evaluate(f'window.scrollBy(0, {scroll_y})')
            await asyncio.sleep(random.uniform(0.3, 1.0))
    
    @staticmethod
    async def explore_hover(page: Page, selector: str):
        """Hover over elements to simulate exploration."""
        elements = page.locator(selector)
        count = await elements.count()

        if count > 0:
            # Hover over 1-3 random elements
            for _ in range(random.randint(1, min(3, count))):
                idx = random.randint(0, count - 1)
                try:
                    await elements.nth(idx).hover()
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                except:
                    pass

    @staticmethod
    async def simulate_mouse_movement(page: Page, steps: int = None):
        """Generate realistic mouse movements so rrweb records MouseMove
        IncrementalSnapshot events.  These are the 'timeline indicator
        events' that LD's session pipeline checks for."""
        if steps is None:
            steps = random.randint(3, 6)
        viewport = page.viewport_size or {'width': 1280, 'height': 720}
        for _ in range(steps):
            x = random.randint(50, viewport['width'] - 50)
            y = random.randint(50, viewport['height'] - 50)
            try:
                await page.mouse.move(x, y, steps=random.randint(3, 8))
                await asyncio.sleep(random.uniform(0.1, 0.4))
            except Exception:
                pass

    @staticmethod
    async def interact_idle(page: Page, duration: float = 2.0):
        """Keep the page 'alive' with realistic idle interactions —
        mouse drifts and occasional scrolls — for the given duration.
        This ensures rrweb captures enough timeline events."""
        end = asyncio.get_event_loop().time() + duration
        viewport = page.viewport_size or {'width': 1280, 'height': 720}
        while asyncio.get_event_loop().time() < end:
            action = random.choices(
                ['mouse', 'scroll', 'pause'],
                weights=[0.5, 0.2, 0.3],
            )[0]
            try:
                if action == 'mouse':
                    x = random.randint(50, viewport['width'] - 50)
                    y = random.randint(50, viewport['height'] - 50)
                    await page.mouse.move(x, y, steps=random.randint(3, 8))
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                elif action == 'scroll':
                    delta = random.randint(50, 200) * random.choice([1, -1])
                    await page.evaluate(f'window.scrollBy(0, {delta})')
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                else:
                    await asyncio.sleep(random.uniform(0.3, 0.8))
            except Exception:
                await asyncio.sleep(0.3)


class ComprehensiveSessionScenario:
    """
    A comprehensive session that simulates a real user browsing the site.
    Hits all backend endpoints during a ~60 second session.
    
    Endpoints to hit:
    - /api/health (via dashboard)
    - /api/dashboard
    - /api/login
    - /api/users/<user_id>
    - /api/products (list)
    - /api/products/<id> (detail)
    - /api/search
    - /api/checkout
    - /api/orders
    """
    
    def __init__(self, target_duration: int = 30):
        self.name = "comprehensive_session"
        self.target_duration = target_duration
        self.endpoints_hit = set()
        self.api_errors = 0  # HTTP errors seen during this session

    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        """Execute a comprehensive user session with a hard timeout."""
        results = []
        start_time = datetime.now()
        self.endpoints_hit = set()
        self.api_errors = 0

        # Track HTTP error responses from the backend so feedback
        # sentiment can be weighted by the user's actual experience.
        def _on_response(response):
            if '/api/' in response.url and response.status >= 500:
                self.api_errors += 1

        page.on('response', _on_response)

        async def _run_phases():
            # Phase 1: Initial landing and exploration
            await self._phase_landing(page, results)

            # Phase 2: Browse products
            await self._phase_browse_products(page, results)

            # Phase 3: Search for something
            await self._phase_search(page, results)

            # Phase 4: Login
            await self._phase_login(page, user, results)

            # Phase 5: View account/dashboard
            await self._phase_account(page, user, results)

            # Phase 6: Add to cart and checkout
            await self._phase_checkout(page, user, results)

            # Phase 7: Submit qualitative feedback (sentiment based on errors)
            await self._phase_feedback(page, results)

            # Phase 8: AI support chat (~50% of sessions)
            await self._phase_chat(page, results)

            # Phase 9: Final browsing/exploration — fill up to target duration
            elapsed = (datetime.now() - start_time).total_seconds()
            remaining = max(0, self.target_duration - elapsed)
            if remaining > 3:
                await self._phase_final_exploration(page, results, remaining)

        try:
            await asyncio.wait_for(_run_phases(), timeout=SESSION_TIMEOUT)
        except asyncio.TimeoutError:
            results.append({
                'action': 'session_timeout',
                'success': False,
                'error': f'Session exceeded {SESSION_TIMEOUT}s hard limit',
                'phase': 'timeout',
            })
        except Exception as e:
            results.append({
                'action': 'session_error',
                'success': False,
                'error': str(e),
                'phase': 'unknown'
            })

        elapsed = (datetime.now() - start_time).total_seconds()

        return {
            'scenario': self.name,
            'user': user,
            'actions': results,
            'endpoints_hit': list(self.endpoints_hit),
            'session_duration_seconds': round(elapsed, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _read_visible_variants(self, page: Page) -> tuple[str, str]:
        """Read the visible frontend flag variants straight from the DOM.

        The ProductCard component sets `data-layout-variant` on each card
        and PromoBanner sets `data-variant` on the banner, so whatever the
        user actually sees is authoritative.  Returns (layout, promo) with
        sensible defaults when elements aren't present.
        """
        layout = 'standard'
        try:
            first_card = page.locator('[data-testid="product-card"]').first
            if await first_card.count() > 0:
                attr = await first_card.get_attribute('data-layout-variant')
                if attr:
                    layout = attr
        except Exception:
            pass

        promo = 'none'
        try:
            banner = page.locator('[data-testid="promo-banner"]')
            if await banner.count() > 0:
                attr = await banner.get_attribute('data-variant')
                if attr:
                    promo = attr
        except Exception:
            pass

        return layout, promo

    async def _phase_landing(self, page: Page, results: List[Dict]):
        """Land on homepage and look around."""
        # Navigate to home page
        await page.goto(FRONTEND_URL, wait_until='domcontentloaded', timeout=15000)
        self.endpoints_hit.add('/api/health')
        results.append({'action': 'view_home', 'success': True, 'phase': 'landing'})

        # Take time to look at the homepage — with idle interactions so
        # rrweb records enough timeline events for LD's session filter.
        await HumanClicker.interact_idle(page, random.uniform(3, 5))

        # Scroll around and move mouse
        await HumanClicker.scroll_randomly(page, random.randint(1, 3))
        await HumanClicker.simulate_mouse_movement(page)

        # Hover over some navigation elements
        await HumanClicker.explore_hover(page, 'nav a, [data-testid*="nav"]')

        await HumanTypist.hesitate(0.5, 1.5)
    
    async def _phase_browse_products(self, page: Page, results: List[Dict]):
        """Browse the products page."""
        # Navigate to products (try clicking first, then direct navigation)
        try:
            shop_btn = page.locator('[data-testid="shop-now-button"], a[href*="products"]')
            if await shop_btn.count() > 0:
                await HumanClicker.click_with_hesitation(page, '[data-testid="shop-now-button"], a[href*="products"]')
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
            else:
                await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded', timeout=10000)

            self.endpoints_hit.add('/api/products')
            results.append({'action': 'view_products_list', 'success': True, 'phase': 'browse'})
        except Exception as e:
            await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded', timeout=10000)
            self.endpoints_hit.add('/api/products')
            results.append({'action': 'view_products_list', 'success': True, 'phase': 'browse', 'note': 'direct nav'})
        
        # Take time to look at products — with mouse movement
        await HumanClicker.interact_idle(page, random.uniform(2, 4))
        await HumanClicker.scroll_randomly(page)
        await HumanClicker.simulate_mouse_movement(page)

        # Hover over some product cards
        await HumanClicker.explore_hover(page, '[data-testid="product-card"]')
        
        # Click on 1-2 products to view details
        product_cards = page.locator('[data-testid="product-card"]')
        count = await product_cards.count()
        
        if count > 0:
            products_to_view = random.randint(1, min(2, count))
            
            for i in range(products_to_view):
                try:
                    idx = random.randint(0, count - 1)
                    await HumanTypist.hesitate(0.5, 1.0)
                    await product_cards.nth(idx).click()
                    await page.wait_for_selector('[data-testid="product-detail"]', timeout=10000)
                    
                    self.endpoints_hit.add('/api/products/<id>')
                    results.append({'action': 'view_product_detail', 'success': True, 'phase': 'browse'})
                    
                    # Read product details — with mouse interaction
                    await HumanClicker.interact_idle(page, random.uniform(2, 5))
                    await HumanClicker.scroll_randomly(page, random.randint(1, 3))
                    
                    # Go back to products list
                    await page.go_back()
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)
                    await HumanTypist.quick_glance()
                    
                except Exception as e:
                    results.append({'action': 'view_product_detail', 'success': False, 'error': str(e), 'phase': 'browse'})
                    break
    
    async def _phase_search(self, page: Page, results: List[Dict]):
        """Search for products."""
        # Make sure we're on a page with search
        if '/products' not in page.url:
            await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded', timeout=10000)
            await HumanTypist.quick_glance()
        
        # Find search input
        search_input = page.locator('[data-testid="search-input"], input[type="search"], input[placeholder*="earch"]')
        
        if await search_input.count() > 0:
            # Pick a search query
            query_data = random.choice(SEARCH_QUERIES)
            final_query = query_data[0]
            
            # Decide whether to make typos (70% chance)
            if random.random() < 0.7 and query_data[1]:
                # Start with a typo version
                typo_query = random.choice(query_data[1])
                
                # Type the typo
                await HumanTypist.type_like_human(page, '[data-testid="search-input"], input[type="search"], input[placeholder*="earch"]', 
                                                   typo_query, make_typos=False, wpm=35)
                
                # Pause, "notice" the typo
                await HumanTypist.hesitate(0.8, 1.5)
                
                # Clear and retype correctly
                await search_input.first.fill('')
                await HumanTypist.hesitate(0.3, 0.5)
                await HumanTypist.type_like_human(page, '[data-testid="search-input"], input[type="search"], input[placeholder*="earch"]',
                                                   final_query, make_typos=False, wpm=50)
            else:
                # Type the query with possible typos
                await HumanTypist.type_like_human(page, '[data-testid="search-input"], input[type="search"], input[placeholder*="earch"]',
                                                   final_query, make_typos=True, wpm=40)
            
            await HumanTypist.hesitate(0.3, 0.6)
            
            # Submit search
            search_btn = page.locator('[data-testid="search-button"]')
            if await search_btn.count() > 0:
                await search_btn.click()
            else:
                await search_input.first.press('Enter')
            
            await HumanTypist.hesitate(0.5, 1.0)
            
            self.endpoints_hit.add('/api/search')
            results.append({'action': 'search', 'query': final_query, 'success': True, 'phase': 'search'})
            
            # Look at search results
            await HumanTypist.read_page(1, 3)
            
            # Maybe click on a result
            if random.random() > 0.4:
                product_cards = page.locator('[data-testid="product-card"]')
                if await product_cards.count() > 0:
                    await HumanTypist.hesitate(0.5, 1.0)
                    await product_cards.first.click()
                    try:
                        await page.wait_for_selector('[data-testid="product-detail"]', timeout=5000)
                        self.endpoints_hit.add('/api/products/<id>')
                        results.append({'action': 'view_search_result', 'success': True, 'phase': 'search'})
                        await HumanTypist.read_page(1, 2)
                    except:
                        pass
        else:
            # Navigate with query parameter
            query = random.choice(SEARCH_QUERIES)[0]
            await page.goto(f"{FRONTEND_URL}/products?q={query}", wait_until='domcontentloaded', timeout=10000)
            self.endpoints_hit.add('/api/search')
            results.append({'action': 'search', 'query': query, 'success': True, 'phase': 'search', 'note': 'via url'})
            await HumanTypist.read_page(1, 2)
    
    async def _phase_login(self, page: Page, user: dict, results: List[Dict]):
        """Login to the account."""
        await page.goto(f"{FRONTEND_URL}/login", wait_until='domcontentloaded', timeout=10000)
        results.append({'action': 'view_login', 'success': True, 'phase': 'login'})
        await HumanTypist.read_page(1, 2)
        
        try:
            # Try demo login buttons first
            demo_btn = page.locator(f'[data-testid="demo-login-{user["email"]}"], [data-testid^="demo-login"]')
            
            if await demo_btn.count() > 0:
                # Click on a demo login button
                await HumanTypist.hesitate(0.5, 1.5)
                await demo_btn.first.click()
                await HumanTypist.hesitate(1, 2)
                
                self.endpoints_hit.add('/api/login')
                results.append({'action': 'demo_login', 'success': True, 'phase': 'login'})
            else:
                # Manual login with form
                email_input = page.locator('[data-testid="email-input"], input[type="email"], input[name="email"]')
                password_input = page.locator('[data-testid="password-input"], input[type="password"], input[name="password"]')
                
                if await email_input.count() > 0 and await password_input.count() > 0:
                    # Type email slowly
                    await HumanTypist.type_like_human(page, 
                        '[data-testid="email-input"], input[type="email"], input[name="email"]',
                        user['email'], make_typos=True, wpm=35)
                    
                    await HumanTypist.hesitate(0.5, 1.0)
                    
                    # Type password (faster, muscle memory)
                    await HumanTypist.type_like_human(page,
                        '[data-testid="password-input"], input[type="password"], input[name="password"]',
                        'demo123', make_typos=False, wpm=60)
                    
                    await HumanTypist.hesitate(0.3, 0.7)
                    
                    # Click login
                    login_btn = page.locator('[data-testid="login-button"], button[type="submit"]')
                    if await login_btn.count() > 0:
                        await login_btn.click()
                        await HumanTypist.hesitate(1, 2)
                        
                        self.endpoints_hit.add('/api/login')
                        results.append({'action': 'manual_login', 'success': True, 'phase': 'login'})
        except Exception as e:
            results.append({'action': 'login', 'success': False, 'error': str(e), 'phase': 'login'})
    
    async def _phase_account(self, page: Page, user: dict, results: List[Dict]):
        """View account and dashboard."""
        # Try to access account page
        try:
            await page.goto(f"{FRONTEND_URL}/account", wait_until='domcontentloaded', timeout=10000)
            self.endpoints_hit.add('/api/users/<user_id>')
            results.append({'action': 'view_account', 'success': True, 'phase': 'account'})
            await HumanClicker.interact_idle(page, random.uniform(2, 4))
            await HumanClicker.scroll_randomly(page, random.randint(1, 3))
            await HumanClicker.simulate_mouse_movement(page)
        except Exception as e:
            results.append({'action': 'view_account', 'success': False, 'error': str(e), 'phase': 'account'})
        
        # Try to access dashboard (if available)
        try:
            # Look for dashboard link
            dashboard_link = page.locator('[data-testid="dashboard-link"], a[href*="dashboard"]')
            if await dashboard_link.count() > 0:
                await HumanClicker.click_with_hesitation(page, '[data-testid="dashboard-link"], a[href*="dashboard"]')
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
            else:
                # Navigate directly
                await page.goto(f"{FRONTEND_URL}/dashboard", wait_until='domcontentloaded', timeout=10000)
            
            self.endpoints_hit.add('/api/dashboard')
            results.append({'action': 'view_dashboard', 'success': True, 'phase': 'account'})
            await HumanTypist.read_page(2, 3)
        except Exception as e:
            # Dashboard might not exist in all apps
            results.append({'action': 'view_dashboard', 'success': False, 'error': str(e), 'phase': 'account'})
        
        # Try to view orders
        try:
            orders_link = page.locator('[data-testid="orders-link"], a[href*="orders"]')
            if await orders_link.count() > 0:
                await HumanClicker.click_with_hesitation(page, '[data-testid="orders-link"], a[href*="orders"]')
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                self.endpoints_hit.add('/api/orders')
                results.append({'action': 'view_orders', 'success': True, 'phase': 'account'})
                await HumanTypist.read_page(1, 2)
        except:
            pass
    
    async def _phase_checkout(self, page: Page, user: dict, results: List[Dict]):
        """Add items to cart and go through checkout.

        The simulator's add-to-cart and cart-size behavior is biased by the
        visible flag variants so the metrics downstream actually move when
        flags are flipped.  This is what makes the LD demo story show up:
        without this, flipping a frontend flag does nothing to conversions
        because the Playwright bot clicks everything deterministically.
        """
        # Go back to products
        await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded', timeout=10000)
        await HumanTypist.quick_glance()

        # Read the layout + promo variants directly from the DOM — this is
        # literally what the user saw, not a re-eval of the flag.
        layout_variant, promo_variant = await self._read_visible_variants(page)

        # Bias add-to-cart probability per layout variant. Rationale:
        #   - detailed: more info, social proof → users convert more
        #   - minimal:  price hidden, fewer trust signals → users hesitate
        #   - standard: baseline
        add_to_cart_probability = {
            'detailed': 0.92,
            'standard': 0.80,
            'minimal':  0.55,
        }.get(layout_variant, 0.80)

        # Promo banners nudge people to add more items (free-shipping
        # threshold) or act faster (urgency). "percent-off" slightly lifts
        # baseline add rate.
        promo_add_bump = {
            'free-shipping-50': 0.05,
            'percent-off':      0.07,
            'urgency':          0.10,
            'none':             0.0,
        }.get(promo_variant, 0.0)
        add_to_cart_probability = min(0.99, add_to_cart_probability + promo_add_bump)

        # Decide how many distinct products to add. free-shipping-50 pushes
        # users to basket-build toward the threshold.
        extra_item_rolls = {
            'free-shipping-50': 2,  # try to add up to 3 items total
            'percent-off':      1,
            'urgency':          0,  # rushed, grab one and go
            'none':             1,
        }.get(promo_variant, 1)

        # Click on a primary product
        product_cards = page.locator('[data-testid="product-card"]')
        card_count = await product_cards.count()
        if card_count > 0:
            idx = random.randint(0, card_count - 1)
            await HumanTypist.hesitate(0.5, 1.0)
            await product_cards.nth(idx).click()

            try:
                await page.wait_for_selector('[data-testid="product-detail"]', timeout=10000)
                await HumanTypist.read_page(1, 2)

                # Bias: sometimes bail without adding to cart
                if random.random() < add_to_cart_probability:
                    add_btn = page.locator('[data-testid="add-to-cart"]')
                    if await add_btn.count() > 0:
                        await HumanClicker.click_with_hesitation(page, '[data-testid="add-to-cart"]')
                        await HumanTypist.hesitate(0.5, 1.0)
                        results.append({
                            'action': 'add_to_cart',
                            'success': True,
                            'phase': 'checkout',
                            'layout_variant': layout_variant,
                            'promo_variant': promo_variant,
                        })
                else:
                    results.append({
                        'action': 'skip_add_to_cart',
                        'success': True,
                        'phase': 'checkout',
                        'layout_variant': layout_variant,
                        'promo_variant': promo_variant,
                        'reason': 'variant_bias',
                    })
            except:
                pass

        # Optionally add extra items to basket (basket-build behavior).
        for _ in range(extra_item_rolls):
            if random.random() > add_to_cart_probability * 0.7:
                continue
            try:
                await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded', timeout=10000)
                extra_cards = page.locator('[data-testid="product-card"]')
                extra_count = await extra_cards.count()
                if extra_count == 0:
                    break
                extra_idx = random.randint(0, extra_count - 1)
                await extra_cards.nth(extra_idx).click()
                await page.wait_for_selector('[data-testid="add-to-cart"]', timeout=5000)
                await HumanTypist.hesitate(0.3, 0.7)
                await HumanClicker.click_with_hesitation(page, '[data-testid="add-to-cart"]')
                results.append({
                    'action': 'add_extra_to_cart',
                    'success': True,
                    'phase': 'checkout',
                    'promo_variant': promo_variant,
                })
            except:
                break
        
        # Go to cart
        try:
            cart_icon = page.locator('[data-testid="cart-icon"], a[href*="cart"]')
            if await cart_icon.count() > 0:
                await HumanClicker.click_with_hesitation(page, '[data-testid="cart-icon"], a[href*="cart"]')
            else:
                await page.goto(f"{FRONTEND_URL}/cart", wait_until='domcontentloaded')
            
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            results.append({'action': 'view_cart', 'success': True, 'phase': 'checkout'})
            await HumanTypist.read_page(1, 2)
            
            # Scroll to look at cart items
            await HumanClicker.scroll_randomly(page, random.randint(0, 1))
        except Exception as e:
            results.append({'action': 'view_cart', 'success': False, 'error': str(e), 'phase': 'checkout'})
        
        # Click checkout
        try:
            checkout_btn = page.locator('[data-testid="checkout-button"], button:has-text("Checkout")')
            if await checkout_btn.count() > 0:
                await HumanTypist.hesitate(0.5, 1.5)
                await checkout_btn.click()
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                results.append({'action': 'start_checkout', 'success': True, 'phase': 'checkout'})
                await HumanTypist.read_page(1, 2)
                
                # Fill shipping form
                await self._fill_shipping_form(page, user, results)
                
                # Fill payment form
                await self._fill_payment_form(page, user, results)
                
                # Place order
                place_order_btn = page.locator('[data-testid="place-order"], button:has-text("Place Order")')
                if await place_order_btn.count() > 0:
                    await HumanTypist.hesitate(1, 2)  # Think before committing
                    await place_order_btn.click()
                    await HumanTypist.hesitate(2, 4)
                    
                    self.endpoints_hit.add('/api/checkout')
                    results.append({'action': 'place_order', 'success': True, 'phase': 'checkout'})
                    
                    # Check for confirmation
                    try:
                        await page.wait_for_selector('[data-testid="order-confirmation"]', timeout=5000)
                        self.endpoints_hit.add('/api/orders')
                        results.append({'action': 'order_confirmed', 'success': True, 'phase': 'checkout'})
                        await HumanTypist.read_page(2, 3)
                    except:
                        pass
        except Exception as e:
            results.append({'action': 'checkout', 'success': False, 'error': str(e), 'phase': 'checkout'})
    
    async def _fill_shipping_form(self, page: Page, user: dict, results: List[Dict]):
        """Fill the shipping form with human-like typing."""
        fields = [
            ('[data-testid="first-name-input"], input[name="firstName"]', 'Demo', 30),
            ('[data-testid="last-name-input"], input[name="lastName"]', 'User', 35),
            ('[data-testid="shipping-email-input"], input[name="email"]', user['email'], 40),
            ('[data-testid="address-input"], input[name="address"]', '123 Demo Street', 45),
            ('[data-testid="city-input"], input[name="city"]', 'San Francisco', 50),
            ('[data-testid="state-input"], input[name="state"]', 'CA', 60),
            ('[data-testid="zip-input"], input[name="zip"]', '94105', 55),
        ]
        
        for selector, value, wpm in fields:
            element = page.locator(selector)
            if await element.count() > 0:
                await HumanTypist.type_like_human(page, selector, value, make_typos=random.random() < 0.15, wpm=wpm)
                await HumanTypist.hesitate(0.2, 0.5)
        
        # Click continue
        continue_btn = page.locator('[data-testid="continue-to-payment"], button:has-text("Continue")')
        if await continue_btn.count() > 0:
            await HumanTypist.hesitate(0.5, 1.0)
            await continue_btn.click()
            await HumanTypist.hesitate(0.5, 1.0)
            results.append({'action': 'submit_shipping', 'success': True, 'phase': 'checkout'})
    
    async def _fill_payment_form(self, page: Page, user: dict, results: List[Dict]):
        """Fill the payment form with human-like typing."""
        fields = [
            ('[data-testid="card-number"], input[name="cardNumber"]', '4242 4242 4242 4242', 35),
            ('[data-testid="card-name"], input[name="cardName"]', user['name'], 45),
            ('[data-testid="card-expiry"], input[name="expiry"]', '12/25', 50),
            ('[data-testid="card-cvv"], input[name="cvv"]', '123', 60),
        ]
        
        for selector, value, wpm in fields:
            element = page.locator(selector)
            if await element.count() > 0:
                await HumanTypist.type_like_human(page, selector, value, make_typos=False, wpm=wpm)
                await HumanTypist.hesitate(0.2, 0.4)
        
        results.append({'action': 'fill_payment', 'success': True, 'phase': 'checkout'})
    
    async def _phase_feedback(self, page: Page, results: List[Dict]):
        """Submit qualitative feedback via the LD SDK.

        Sentiment is weighted by how many HTTP 5xx errors the user saw
        during this session:
          - 0 errors:  60% positive, 30% neutral, 10% negative
          - 1-2 errors: 20% positive, 30% neutral, 50% negative
          - 3+ errors: 5% positive, 10% neutral, 85% negative

        ~80% of sessions leave feedback to generate a healthy volume.
        """
        if random.random() > 0.80:
            # 20% of sessions skip feedback entirely
            return

        # Choose sentiment based on errors observed
        if self.api_errors == 0:
            sentiment = random.choices(
                ['positive', 'neutral', 'negative'],
                weights=[0.60, 0.30, 0.10],
            )[0]
        elif self.api_errors <= 2:
            sentiment = random.choices(
                ['positive', 'neutral', 'negative'],
                weights=[0.20, 0.30, 0.50],
            )[0]
        else:
            sentiment = random.choices(
                ['positive', 'neutral', 'negative'],
                weights=[0.05, 0.10, 0.85],
            )[0]

        # Pick feedback text matching sentiment
        if sentiment == 'positive':
            text = random.choice(FEEDBACK_POSITIVE)
        elif sentiment == 'neutral':
            text = random.choice(FEEDBACK_NEUTRAL)
        else:
            text = random.choice(FEEDBACK_NEGATIVE)

        # Pick a flag to associate. Bias toward migrate-warehouse-api
        # when errors were observed since it's the error source.
        if self.api_errors > 0 and random.random() < 0.70:
            flag_key = 'migrate-warehouse-api'
        else:
            flag_key = random.choice(FEEDBACK_FLAG_KEYS)

        try:
            success = await page.evaluate(
                """([flagKey, sentiment, text]) => {
                    if (typeof window.__submitFeedback === 'function') {
                        return window.__submitFeedback(flagKey, sentiment, text);
                    }
                    return false;
                }""",
                [flag_key, sentiment, text],
            )
            results.append({
                'action': 'submit_feedback',
                'success': bool(success),
                'phase': 'feedback',
                'sentiment': sentiment,
                'flag_key': flag_key,
                'api_errors_seen': self.api_errors,
            })
        except Exception as e:
            results.append({
                'action': 'submit_feedback',
                'success': False,
                'error': str(e),
                'phase': 'feedback',
            })

        # Brief pause after submitting
        await HumanTypist.hesitate(0.5, 1.0)

    async def _phase_chat(self, page: Page, results: List[Dict]):
        """Open the AI support chatbot and ask 1-3 questions.

        ~50% of sessions interact with the chatbot. Messages are sent via
        the programmatic window.__sendChatMessage(text) API exposed by
        ChatWidget, which calls POST /api/chat → chat-service → Ollama.

        LLM inference can take several seconds, so we wait generously for
        each response before sending the next question.
        """
        if random.random() > 0.50:
            # Half of sessions skip the chatbot
            return

        questions = random.sample(CHAT_QUESTIONS, k=random.randint(1, 3))

        for i, question in enumerate(questions):
            try:
                # LLM inference may be slow on CPU-only Ollama — allow
                # up to 30s for the round-trip (default 10s is too tight).
                response = await asyncio.wait_for(
                    page.evaluate(
                        """async (text) => {
                            if (typeof window.__sendChatMessage === 'function') {
                                return await window.__sendChatMessage(text);
                            }
                            return null;
                        }""",
                        question,
                    ),
                    timeout=30,
                )

                success = response is not None
                results.append({
                    'action': 'chat_message',
                    'success': success,
                    'phase': 'chat',
                    'question': question,
                    'response_length': len(response) if response else 0,
                    'message_index': i + 1,
                })

                if success:
                    self.endpoints_hit.add('/api/chat')

                # Brief pause between messages — like reading the response
                await HumanTypist.read_page(1.5, 3.0)

            except Exception as e:
                results.append({
                    'action': 'chat_message',
                    'success': False,
                    'error': str(e),
                    'phase': 'chat',
                    'question': question,
                    'message_index': i + 1,
                })
                # Don't bail on error — try next question
                await HumanTypist.hesitate(0.5, 1.0)

        # Submit thumbs up/down feedback on the last bot response (~70% of
        # chatbot users give feedback).  Sentiment is weighted by how many
        # API errors were seen during the session, similar to _phase_feedback.
        if random.random() < 0.70:
            # Decide sentiment based on error count
            if self.api_errors == 0:
                sentiment = random.choices(
                    ['positive', 'negative'],
                    weights=[0.75, 0.25],
                )[0]
            elif self.api_errors <= 2:
                sentiment = random.choices(
                    ['positive', 'negative'],
                    weights=[0.40, 0.60],
                )[0]
            else:
                sentiment = random.choices(
                    ['positive', 'negative'],
                    weights=[0.15, 0.85],
                )[0]

            try:
                feedback_sent = await page.evaluate(
                    """async (sentiment) => {
                        if (typeof window.__sendChatFeedback === 'function') {
                            return await window.__sendChatFeedback(sentiment);
                        }
                        return false;
                    }""",
                    sentiment,
                )
                results.append({
                    'action': 'chat_feedback',
                    'success': bool(feedback_sent),
                    'phase': 'chat',
                    'sentiment': sentiment,
                    'api_errors_seen': self.api_errors,
                })
            except Exception as e:
                results.append({
                    'action': 'chat_feedback',
                    'success': False,
                    'error': str(e),
                    'phase': 'chat',
                })

        # Brief pause after finishing chat
        await HumanTypist.hesitate(0.5, 1.0)

    async def _phase_final_exploration(self, page: Page, results: List[Dict], time_remaining: float):
        """Use remaining time to explore more of the site with rich
        mouse/scroll interactions that rrweb records as timeline events."""
        actions_done = 0
        max_actions = int(time_remaining / 4)  # ~4 seconds per action

        while actions_done < max_actions:
            action = random.choice(['browse', 'scroll', 'navigate', 'interact'])

            try:
                if action == 'browse':
                    await page.goto(f"{FRONTEND_URL}/products",
                                    wait_until='domcontentloaded', timeout=10000)
                    await HumanClicker.interact_idle(page, random.uniform(1.5, 3))
                    await HumanClicker.scroll_randomly(page)

                elif action == 'scroll':
                    await HumanClicker.scroll_randomly(page, random.randint(2, 4))
                    await HumanClicker.simulate_mouse_movement(page)
                    await HumanTypist.read_page(0.5, 1.5)

                elif action == 'navigate':
                    pages = ['/', '/products', '/cart', '/account']
                    target = random.choice(pages)
                    await page.goto(f"{FRONTEND_URL}{target}",
                                    wait_until='domcontentloaded', timeout=10000)
                    await HumanClicker.interact_idle(page, random.uniform(1.5, 2.5))

                elif action == 'interact':
                    # Pure interaction time — mouse moves + scrolls
                    await HumanClicker.interact_idle(page, random.uniform(2, 4))

            except Exception:
                pass

            actions_done += 1
            results.append({'action': f'explore_{action}', 'success': True, 'phase': 'exploration'})


class TrafficGenerator:
    """Generates realistic browser-based traffic patterns."""
    
    def __init__(self, sessions_per_minute: int = 2):
        self.sessions_per_minute = sessions_per_minute
        self.session_count = 0
        self.error_count = 0
        self.success_count = 0
        self.browser: Optional[Browser] = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
        self.scenario = ComprehensiveSessionScenario(target_duration=TARGET_SESSION_DURATION)

        # Ensure log directory exists
        os.makedirs(os.path.dirname(SESSION_LOG_FILE), exist_ok=True)
        os.makedirs(os.path.dirname(EVENT_LOG_FILE), exist_ok=True)

    def select_user(self) -> dict:
        """Select a random user for the session."""
        return get_random_user()

    def _log_session_key(self, user_key: str, session_id: str):
        """Append user key to the session log file.

        Each line: <ISO timestamp> | <session_id> | <user_key>
        Tail this file to see which keys should have sessions + flag evals.
        """
        try:
            with open(SESSION_LOG_FILE, "a") as f:
                f.write(f"{datetime.now().isoformat()} | {session_id} | {user_key}\n")
        except Exception as e:
            print(f"  [log error] session log: {e}")

    def _log_events(self, user_key: str, session_id: str, events: list):
        """Log LD event payloads to the event log file.

        Writes a summary of each event batch:  which kinds, which flag keys,
        and the user key, so you can cross-reference with the session log.
        """
        try:
            feature_flags = []
            kinds = {}
            for evt in events:
                k = evt.get("kind", "unknown")
                kinds[k] = kinds.get(k, 0) + 1
                if k == "feature":
                    feature_flags.append(evt.get("key", "?"))

            with open(EVENT_LOG_FILE, "a") as f:
                line = (
                    f"{datetime.now().isoformat()} | {session_id} | {user_key}"
                    f" | kinds={json.dumps(kinds)}"
                )
                if feature_flags:
                    line += f" | flags={','.join(feature_flags)}"
                f.write(line + "\n")
        except Exception as e:
            print(f"  [log error] event log: {e}")
    
    async def run_session(self, context: BrowserContext) -> Dict[str, Any]:
        """Run a single browser session with a hard timeout guard."""
        async with self.semaphore:
            self.session_count += 1
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            user = self.select_user()
            start_time = datetime.now()

            print(f"[{datetime.now().isoformat()}] Session {session_id} starting: {user['email']}")

            page = await context.new_page()

            # --- Stealth: mask Playwright automation signals ---
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false, configurable: true,
                });
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'MacIntel', configurable: true,
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'], configurable: true,
                });
                if (!window.chrome) { window.chrome = {}; }
                if (!window.chrome.runtime) {
                    window.chrome.runtime = { id: undefined };
                }
            """)

            # Inject user identity
            user_json = json.dumps(user)
            await page.add_init_script(f"window.__LD_USER__ = {user_json};")

            # --- Monitor LD event traffic ---
            events_seen = {"bulk": 0, "feature": 0, "summary": 0, "identify": 0, "custom": 0}

            async def monitor_ld_events(route):
                request = route.request
                url = request.url
                try:
                    if request.method == "POST" and "events.launchdarkly.com/events/bulk" in url:
                        raw = request.post_data_buffer
                        if raw:
                            try:
                                payload = json.loads(raw)
                            except Exception:
                                try:
                                    payload = json.loads(gzip.decompress(raw))
                                except Exception:
                                    payload = None
                            if isinstance(payload, list):
                                events_seen["bulk"] += 1
                                for evt in payload:
                                    kind = evt.get("kind", "unknown")
                                    events_seen[kind] = events_seen.get(kind, 0) + 1
                                self._log_events(user["key"], session_id, payload)
                except Exception:
                    pass
                await route.continue_()

            await page.route("**/events.launchdarkly.com/**", monitor_ld_events)
            self._log_session_key(user["key"], session_id)

            # ---- Run the session (no force-kill — let it complete) ----
            result = None
            try:
                r = await self.scenario.execute(page, user)
                r['session_id'] = session_id
                # Flush events before close
                try:
                    await page.evaluate("""async () => {
                        if (window.__ldClient) await window.__ldClient.flush();
                        window.dispatchEvent(new Event('pagehide'));
                    }""")
                    await asyncio.sleep(1)
                except Exception:
                    pass
                result = r
            except Exception as e:
                self.error_count += 1
                print(f"[{datetime.now().isoformat()}] Session {session_id} error: {e}")
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

            elapsed = (datetime.now() - start_time).total_seconds()

            if result is None:
                return {
                    'session_id': session_id, 'scenario': 'comprehensive_session',
                    'user': user, 'error': 'unknown',
                    'timestamp': datetime.now().isoformat(),
                }

            # Log event summary
            if events_seen["bulk"] > 0:
                print(f"  [{session_id}] LD events: {events_seen}")

            failed = any(not a.get('success', True) for a in result.get('actions', []))
            if failed:
                self.error_count += 1
            else:
                self.success_count += 1

            endpoints = result.get('endpoints_hit', [])
            duration = result.get('session_duration_seconds', 0)
            print(f"[{datetime.now().isoformat()}] Session {session_id} completed: "
                  f"{duration:.1f}s, {len(endpoints)} endpoints, "
                  f"{len(result.get('actions', []))} actions")
            return result
    
    async def run_forever(self):
        """Run traffic generation forever with overlapping sessions."""
        interval = 60.0 / self.sessions_per_minute
        
        # Calculate expected concurrent sessions
        expected_concurrent = TARGET_SESSION_DURATION / interval
        
        print(f"\n{'='*70}")
        print(f"  LaunchDarkly Observability Demo - Human-like Traffic Generator")
        print(f"{'='*70}")
        print(f"  Frontend: {FRONTEND_URL}")
        print(f"  Rate: {self.sessions_per_minute} sessions/minute")
        print(f"  Target session duration: {TARGET_SESSION_DURATION} seconds")
        print(f"  Interval: {interval:.2f} seconds between session starts")
        print(f"  Expected concurrent sessions: ~{expected_concurrent:.1f}")
        print(f"  Max concurrent browsers: {MAX_CONCURRENT_BROWSERS}")
        print(f"{'='*70}")
        print(f"  Human-like behaviors enabled:")
        print(f"    - Typing with variable speed (30-60 WPM)")
        print(f"    - Typos and corrections")
        print(f"    - Reading/hesitation delays")
        print(f"    - Random scrolling and hovering")
        print(f"    - Full endpoint coverage per session")
        print(f"{'='*70}\n")
        
        async with async_playwright() as p:
            # Launch browser with stealth flags to avoid bot detection.
            # LD's session replay pipeline (via Highlight) filters sessions
            # from automated browsers, so we mask automation signals.
            self.browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                ],
            )

            # Create a persistent context for better session handling.
            # Set aggressive default timeouts so individual Playwright
            # operations fail fast instead of hanging the whole session.
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
            )
            context.set_default_timeout(10000)           # 10s for selectors, clicks, etc.
            context.set_default_navigation_timeout(15000) # 15s for goto / load states
            
            # Track running session tasks
            running_tasks: set = set()
            
            async def session_wrapper():
                """Wrapper to run session and print stats."""
                task = asyncio.current_task()
                running_tasks.add(task)
                try:
                    await self.run_session(context)
                    
                    # Print stats every 5 sessions
                    if self.session_count % 5 == 0:
                        error_rate = (self.error_count / self.session_count * 100) if self.session_count > 0 else 0
                        print(f"\n{'='*50}")
                        print(f"[Stats] Sessions: {self.session_count}, "
                              f"Success: {self.success_count}, "
                              f"Errors: {self.error_count} ({error_rate:.1f}%), "
                              f"Active: {len(running_tasks)}")
                        print(f"{'='*50}\n")
                except Exception as e:
                    print(f"Error in session: {e}")
                finally:
                    running_tasks.discard(task)
            
            try:
                while True:
                    try:
                        # Spawn session without waiting for it to complete
                        asyncio.create_task(session_wrapper())
                        
                        # Wait before starting next session
                        await asyncio.sleep(interval)
                        
                    except KeyboardInterrupt:
                        print("\n\nShutting down traffic generator...")
                        break
                    except Exception as e:
                        print(f"Error in traffic loop: {e}")
                        await asyncio.sleep(interval)
            finally:
                # Wait for running sessions to complete before closing
                if running_tasks:
                    print(f"Waiting for {len(running_tasks)} active sessions to complete...")
                    await asyncio.gather(*running_tasks, return_exceptions=True)
                await context.close()
                await self.browser.close()
    
    def run(self):
        """Start the traffic generator."""
        asyncio.run(self.run_forever())


def main():
    """Main entry point."""
    generator = TrafficGenerator(sessions_per_minute=SESSIONS_PER_MINUTE)
    generator.run()


if __name__ == '__main__':
    main()
