// utils/apiUtils.js
class RequestManager {
  constructor() {
    this.cache = new Map();
    this.pendingRequests = new Map();
    this.rateLimitQueue = [];
  }

  // Cache API responses
  async cachedRequest(key, requestFn, ttl = 60000) { // Default TTL: 1 minute
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < ttl) {
      return cached.data;
    }

    // Check if request is already pending
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key);
    }

    const promise = requestFn().then(data => {
      this.cache.set(key, { data, timestamp: Date.now() });
      this.pendingRequests.delete(key);
      return data;
    }).catch(error => {
      this.pendingRequests.delete(key);
      throw error;
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  // Clear cache for specific key
  clearCache(key) {
    this.cache.delete(key);
  }

  // Clear all cache
  clearAllCache() {
    this.cache.clear();
  }
}

export const requestManager = new RequestManager();