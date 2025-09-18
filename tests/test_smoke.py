"""
Simple smoke tests to validate the test suite setup
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestTestSuite:
    """Basic tests to ensure the test suite is working"""
    
    def test_pytest_working(self):
        """Test that pytest is working correctly"""
        assert True
    
    def test_imports_working(self):
        """Test that imports are working correctly"""
        try:
            import src.github_operations
            import main
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
    
    def test_environment_variables_accessible(self, monkeypatch):
        """Test that environment variables can be set and accessed"""
        test_value = "test_value_123"
        monkeypatch.setenv("TEST_VAR", test_value)
        assert os.getenv("TEST_VAR") == test_value
    
    def test_fixtures_working(self, mock_github_token, mock_repository_name):
        """Test that fixtures are working correctly"""
        assert mock_github_token == "ghp_test_token_1234567890abcdef"
        assert mock_repository_name == "testuser/testrepo"
    
    def test_mock_github_issue_fixture(self, mock_github_issue):
        """Test that GitHub issue mock fixture works"""
        assert mock_github_issue.number == 123
        assert mock_github_issue.title == "Test Issue"
        assert "github.com" in mock_github_issue.html_url
    
    @pytest.mark.unit
    def test_unit_test_marker(self):
        """Test that unit test marker works"""
        assert True
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test marker test")
    def test_integration_test_marker(self):
        """Test that integration test marker works"""
        assert True
    
    def test_string_operations(self):
        """Simple test to verify basic Python functionality"""
        test_string = "Speculum Principum"
        assert test_string.lower() == "speculum principum"
        assert len(test_string) > 0
        assert "Speculum" in test_string
    
    def test_list_operations(self):
        """Simple test for list operations"""
        test_list = ["bug", "enhancement", "question"]
        assert len(test_list) == 3
        assert "bug" in test_list
        assert test_list[0] == "bug"
    
    def test_dict_operations(self):
        """Simple test for dictionary operations"""
        test_dict = {
            "title": "Test Issue",
            "labels": ["bug", "urgent"],
            "assignees": ["user1"]
        }
        assert test_dict["title"] == "Test Issue"
        assert len(test_dict["labels"]) == 2
        assert "bug" in test_dict["labels"]