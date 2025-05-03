import json
import redis
from functools import wraps
from flask import current_app

# Initialize Redis connection
redis_client = None

def get_redis():
    """Return the Redis client, initializing it if necessary."""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis.from_url(current_app.config['REDIS_URL'])
    return redis_client

def cache_subscription(subscription_id, subscription_data, timeout=None):
    """
    Cache subscription data in Redis.
    
    Args:
        subscription_id (str): The unique identifier of the subscription.
        subscription_data (dict): The subscription data to cache.
        timeout (int, optional): The time-to-live (TTL) for the cache in seconds.
    """
    if timeout is None:
        timeout = current_app.config['SUBSCRIPTION_CACHE_TIMEOUT']
    
    redis_key = f"subscription:{subscription_id}"
    get_redis().setex(
        redis_key,
        timeout,
        json.dumps(subscription_data)  # Serialize data as JSON
    )

def get_cached_subscription(subscription_id):
    """
    Get subscription data from Redis cache.
    
    Args:
        subscription_id (str): The unique identifier of the subscription.
    
    Returns:
        dict or None: The cached subscription data or None if not found.
    """
    redis_key = f"subscription:{subscription_id}"
    data = get_redis().get(redis_key)
    
    if data:
        return json.loads(data)  # Deserialize JSON back to Python object
    return None

def invalidate_subscription_cache(subscription_id):
    """
    Remove subscription data from the Redis cache.
    
    Args:
        subscription_id (str): The unique identifier of the subscription.
    """
    redis_key = f"subscription:{subscription_id}"
    get_redis().delete(redis_key)

def cached(key_prefix, timeout=None):
    """
    Cache function results using Redis.
    
    Args:
        key_prefix (str): The prefix used to generate a unique cache key.
        timeout (int, optional): The TTL for the cache in seconds.
        
    Returns:
        function: The decorator function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate a unique cache key based on the function arguments
            key_parts = [key_prefix]
            for arg in args:
                key_parts.append(str(arg))
            for k, v in kwargs.items():
                key_parts.append(f"{k}:{v}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get the result from the cache
            cached_result = get_redis().get(cache_key)
            if cached_result:
                return json.loads(cached_result)  # Return the cached result
            
            # Call the original function if not cached
            result = f(*args, **kwargs)
            
            # Cache the result
            cache_timeout = timeout or current_app.config['CACHE_DEFAULT_TIMEOUT']
            get_redis().setex(cache_key, cache_timeout, json.dumps(result))  # Serialize result as JSON
            
            return result
        return decorated_function
    return decorator
