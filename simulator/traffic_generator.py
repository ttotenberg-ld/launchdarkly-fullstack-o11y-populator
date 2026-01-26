"""
Traffic Generator - Generates realistic traffic patterns for LaunchDarkly observability demo.
Runs perpetually to populate demo environment with varied observability data.
"""

import os
import sys
import time
import random
import asyncio
import aiohttp
import uuid
from datetime import datetime
from typing import List, Dict, Any

# Add backend directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from shared.users import USER_PERSONAS, get_random_user
from shared.service_names import get_all_service_names

# Configuration
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', 'http://localhost:5000')
REQUESTS_PER_MINUTE = int(os.getenv('REQUESTS_PER_MINUTE', '30'))
ERROR_SESSION_RATE = float(os.getenv('ERROR_SESSION_RATE', '0.15'))  # 15% of sessions have errors


class TrafficScenario:
    """Base class for traffic scenarios."""
    
    def __init__(self, name: str, weight: int, error_prone: bool = False):
        self.name = name
        self.weight = weight
        self.error_prone = error_prone
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        raise NotImplementedError


class BrowseProductsScenario(TrafficScenario):
    """User browses products."""
    
    def __init__(self):
        super().__init__("browse_products", weight=35, error_prone=False)
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        results = []
        
        # List products
        async with session.get(f"{API_GATEWAY_URL}/api/products") as resp:
            results.append({
                'action': 'list_products',
                'status': resp.status,
                'success': resp.status == 200
            })
        
        # View 1-3 random products
        for _ in range(random.randint(1, 3)):
            product_id = f"prod_00{random.randint(1, 8)}"
            async with session.get(f"{API_GATEWAY_URL}/api/products/{product_id}") as resp:
                results.append({
                    'action': 'view_product',
                    'product_id': product_id,
                    'status': resp.status
                })
            await asyncio.sleep(random.uniform(0.5, 2.0))  # Simulate browsing time
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class UserLoginScenario(TrafficScenario):
    """User logs in and views profile."""
    
    def __init__(self):
        super().__init__("user_login", weight=20, error_prone=True)
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        results = []
        
        # Login
        async with session.post(f"{API_GATEWAY_URL}/api/login", json={'user': user}) as resp:
            results.append({
                'action': 'login',
                'status': resp.status,
                'success': resp.status == 200
            })
        
        # View profile
        async with session.get(f"{API_GATEWAY_URL}/api/users/{user['key']}") as resp:
            results.append({
                'action': 'view_profile',
                'status': resp.status
            })
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class CheckoutFlowScenario(TrafficScenario):
    """User goes through checkout flow - the most complex trace chain."""
    
    def __init__(self):
        super().__init__("checkout_flow", weight=15, error_prone=True)
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        results = []
        
        # Browse some products first
        async with session.get(f"{API_GATEWAY_URL}/api/products") as resp:
            results.append({'action': 'browse_products', 'status': resp.status})
        
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Create cart with random items
        cart_items = [
            {'id': f"prod_00{random.randint(1, 8)}", 'quantity': random.randint(1, 3)}
            for _ in range(random.randint(1, 4))
        ]
        
        # Checkout - this triggers the full trace chain
        async with session.post(f"{API_GATEWAY_URL}/api/checkout", json={
            'user': user,
            'items': cart_items,
        }) as resp:
            results.append({
                'action': 'checkout',
                'status': resp.status,
                'success': resp.status == 200,
                'items': len(cart_items)
            })
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class SearchProductsScenario(TrafficScenario):
    """User searches for products."""
    
    def __init__(self):
        super().__init__("search_products", weight=15, error_prone=False)
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        results = []
        
        queries = [
            'feature flags', 'rollout', 'testing', 'targeting', 
            'sdk', 'experiment', 'segment', 'release'
        ]
        query = random.choice(queries)
        
        async with session.post(f"{API_GATEWAY_URL}/api/search", json={'query': query}) as resp:
            results.append({
                'action': 'search',
                'query': query,
                'status': resp.status
            })
        
        # Maybe view a product from search results
        if random.random() > 0.5:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            product_id = f"prod_00{random.randint(1, 8)}"
            async with session.get(f"{API_GATEWAY_URL}/api/products/{product_id}") as resp:
                results.append({
                    'action': 'view_product',
                    'product_id': product_id,
                    'status': resp.status
                })
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class UpdateProfileScenario(TrafficScenario):
    """User updates their profile."""
    
    def __init__(self):
        super().__init__("update_profile", weight=10, error_prone=False)
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        results = []
        
        # View current profile
        async with session.get(f"{API_GATEWAY_URL}/api/users/{user['key']}") as resp:
            results.append({
                'action': 'view_profile',
                'status': resp.status
            })
        
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Update profile
        updates = {
            'preferences': {
                'theme': random.choice(['light', 'dark', 'auto']),
                'notifications': random.choice([True, False]),
                'language': random.choice(['en', 'es', 'fr', 'de']),
            }
        }
        
        async with session.put(f"{API_GATEWAY_URL}/api/users/{user['key']}", json=updates) as resp:
            results.append({
                'action': 'update_profile',
                'status': resp.status,
                'success': resp.status == 200
            })
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class ViewDashboardScenario(TrafficScenario):
    """User views dashboard."""
    
    def __init__(self):
        super().__init__("view_dashboard", weight=5, error_prone=False)
    
    async def execute(self, session: aiohttp.ClientSession, user: dict) -> Dict[str, Any]:
        results = []
        
        async with session.get(f"{API_GATEWAY_URL}/api/dashboard") as resp:
            results.append({
                'action': 'view_dashboard',
                'status': resp.status
            })
        
        return {'scenario': self.name, 'user': user, 'actions': results}


