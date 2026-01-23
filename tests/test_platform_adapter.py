"""
Tests for Platform Adapter Module

Run with: pytest tests/test_platform_adapter.py -v
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.platform_adapter import (
    get_platform_config,
    validate_summary_length,
    format_length_error,
    get_character_count,
    PLATFORM_CONFIG,
)
from agent_core.agent_client import get_instructions


class TestPlatformConfig:
    """Tests for platform configuration."""
    
    def test_twitter_config_exists(self):
        """Verify Twitter config is defined."""
        assert "twitter" in PLATFORM_CONFIG
        
    def test_twitter_max_chars(self):
        """Verify Twitter character limit is 280."""
        config = get_platform_config("twitter")
        assert config["max_chars"] == 280
        
    def test_default_config_no_limit(self):
        """Verify default platform has no character limit."""
        config = get_platform_config("default")
        assert config["max_chars"] is None
        
    def test_unsupported_platform_raises(self):
        """Verify unsupported platform raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_platform_config("tiktok")
        assert "Unsupported platform" in str(exc_info.value)


class TestSummaryValidation:
    """Tests for summary length validation."""
    
    def test_twitter_summary_length_valid(self):
        """Verify text ≤280 chars passes validation."""
        text = "A" * 280
        assert validate_summary_length(text, "twitter") is True
        
    def test_twitter_summary_length_invalid(self):
        """Verify text >280 chars fails validation."""
        text = "A" * 281
        assert validate_summary_length(text, "twitter") is False
        
    def test_default_summary_no_limit(self):
        """Verify default platform accepts any length."""
        text = "A" * 10000
        assert validate_summary_length(text, "default") is True
        
    def test_empty_string_valid(self):
        """Verify empty string passes validation."""
        assert validate_summary_length("", "twitter") is True


class TestCharacterCount:
    """Tests for character counting."""
    
    def test_get_character_count(self):
        """Verify character count is accurate."""
        assert get_character_count("hello") == 5
        assert get_character_count("") == 0
        assert get_character_count("🐦") == 1  # Emoji counts as 1


class TestErrorFormatting:
    """Tests for error message formatting."""
    
    def test_format_length_error_excess(self):
        """Verify error message shows correct excess."""
        text = "A" * 290  # 10 chars over
        error = format_length_error(text, "twitter")
        assert "10 characters" in error
        assert "290" in error
        assert "280" in error
        
    def test_format_length_error_no_limit(self):
        """Verify no error for platform without limit."""
        error = format_length_error("any text", "default")
        assert error == ""


class TestGetInstructions:
    """Tests for platform-specific instructions."""
    
    def test_get_instructions_default(self):
        """Verify default instructions for backward compatibility."""
        instructions = get_instructions("default")
        assert "YouTube summarizer" in instructions
        assert "get_transcript_text" in instructions
        
    def test_get_instructions_twitter(self):
        """Verify Twitter-specific instructions."""
        instructions = get_instructions("twitter")
        assert "280" in instructions or "Twitter" in instructions
        assert "hashtag" in instructions.lower()
        
    def test_legacy_function_unchanged(self):
        """
        Verify original summarize_youtube_video still exists.
        This is a regression test per TDD-R requirements.
        """
        from agent_core.agent_client import summarize_youtube_video
        import inspect
        
        # Check function signature hasn't changed
        sig = inspect.signature(summarize_youtube_video)
        params = list(sig.parameters.keys())
        assert params == ["youtube_url"], f"Expected ['youtube_url'], got {params}"
