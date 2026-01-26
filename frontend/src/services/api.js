/**
 * API service with trace context propagation for LaunchDarkly Observability.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// User personas with LaunchDarkly pun emails
const USER_PERSONAS = [
  { key: 'usr_001', name: 'Luna Darksworth', email: 'luna@staylightly.io' },
  { key: 'usr_002', name: 'Lance Dimly', email: 'lance@darklaunchly.com' },
  { key: 'usr_003', name: 'Darcy Launch', email: 'darcy@lunchdarkly.net' },
  { key: 'usr_004', name: 'Larry Duskman', email: 'larry@launchdorkly.io' },
  { key: 'usr_005', name: 'Lydia Twilight', email: 'lydia@dimlylaunch.com' },
  { key: 'usr_006', name: 'Drake Moonson', email: 'drake@launchbrightly.io' },
  { key: 'usr_007', name: 'Dawn Flagworth', email: 'dawn@toggledarkly.com' },
  { key: 'usr_008', name: 'Felix Feature', email: 'felix@flaglaunchly.io' },
  { key: 'usr_009', name: 'Sage Rollout', email: 'sage@rolldarkly.net' },
  { key: 'usr_010', name: 'Nova Experiment', email: 'nova@launchsoftly.io' },
];

// Sample products
const PRODUCTS = [
  { id: 'prod_001', name: 'Feature Flag Starter Kit', price: 29.99 },
  { id: 'prod_002', name: 'Progressive Rollout Pro', price: 49.99 },
  { id: 'prod_003', name: 'A/B Testing Suite', price: 79.99 },
  { id: 'prod_004', name: 'Targeting Rules Package', price: 39.99 },
  { id: 'prod_005', name: 'Segment Builder', price: 59.99 },
];

/**
 * Get a random user persona.
 */
export function getRandomUser() {
  return USER_PERSONAS[Math.floor(Math.random() * USER_PERSONAS.length)];
}

/**
 * Get a random product.
 */
export function getRandomProduct() {
  return PRODUCTS[Math.floor(Math.random() * PRODUCTS.length)];
}

/**
 * Generate a random cart.
 */
export function getRandomCart() {
  const count = Math.floor(Math.random() * 3) + 1;
  const items = [];
  for (let i = 0; i < count; i++) {
    items.push({
      ...getRandomProduct(),
      quantity: Math.floor(Math.random() * 3) + 1,
    });
  }
  return items;
}

/**
 * Make an API request with error handling.
 */
async function request(path, options = {}) {
  const url = `${API_URL}${path}`;
  
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();
    
    return {
      success: response.ok,
      status: response.status,
      data,
    };
  } catch (error) {
    return {
      success: false,
      status: 0,
      error: error.message,
    };
  }
}

/**
 * API methods.
 */
export const api = {
  // Health check
  health: () => request('/api/health'),
  
  // Dashboard
  dashboard: () => request('/api/dashboard'),
  
  // Authentication
  login: (user) => request('/api/login', {
    method: 'POST',
    body: JSON.stringify({ user: user || getRandomUser() }),
  }),
  
  // Users
  getUser: (userId) => request(`/api/users/${userId}`),
  updateUser: (userId, data) => request(`/api/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  
  // Products
  listProducts: () => request('/api/products'),
  getProduct: (productId) => request(`/api/products/${productId}`),
  
  // Search
  search: (query) => request('/api/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  }),
  
  // Checkout
  checkout: (user, items) => request('/api/checkout', {
    method: 'POST',
    body: JSON.stringify({ 
      user: user || getRandomUser(),
      items: items || getRandomCart(),
    }),
  }),
  
  // Orders
  listOrders: () => request('/api/orders'),
};

export default api;
