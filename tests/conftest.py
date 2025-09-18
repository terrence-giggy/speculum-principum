"""
Test fixtures and mock data for Speculum Principum tests
"""

import pytest
from unittest.mock import Mock, MagicMock
from github import Github
from github.Repository import Repository
from github.Issue import Issue


@pytest.fixture
def mock_github_token():
    """Mock GitHub token for testing"""
    return "ghp_test_token_1234567890abcdef"


@pytest.fixture
def mock_repository_name():
    """Mock repository name for testing"""
    return "testuser/testrepo"


@pytest.fixture
def mock_issue_data():
    """Mock issue data for testing"""
    return {
        "title": "Test Issue",
        "body": "This is a test issue description",
        "labels": ["bug", "urgent"],
        "assignees": ["testuser1", "testuser2"]
    }


@pytest.fixture
def mock_github_issue():
    """Mock GitHub Issue object"""
    issue = Mock(spec=Issue)
    issue.number = 123
    issue.title = "Test Issue"
    issue.body = "This is a test issue description"
    issue.html_url = "https://github.com/testuser/testrepo/issues/123"
    issue.state = "open"
    issue.labels = [Mock(name="bug"), Mock(name="urgent")]
    issue.assignees = [Mock(login="testuser1"), Mock(login="testuser2")]
    return issue


@pytest.fixture
def mock_github_label():
    """Mock GitHub Label object"""
    label = Mock()
    label.name = "bug"
    return label


@pytest.fixture
def mock_github_repository():
    """Mock GitHub Repository object"""
    repo = Mock(spec=Repository)
    repo.name = "testrepo"
    repo.full_name = "testuser/testrepo"
    repo.description = "Test repository for Speculum Principum"
    repo.html_url = "https://github.com/testuser/testrepo"
    repo.open_issues_count = 5
    
    # Mock methods
    repo.create_issue = Mock()
    repo.get_labels = Mock()
    repo.get_issues = Mock()
    
    return repo


@pytest.fixture
def mock_github_client():
    """Mock GitHub client"""
    github = Mock(spec=Github)
    github.get_repo = Mock()
    return github


@pytest.fixture
def sample_repo_info():
    """Sample repository information"""
    return {
        'name': 'testrepo',
        'full_name': 'testuser/testrepo',
        'description': 'Test repository for Speculum Principum',
        'url': 'https://github.com/testuser/testrepo',
        'issues_count': 5
    }


@pytest.fixture
def environment_variables(monkeypatch, mock_github_token, mock_repository_name):
    """Set up environment variables for testing"""
    monkeypatch.setenv("GITHUB_TOKEN", mock_github_token)
    monkeypatch.setenv("GITHUB_REPOSITORY", mock_repository_name)


@pytest.fixture
def mock_labels_list():
    """Mock list of repository labels"""
    labels = []
    for label_name in ["bug", "urgent", "enhancement", "question"]:
        label = Mock()
        label.name = label_name
        labels.append(label)
    return labels


@pytest.fixture
def cli_args_create_issue():
    """Mock CLI arguments for create-issue operation"""
    return [
        "create-issue",
        "--title", "Test Issue from CLI",
        "--body", "This is a test issue created from CLI",
        "--labels", "bug", "urgent",
        "--assignees", "testuser1", "testuser2"
    ]


@pytest.fixture
def cli_args_minimal():
    """Mock minimal CLI arguments for create-issue operation"""
    return [
        "create-issue",
        "--title", "Minimal Test Issue"
    ]


class MockGitHubException(Exception):
    """Mock GitHub exception for testing error handling"""
    def __init__(self, message="Mock GitHub API error", data=None):
        super().__init__(message)
        self.data = data or {"message": message}


@pytest.fixture
def mock_github_exception():
    """Mock GitHub exception"""
    return MockGitHubException("API rate limit exceeded", {"message": "API rate limit exceeded"})


@pytest.fixture
def mock_issue_creation_response(mock_github_issue):
    """Mock successful issue creation response"""
    return mock_github_issue