import { useState, useEffect, useCallback, useRef } from 'react';
import { api, getRandomUser, getRandomProduct, getRandomCart } from '../services/api';

// Import LaunchDarkly Observability
let LDObserve = null;
try {
  const ldModule = await import('@launchdarkly/observability');
  LDObserve = ldModule.default || ldModule.LDObserve;
} catch (e) {
  console.warn('LaunchDarkly Observability not available');
}

// Traffic scenarios with weights
const SCENARIOS = [
  { 
    id: 'browse_products', 
    name: 'Browse Products', 
    weight: 35,
    execute: async (user) => {
      const span = LDObserve?.startSpan?.('frontend.browse.products');
      try {
        span?.setAttribute?.('user.email', user.email);
        span?.setAttribute?.('source', 'frontend');
        
        await api.listProducts();
        
        // View 1-3 products
        const viewCount = Math.floor(Math.random() * 3) + 1;
        for (let i = 0; i < viewCount; i++) {
          const product = getRandomProduct();
          await api.getProduct(product.id);
          await sleep(500 + Math.random() * 1500);
        }
        
        return { success: true, action: 'browse_products', viewCount };
      } finally {
        span?.end?.();
      }
    }
  },
  { 
    id: 'user_login', 
    name: 'User Login', 
    weight: 20,
    execute: async (user) => {
      const span = LDObserve?.startSpan?.('frontend.auth.login');
      try {
        span?.setAttribute?.('user.email', user.email);
        span?.setAttribute?.('source', 'frontend');
        
        await api.login(user);
        await api.getUser(user.key);
        
        return { success: true, action: 'user_login' };
      } finally {
        span?.end?.();
      }
    }
  },
  { 
    id: 'checkout_flow', 
    name: 'Checkout Flow', 
    weight: 15,
    execute: async (user) => {
      const span = LDObserve?.startSpan?.('frontend.checkout.complete');
      try {
        span?.setAttribute?.('user.email', user.email);
        span?.setAttribute?.('source', 'frontend');
        
        // Browse first
        await api.listProducts();
        await sleep(1000);
        
        // Checkout
        const cart = getRandomCart();
        span?.setAttribute?.('cart.items', cart.length);
        
        const result = await api.checkout(user, cart);
        
        span?.setAttribute?.('checkout.success', result.success);
        
        return { success: result.success, action: 'checkout_flow', items: cart.length };
      } finally {
        span?.end?.();
      }
    }
  },
  { 
    id: 'search_products', 
    name: 'Search Products', 
    weight: 15,
    execute: async (user) => {
      const queries = ['feature flags', 'rollout', 'testing', 'targeting', 'sdk'];
      const query = queries[Math.floor(Math.random() * queries.length)];
      
      const span = LDObserve?.startSpan?.('frontend.search.query');
      try {
        span?.setAttribute?.('search.query', query);
        span?.setAttribute?.('source', 'frontend');
        
        await api.search(query);
        
        // Maybe view a product
        if (Math.random() > 0.5) {
          await sleep(500);
          const product = getRandomProduct();
          await api.getProduct(product.id);
        }
        
        return { success: true, action: 'search_products', query };
      } finally {
        span?.end?.();
      }
    }
  },
  { 
    id: 'update_profile', 
    name: 'Update Profile', 
    weight: 10,
    execute: async (user) => {
      const span = LDObserve?.startSpan?.('frontend.profile.update');
      try {
        span?.setAttribute?.('user.email', user.email);
        span?.setAttribute?.('source', 'frontend');
        
        await api.getUser(user.key);
        await sleep(1000);
        
        await api.updateUser(user.key, {
          preferences: {
            theme: Math.random() > 0.5 ? 'dark' : 'light',
            notifications: Math.random() > 0.3,
          }
        });
        
        return { success: true, action: 'update_profile' };
      } finally {
        span?.end?.();
      }
    }
  },
  { 
    id: 'view_dashboard', 
    name: 'View Dashboard', 
    weight: 5,
    execute: async (user) => {
      const span = LDObserve?.startSpan?.('frontend.dashboard.view');
      try {
        span?.setAttribute?.('source', 'frontend');
        
        await api.dashboard();
        
        return { success: true, action: 'view_dashboard' };
      } finally {
        span?.end?.();
      }
    }
  },
];

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function selectScenario(scenarios) {
  const totalWeight = scenarios.reduce((sum, s) => sum + s.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (const scenario of scenarios) {
    random -= scenario.weight;
    if (random <= 0) {
      return scenario;
    }
  }
  
  return scenarios[0];
}

export function useAutoPlay(intervalMs = 2000) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [rate, setRate] = useState(30); // requests per minute
  const [currentAction, setCurrentAction] = useState(null);
  const [stats, setStats] = useState({ sessions: 0, success: 0, errors: 0 });
  const [activities, setActivities] = useState([]);
  
  const intervalRef = useRef(null);

  const runScenario = useCallback(async () => {
    const user = getRandomUser();
    const scenario = selectScenario(SCENARIOS);
    
    setCurrentAction({ scenario: scenario.name, user });
    
    try {
      const result = await scenario.execute(user);
      
      setStats(prev => ({
        sessions: prev.sessions + 1,
        success: result.success ? prev.success + 1 : prev.success,
        errors: result.success ? prev.errors : prev.errors + 1,
      }));
      
      // Add to activity feed
      setActivities(prev => [{
        id: Date.now(),
        type: result.success ? 'success' : 'error',
        title: scenario.name,
        meta: `${user.email} - just now`,
        icon: result.success ? 'check' : 'x',
      }, ...prev.slice(0, 19)]);
      
    } catch (error) {
      console.error('Scenario error:', error);
      
      setStats(prev => ({
        ...prev,
        sessions: prev.sessions + 1,
        errors: prev.errors + 1,
      }));
      
      setActivities(prev => [{
        id: Date.now(),
        type: 'error',
        title: `${scenario.name} failed`,
        meta: `${user.email} - just now`,
        icon: 'x',
      }, ...prev.slice(0, 19)]);
    }
    
    setCurrentAction(null);
  }, []);

  const start = useCallback(() => {
    if (intervalRef.current) return;
    
    setIsPlaying(true);
    
    // Run immediately
    runScenario();
    
    // Then run on interval
    const intervalTime = (60 / rate) * 1000;
    intervalRef.current = setInterval(runScenario, intervalTime);
  }, [rate, runScenario]);

  const stop = useCallback(() => {
    setIsPlaying(false);
    setCurrentAction(null);
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const toggle = useCallback(() => {
    if (isPlaying) {
      stop();
    } else {
      start();
    }
  }, [isPlaying, start, stop]);

  // Update interval when rate changes
  useEffect(() => {
    if (isPlaying && intervalRef.current) {
      clearInterval(intervalRef.current);
      const intervalTime = (60 / rate) * 1000;
      intervalRef.current = setInterval(runScenario, intervalTime);
    }
  }, [rate, isPlaying, runScenario]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    isPlaying,
    rate,
    setRate,
    currentAction,
    stats,
    activities,
    toggle,
    start,
    stop,
  };
}

export default useAutoPlay;
