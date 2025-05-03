import hmac
import hashlib

def generate_signature(payload, secret):
    """
    Generate an HMAC-SHA256 signature for a payload using the provided secret.
    
    Args:
        payload (str): The JSON payload as a string
        secret (str): The secret key
        
    Returns:
        str: The hex digest of the signature
    """
    if not secret:
        return None
    
    # Create an HMAC-SHA256 hash of the payload using the secret key
    return hmac.new(
        key=secret.encode('utf-8'),  # Secret must be encoded to bytes
        msg=payload.encode('utf-8'),  # Payload must be encoded to bytes
        digestmod=hashlib.sha256
    ).hexdigest()  # Return the hexadecimal digest of the signature

def verify_signature(payload, signature, secret):
    """
    Verify that a signature matches the expected signature for a payload.
    
    Args:
        payload (str): The JSON payload as a string
        signature (str): The provided signature to verify
        secret (str): The secret key used to generate the expected signature
        
    Returns:
        bool: True if the signature is valid, False otherwise
    """
    if not secret or not signature:
        return False
    
    # Generate the expected signature from the payload and secret
    expected_signature = generate_signature(payload, secret)
    
    # Use hmac.compare_digest for secure comparison of signatures
    return hmac.compare_digest(signature, expected_signature)
