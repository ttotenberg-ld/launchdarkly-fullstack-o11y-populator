/**
 * API service with trace context propagation for LaunchDarkly Observability.
 */

import { faker } from '@faker-js/faker';

// Use VITE_API_URL if set, otherwise use empty string for relative URLs
// (nginx will proxy /api/* to the api-gateway)
const API_URL = import.meta.env.VITE_API_URL ?? '';

const PLANS = ['free', 'silver', 'gold', 'platinum', 'diamond'];
const ROLES = ['reader', 'writer', 'admin'];
const METROS = ['New York', 'Chicago', 'Minneapolis', 'Atlanta', 'Los Angeles', 'San Francisco', 'Denver', 'Boston'];

/**
 * Generate a UUID v4.  crypto.randomUUID() requires a secure context
 * (HTTPS / localhost).  The Playwright simulator hits the frontend over
 * plain HTTP inside Docker, so we fall back to crypto.getRandomValues().
 */
function uuid() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // RFC-4122 v4 UUID via getRandomValues (works in all contexts)
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

let _currentUser = null;

// Sample products
const PRODUCTS = [
  { id: 'prod_001', name: 'Feature Flag Starter Kit', price: 29.99 },
  { id: 'prod_002', name: 'Progressive Rollout Pro', price: 49.99 },
  { id: 'prod_003', name: 'A/B Testing Suite', price: 79.99 },
  { id: 'prod_004', name: 'Targeting Rules Package', price: 39.99 },
  { id: 'prod_005', name: 'Segment Builder', price: 59.99 },
];

/**
 * Generate a fresh random user with faker and store as the current user
 * so downstream requests can attach their context as headers.
 */
export function getRandomUser() {
  const user = {
    key: `usr-${uuid()}`,
    name: faker.person.fullName(),
    email: faker.internet.email(),
    plan: faker.helpers.arrayElement(PLANS),
    role: faker.helpers.arrayElement(ROLES),
    metro: faker.helpers.arrayElement(METROS),
    country: faker.location.countryCode(),
  };
  _currentUser = user;
  return user;
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
 * Attaches the current user's context as X-User-* headers so backend
 * services can build rich LD multi-contexts without parsing the body.
 */
async function request(path, options = {}) {
  const url = `${API_URL}${path}`;

  const userHeaders = {};
  const user = _currentUser ?? getRandomUser();
  if (user) {
    userHeaders['X-User-Key'] = user.key;
    userHeaders['X-User-Name'] = user.name;
    userHeaders['X-User-Email'] = user.email;
    if (user.plan) userHeaders['X-User-Plan'] = user.plan;
    if (user.role) userHeaders['X-User-Role'] = user.role;
    if (user.metro) userHeaders['X-User-Metro'] = user.metro;
    if (user.country) userHeaders['X-User-Country'] = user.country;
  }

  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...userHeaders,
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