class TrafficGenerator:
    """Generates realistic traffic patterns."""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.scenarios = [
            BrowseProductsScenario(),
            UserLoginScenario(),
            CheckoutFlowScenario(),
            SearchProductsScenario(),
            UpdateProfileScenario(),
            ViewDashboardScenario(),
        ]
        self.total_weight = sum(s.weight for s in self.scenarios)
        self.session_count = 0
        self.error_count = 0
        self.success_count = 0
    
    def select_scenario(self) -> TrafficScenario:
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
    
    async def run_session(self) -> Dict[str, Any]:
        """Run a single user session."""
        self.session_count += 1
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        user = self.select_user()
        scenario = self.select_scenario()
        
        # Determine if this session should have errors
        force_errors = random.random() < ERROR_SESSION_RATE
        
        print(f"[{datetime.now().isoformat()}] Session {session_id}: {user['email']} - {scenario.name}"
              + (" (error session)" if force_errors else ""))
        
        try:
            async with aiohttp.ClientSession() as session:
                result = await scenario.execute(session, user)
                result['session_id'] = session_id
                result['timestamp'] = datetime.now().isoformat()
                
                # Check if any actions failed
                failed = any(a.get('status', 200) >= 400 for a in result.get('actions', []))
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
    
    async def run_forever(self):
        """Run traffic generation forever."""
        interval = 60.0 / self.requests_per_minute
        
        print(f"\n{'='*60}")
        print(f"  LaunchDarkly Observability Demo - Traffic Generator")
        print(f"{'='*60}")
        print(f"  Target: {API_GATEWAY_URL}")
        print(f"  Rate: {self.requests_per_minute} requests/minute")
        print(f"  Interval: {interval:.2f} seconds between requests")
        print(f"  Error session rate: {ERROR_SESSION_RATE*100:.0f}%")
        print(f"{'='*60}\n")
        
        while True:
            try:
                await self.run_session()
                
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
    
    def run(self):
        """Start the traffic generator."""
        asyncio.run(self.run_forever())


def main():
    """Main entry point."""
    generator = TrafficGenerator(requests_per_minute=REQUESTS_PER_MINUTE)
    generator.run()


if __name__ == '__main__':
    main()
