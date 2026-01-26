"""
Traffic Generator - Generates realistic browser-based traffic for LaunchDarkly observability demo.
Uses Playwright for headless browser automation to generate real frontend sessions.
"""

import os
import sys
import random
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Add backend directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from shared.users import USER_PERSONAS, get_random_user

# Configuration
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
SESSIONS_PER_MINUTE = int(os.getenv('SESSIONS_PER_MINUTE', '10'))
MAX_CONCURRENT_BROWSERS = int(os.getenv('MAX_CONCURRENT_BROWSERS', '3'))


class BrowserScenario:
    """Base class for browser-based scenarios."""
    
    def __init__(self, name: str, weight: int, requires_auth: bool = False):
        self.name = name
        self.weight = weight
        self.requires_auth = requires_auth
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        raise NotImplementedError
    
    async def human_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        """Simulate human-like delays between actions."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))


class BrowseProductsScenario(BrowserScenario):
    """User browses products and views product details."""
    
    def __init__(self):
        super().__init__("browse_products", weight=35)
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        results = []
        
        # Navigate to home page
        await page.goto(FRONTEND_URL, wait_until='domcontentloaded')
        results.append({'action': 'view_home', 'success': True})
        await self.human_delay(1, 3)
        
        # Click on "Shop Now" or navigate to products
        try:
            shop_btn = page.locator('[data-testid="shop-now-button"]')
            if await shop_btn.count() > 0:
                await shop_btn.click()
            else:
                await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded')
            
            await page.wait_for_selector('[data-testid="product-grid"]', timeout=10000)
            results.append({'action': 'view_products', 'success': True})
        except Exception as e:
            results.append({'action': 'view_products', 'success': False, 'error': str(e)})
            return {'scenario': self.name, 'user': user, 'actions': results}
        
        await self.human_delay(1, 2)
        
        # Click on 1-3 random products
        product_cards = page.locator('[data-testid="product-card"]')
        count = await product_cards.count()
        
        if count > 0:
            for _ in range(random.randint(1, min(3, count))):
                try:
                    idx = random.randint(0, count - 1)
                    await product_cards.nth(idx).click()
                    await page.wait_for_selector('[data-testid="product-detail"]', timeout=10000)
                    results.append({'action': 'view_product_detail', 'success': True})
                    await self.human_delay(2, 5)  # Simulate reading product details
                    await page.go_back()
                    await page.wait_for_selector('[data-testid="product-grid"]', timeout=10000)
                except Exception as e:
                    results.append({'action': 'view_product_detail', 'success': False, 'error': str(e)})
                    break
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class SearchProductsScenario(BrowserScenario):
    """User searches for products."""
    
    def __init__(self):
        super().__init__("search_products", weight=15)
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        results = []
        queries = ['feature flags', 'rollout', 'testing', 'targeting', 'sdk', 'experiment']
        query = random.choice(queries)
        
        # Navigate to home page
        await page.goto(FRONTEND_URL, wait_until='domcontentloaded')
        results.append({'action': 'view_home', 'success': True})
        await self.human_delay(0.5, 1.5)
        
        # Find and use search bar
        try:
            search_input = page.locator('[data-testid="search-input"]')
            if await search_input.count() > 0:
                await search_input.fill(query)
                await self.human_delay(0.3, 0.8)
                
                search_btn = page.locator('[data-testid="search-button"]')
                if await search_btn.count() > 0:
                    await search_btn.click()
                else:
                    await search_input.press('Enter')
                
                await page.wait_for_selector('[data-testid="product-grid"]', timeout=10000)
                results.append({'action': 'search', 'query': query, 'success': True})
            else:
                # Navigate directly to products with search query
                await page.goto(f"{FRONTEND_URL}/products?q={query}", wait_until='domcontentloaded')
                results.append({'action': 'search', 'query': query, 'success': True})
        except Exception as e:
            results.append({'action': 'search', 'query': query, 'success': False, 'error': str(e)})
        
        await self.human_delay(1, 2)
        
        # Maybe click on a search result
        if random.random() > 0.5:
            try:
                product_cards = page.locator('[data-testid="product-card"]')
                if await product_cards.count() > 0:
                    await product_cards.first.click()
                    await page.wait_for_selector('[data-testid="product-detail"]', timeout=10000)
                    results.append({'action': 'view_search_result', 'success': True})
            except Exception as e:
                results.append({'action': 'view_search_result', 'success': False, 'error': str(e)})
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class AddToCartScenario(BrowserScenario):
    """User adds products to cart."""
    
    def __init__(self):
        super().__init__("add_to_cart", weight=20)
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        results = []
        
        # Navigate to products
        await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded')
        results.append({'action': 'view_products', 'success': True})
        await self.human_delay(1, 2)
        
        # Click on a product
        try:
            product_cards = page.locator('[data-testid="product-card"]')
            count = await product_cards.count()
            if count > 0:
                await product_cards.nth(random.randint(0, count - 1)).click()
                await page.wait_for_selector('[data-testid="product-detail"]', timeout=10000)
                results.append({'action': 'view_product', 'success': True})
                await self.human_delay(1, 3)
                
                # Add to cart
                add_btn = page.locator('[data-testid="add-to-cart"]')
                if await add_btn.count() > 0:
                    await add_btn.click()
                    await self.human_delay(0.5, 1)
                    results.append({'action': 'add_to_cart', 'success': True})
                    
                    # View cart
                    cart_icon = page.locator('[data-testid="cart-icon"]')
                    if await cart_icon.count() > 0:
                        await cart_icon.click()
                        await page.wait_for_selector('[data-testid="cart-page"]', timeout=10000)
                        results.append({'action': 'view_cart', 'success': True})
        except Exception as e:
            results.append({'action': 'add_to_cart', 'success': False, 'error': str(e)})
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class LoginScenario(BrowserScenario):
    """User logs in to their account."""
    
    def __init__(self):
        super().__init__("user_login", weight=15)
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        results = []
        
        # Navigate to login page
        await page.goto(f"{FRONTEND_URL}/login", wait_until='domcontentloaded')
        results.append({'action': 'view_login', 'success': True})
        await self.human_delay(0.5, 1)
        
        try:
            # Fill in login form
            email_input = page.locator('[data-testid="email-input"]')
            password_input = page.locator('[data-testid="password-input"]')
            
            if await email_input.count() > 0 and await password_input.count() > 0:
                await email_input.fill(user['email'])
                await self.human_delay(0.3, 0.7)
                await password_input.fill('demo123')
                await self.human_delay(0.3, 0.5)
                
                login_btn = page.locator('[data-testid="login-button"]')
                if await login_btn.count() > 0:
                    await login_btn.click()
                    await self.human_delay(1, 2)
                    results.append({'action': 'login', 'success': True})
                    
                    # Check if redirected to account
                    if '/account' in page.url:
                        results.append({'action': 'view_account', 'success': True})
            else:
                # Try demo login buttons
                demo_btn = page.locator(f'[data-testid="demo-login-{user["email"]}"]')
                if await demo_btn.count() > 0:
                    await demo_btn.click()
                    await self.human_delay(1, 2)
                    results.append({'action': 'demo_login', 'success': True})
        except Exception as e:
            results.append({'action': 'login', 'success': False, 'error': str(e)})
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class CheckoutScenario(BrowserScenario):
    """User completes a full checkout flow."""
    
    def __init__(self):
        super().__init__("checkout_flow", weight=10, requires_auth=True)
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        results = []
        
        # First, add something to cart
        await page.goto(f"{FRONTEND_URL}/products", wait_until='domcontentloaded')
        results.append({'action': 'view_products', 'success': True})
        await self.human_delay(1, 2)
        
        try:
            # Click on first product and add to cart
            product_cards = page.locator('[data-testid="product-card"]')
            if await product_cards.count() > 0:
                await product_cards.first.click()
                await page.wait_for_selector('[data-testid="product-detail"]', timeout=10000)
                await self.human_delay(1, 2)
                
                add_btn = page.locator('[data-testid="add-to-cart"]')
                if await add_btn.count() > 0:
                    await add_btn.click()
                    await self.human_delay(0.5, 1)
                    results.append({'action': 'add_to_cart', 'success': True})
            
            # Go to cart
            await page.goto(f"{FRONTEND_URL}/cart", wait_until='domcontentloaded')
            results.append({'action': 'view_cart', 'success': True})
            await self.human_delay(1, 2)
            
            # Click checkout button
            checkout_btn = page.locator('[data-testid="checkout-button"]')
            if await checkout_btn.count() > 0:
                await checkout_btn.click()
                await page.wait_for_selector('[data-testid="checkout-page"]', timeout=10000)
                results.append({'action': 'view_checkout', 'success': True})
                await self.human_delay(1, 2)
                
                # Fill shipping form
                await page.locator('[data-testid="first-name-input"]').fill('Demo')
                await page.locator('[data-testid="last-name-input"]').fill('User')
                await page.locator('[data-testid="shipping-email-input"]').fill(user['email'])
                await page.locator('[data-testid="address-input"]').fill('123 Demo Street')
                await page.locator('[data-testid="city-input"]').fill('San Francisco')
                await page.locator('[data-testid="state-input"]').fill('CA')
                await page.locator('[data-testid="zip-input"]').fill('94105')
                await self.human_delay(0.5, 1)
                
                continue_btn = page.locator('[data-testid="continue-to-payment"]')
                if await continue_btn.count() > 0:
                    await continue_btn.click()
                    results.append({'action': 'submit_shipping', 'success': True})
                    await self.human_delay(1, 2)
                    
                    # Fill payment form
                    await page.locator('[data-testid="card-number"]').fill('4242 4242 4242 4242')
                    await page.locator('[data-testid="card-name"]').fill(user['name'])
                    await page.locator('[data-testid="card-expiry"]').fill('12/25')
                    await page.locator('[data-testid="card-cvv"]').fill('123')
                    await self.human_delay(0.5, 1)
                    
                    place_order_btn = page.locator('[data-testid="place-order"]')
                    if await place_order_btn.count() > 0:
                        await place_order_btn.click()
                        await self.human_delay(2, 4)
                        
                        # Check for confirmation
                        confirmation = page.locator('[data-testid="order-confirmation"]')
                        if await confirmation.count() > 0:
                            results.append({'action': 'complete_checkout', 'success': True})
                        else:
                            results.append({'action': 'complete_checkout', 'success': True, 'note': 'no confirmation visible'})
        except Exception as e:
            results.append({'action': 'checkout', 'success': False, 'error': str(e)})
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class ViewAccountScenario(BrowserScenario):
    """User views and updates their account settings."""
    
    def __init__(self):
        super().__init__("view_account", weight=5, requires_auth=True)
    
    async def execute(self, page: Page, user: dict) -> Dict[str, Any]:
        results = []
        
        # Login first
        await page.goto(f"{FRONTEND_URL}/login", wait_until='domcontentloaded')
        
        try:
            # Use demo login
            demo_btn = page.locator(f'[data-testid="demo-login-{user["email"]}"]')
            if await demo_btn.count() > 0:
                await demo_btn.click()
                await self.human_delay(1, 2)
                results.append({'action': 'login', 'success': True})
            else:
                # Manual login
                await page.locator('[data-testid="email-input"]').fill(user['email'])
                await page.locator('[data-testid="password-input"]').fill('demo123')
                await page.locator('[data-testid="login-button"]').click()
                await self.human_delay(1, 2)
                results.append({'action': 'login', 'success': True})
            
            # Navigate to account
            await page.goto(f"{FRONTEND_URL}/account", wait_until='domcontentloaded')
            results.append({'action': 'view_account', 'success': True})
            await self.human_delay(1, 2)
            
            # Navigate to settings
            settings_link = page.locator('[data-testid="settings-link"]')
            if await settings_link.count() > 0:
                await settings_link.click()
                await page.wait_for_selector('[data-testid="settings-page"]', timeout=10000)
                results.append({'action': 'view_settings', 'success': True})
                await self.human_delay(1, 2)
                
                # Update a setting
                theme_select = page.locator('[data-testid="theme-select"]')
                if await theme_select.count() > 0:
                    await theme_select.select_option(random.choice(['light', 'dark', 'auto']))
                    save_btn = page.locator('[data-testid="save-settings"]')
                    if await save_btn.count() > 0:
                        await save_btn.click()
                        await self.human_delay(0.5, 1)
                        results.append({'action': 'update_settings', 'success': True})
        except Exception as e:
            results.append({'action': 'account', 'success': False, 'error': str(e)})
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class TrafficGenerator:
    """Generates realistic browser-based traffic patterns."""
    
    def __init__(self, sessions_per_minute: int = 10):
        self.sessions_per_minute = sessions_per_minute
        self.scenarios = [
            BrowseProductsScenario(),
            SearchProductsScenario(),
            AddToCartScenario(),
            LoginScenario(),
            CheckoutScenario(),
            ViewAccountScenario(),
        ]
        self.total_weight = sum(s.weight for s in self.scenarios)
        self.session_count = 0
        self.error_count = 0
        self.success_count = 0
        self.browser: Optional[Browser] = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
    
    def select_scenario(self) -> BrowserScenario:
        """Select a scenario based on weights."""
        r = random.randint(1, self.total_weight)
        cumulative = 0
        for scenario in self.scenarios:
            cumulative += scenario.weight
            if r <= cumulative:
                return scenario
        return self.scenarios[0]
    
    def select_user(self) -> dict:
        """Select a random user for the session."""
        return get_random_user()
    
    async def run_session(self, context: BrowserContext) -> Dict[str, Any]:
        """Run a single browser session."""
        async with self.semaphore:
            self.session_count += 1
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            user = self.select_user()
            scenario = self.select_scenario()
            
            print(f"[{datetime.now().isoformat()}] Session {session_id}: {user['email']} - {scenario.name}")
            
            page = await context.new_page()
            
            try:
                result = await scenario.execute(page, user)
                result['session_id'] = session_id
                result['timestamp'] = datetime.now().isoformat()
                
                # Check if any actions failed
                failed = any(not a.get('success', True) for a in result.get('actions', []))
                if failed:
                    self.error_count += 1
                else:
                    self.success_count += 1
                
                return result
            except Exception as e:
                self.error_count += 1
                print(f"[{datetime.now().isoformat()}] Session {session_id} error: {e}")
                return {
                    'session_id': session_id,
                    'scenario': scenario.name,
                    'user': user,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            finally:
                await page.close()
    
    async def run_forever(self):
        """Run traffic generation forever."""
        interval = 60.0 / self.sessions_per_minute
        
        print(f"\n{'='*60}")
        print(f"  LaunchDarkly Observability Demo - Browser Traffic Generator")
        print(f"{'='*60}")
        print(f"  Frontend: {FRONTEND_URL}")
        print(f"  Rate: {self.sessions_per_minute} sessions/minute")
        print(f"  Interval: {interval:.2f} seconds between sessions")
        print(f"  Max concurrent browsers: {MAX_CONCURRENT_BROWSERS}")
        print(f"{'='*60}\n")
        
        async with async_playwright() as p:
            # Launch browser
            self.browser = await p.chromium.launch(headless=True)
            
            # Create a persistent context for better session handling
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            try:
                while True:
                    try:
                        await self.run_session(context)
                        
                        # Print stats every 10 sessions
                        if self.session_count % 10 == 0:
                            error_rate = (self.error_count / self.session_count * 100) if self.session_count > 0 else 0
                            print(f"\n[Stats] Sessions: {self.session_count}, "
                                  f"Success: {self.success_count}, "
                                  f"Errors: {self.error_count} ({error_rate:.1f}%)\n")
                        
                        # Wait before next session
                        await asyncio.sleep(interval)
                        
                    except KeyboardInterrupt:
                        print("\n\nShutting down traffic generator...")
                        break
                    except Exception as e:
                        print(f"Error in traffic loop: {e}")
                        await asyncio.sleep(interval)
            finally:
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
