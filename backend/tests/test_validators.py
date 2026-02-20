"""
Group 1: Password validator tests — pure logic, no DB needed.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from news.validators import validate_password_strength, get_password_requirements


class TestValidatePasswordStrength:
    """Tests for validate_password_strength"""

    def test_short_password(self):
        """Passwords under 8 chars are rejected"""
        valid, msg = validate_password_strength("Ab1")
        assert valid is False
        assert "8 characters" in msg

    def test_no_letter(self):
        """Numeric-only passwords are rejected"""
        valid, msg = validate_password_strength("12345678")
        assert valid is False
        assert "letter" in msg

    def test_no_digit(self):
        """Letter-only passwords are rejected"""
        valid, msg = validate_password_strength("abcdefgh")
        assert valid is False
        assert "number" in msg

    def test_common_password(self):
        """Common passwords are rejected"""
        valid, msg = validate_password_strength("password123")
        assert valid is False
        assert "common" in msg.lower()

    def test_repeated_chars(self):
        """Passwords with 5+ repeated chars are rejected"""
        valid, msg = validate_password_strength("aaaaaa1x")
        assert valid is False
        assert "repeated" in msg.lower()

    def test_valid_password(self):
        """A strong password passes all checks"""
        valid, msg = validate_password_strength("MyStr0ngP@ss")
        assert valid is True

    def test_edge_exactly_8_chars(self):
        """Exactly 8 chars with letter+digit passes"""
        valid, _ = validate_password_strength("Abcdefg1")
        assert valid is True


class TestGetPasswordRequirements:
    """Tests for get_password_requirements"""

    def test_returns_list(self):
        """Should return a list of strings"""
        reqs = get_password_requirements()
        assert isinstance(reqs, list)
        assert len(reqs) >= 3

    def test_mentions_length(self):
        """Should mention minimum length"""
        reqs = get_password_requirements()
        assert any("8" in r for r in reqs)
