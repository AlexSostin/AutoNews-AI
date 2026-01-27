"""
Password strength validation utilities
"""
import re


COMMON_PASSWORDS = [
    'password', 'password123', '12345678', '123456789', 'qwerty', 'qwerty123',
    'abc123', 'letmein', 'monkey', '1234567890', 'dragon', 'master',
    'welcome', 'login', 'admin', 'root', 'pass', 'passw0rd',
]


def validate_password_strength(password):
    """
    Validate password strength for security.
    
    Rules:
    - Minimum 8 characters
    - At least one letter (A-Z or a-z)
    - At least one digit (0-9)
    - Not a common password
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for at least one letter
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Please choose a stronger password"
    
    # Check for repeated characters (e.g., "aaaaaaaa")
    if re.search(r'(.)\1{4,}', password):
        return False, "Password contains too many repeated characters"
    
    return True, "Password is strong"


def get_password_requirements():
    """
    Get password requirements for display to users.
    
    Returns:
        list: List of password requirement strings
    """
    return [
        "At least 8 characters long",
        "At least one letter (A-Z or a-z)",
        "At least one number (0-9)",
        "Not a commonly used password",
    ]
