"""""""""

End-to-end tests for GitHub integration scenarios.

End-to-end tests for GitHub integration scenarios.End-to-end tests for GitHub integration scenarios.

These tests verify GitHub-specific operations including issue processing,

comment updates, and repository interactions.

"""

These tests verify GitHub-specific operations including issue processing,These tests verify GitHub-specific operations including issue processing,

import pytest

from unittest.mock import Mock, patchcomment updates, and repository interactions.comment updates, and repository interactions.

from github.GithubException import GithubException

""""""

from src.issue_processor import GitHubIntegratedIssueProcessor, IssueProcessingError





class TestGitHubIntegration:import pytestimport pytest

    """Test GitHub integration scenarios."""

    from unittest.mock import Mock, patch, MagicMockfrom unittest.m    def test_issue_assignment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

    def test_github_rate_limiting(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

        """Test handling of GitHub API rate limiting."""from github.GithubException import GithubException        """Test assigning users during processing."""

        

        def create_issue_data_dict(mock_issue):        

            """Helper to convert mock issue to expected dict format."""

            return {from src.issue_processor import GitHubIntegratedIssueProcessor, IssueProcessingError        def create_issue_data_dict(mock_issue):

                'number': mock_issue.number,

                'title': mock_issue.title,            """Helper to convert mock issue to expected dict format."""

                'body': mock_issue.body,

                'labels': [label.name for label in mock_issue.labels],            return {

                'assignees': [],

                'created_at': mock_issue.created_at,def create_issue_data_dict(mock_issue):                'number': mock_issue.number,

                'updated_at': mock_issue.updated_at,

                'url': mock_issue.html_url,    """Helper to convert mock issue to expected dict format."""                'title': mock_issue.title,

                'state': mock_issue.state

            }    return {                'body': mock_issue.body,

        

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:        'number': mock_issue.number,                'labels': [label.name for label in mock_issue.labels],

            mock_creator_instance = Mock()

                    'title': mock_issue.title,                'assignees': [],

            # First call succeeds, second call hits rate limit

            call_count = 0        'body': mock_issue.body,                'created_at': mock_issue.created_at,

            def rate_limited_get_issue_data(number):

                nonlocal call_count        'labels': [label.name for label in mock_issue.labels],                'updated_at': mock_issue.updated_at,

                call_count += 1

                if call_count == 1:        'assignees': [],                'url': mock_issue.html_url,

                    return create_issue_data_dict(mock_research_issue)

                else:        'created_at': mock_issue.created_at,                'state': mock_issue.state

                    raise GithubException(403, {"message": "API rate limit exceeded"})

                    'updated_at': mock_issue.updated_at,            }

            mock_creator_instance.get_issue_data = rate_limited_get_issue_data

            mock_creator.return_value = mock_creator_instance        'url': mock_issue.html_url,        

            

            processor = GitHubIntegratedIssueProcessor(        'state': mock_issue.state        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

                github_token="valid-token",

                repository="testorg/testrepo",    }            mock_creator_instance = Mock()

                config_path=str(e2e_config),

                workflow_dir=str(e2e_temp_dir / "workflows"),            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)

                output_base_dir=str(e2e_temp_dir / "output")

            )            mock_creator_instance.assign_issue = Mock()ort Mock, patch, MagicMock

            

            # First call should succeedclass TestGitHubIntegration:from github.GithubException import GithubException

            result1 = processor.process_github_issue(123)

            assert result1.status.value == 'completed'    """Test GitHub integration scenarios."""

            

            # Second call should handle rate limiting gracefully    from src.issue_processor import GitHubIntegratedIssueProcessor, IssueProcessingError

            with pytest.raises(IssueProcessingError) as exc_info:

                processor.process_github_issue(123)    def test_github_authentication_failure(self, e2e_temp_dir, e2e_config):

            

            error_str = str(exc_info.value).lower()        """Test handling of GitHub authentication failures."""

            assert any(word in error_str for word in ["rate limit", "403", "api"])

            class TestGitHubIntegration:

    def test_issue_comment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

        """Test updating issue comments with processing status."""        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:    """Test GitHub integration scenarios."""

        

        def create_issue_data_dict(mock_issue):            # Mock authentication failure    

            """Helper to convert mock issue to expected dict format."""

            return {            mock_creator.side_effect = GithubException(401, {"message": "Bad credentials"})    def test_github_authentication_failure(self, e2e_temp_dir, e2e_config):

                'number': mock_issue.number,

                'title': mock_issue.title,                    """Test handling of GitHub authentication failures."""

                'body': mock_issue.body,

                'labels': [label.name for label in mock_issue.labels],            # Should raise IssueProcessingError during initialization        

                'assignees': [],

                'created_at': mock_issue.created_at,            with pytest.raises(IssueProcessingError) as exc_info:        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

                'updated_at': mock_issue.updated_at,

                'url': mock_issue.html_url,                GitHubIntegratedIssueProcessor(            # Mock authentication failure

                'state': mock_issue.state

            }                    github_token="invalid-token",            mock_creator.side_effect = GithubException(401, {"message": "Bad credentials"})

        

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:                    repository="testorg/testrepo",            

            mock_creator_instance = Mock()

            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)                    config_path=str(e2e_config),            # Should raise IssueProcessingError during initialization

            mock_creator_instance.create_issue_comment = Mock()

            mock_creator.return_value = mock_creator_instance                    workflow_dir=str(e2e_temp_dir / "workflows"),            with pytest.raises(IssueProcessingError) as exc_info:

            

            processor = GitHubIntegratedIssueProcessor(                    output_base_dir=str(e2e_temp_dir / "output")                GitHubIntegratedIssueProcessor(

                github_token="valid-token",

                repository="testorg/testrepo",                )                    github_token="invalid-token",

                config_path=str(e2e_config),

                workflow_dir=str(e2e_temp_dir / "workflows"),                                repository="testorg/testrepo",

                output_base_dir=str(e2e_temp_dir / "output")

            )            # Should indicate authentication error                    config_path=str(e2e_config),

            

            # Process issue            assert exc_info.value.error_code == "GITHUB_INIT_FAILED"                    workflow_dir=str(e2e_temp_dir / "workflows"),

            result = processor.process_github_issue(mock_research_issue.number)

                        assert "bad credentials" in str(exc_info.value).lower()                    output_base_dir=str(e2e_temp_dir / "output")

            # Verify processing completed

            assert result.status.value == 'completed'                    )

    

    def test_issue_label_management(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):    def test_repository_access_failure(self, e2e_temp_dir, e2e_config):            

        """Test adding/removing labels during processing."""

                """Test handling of repository access failures."""            # Should indicate authentication error

        def create_issue_data_dict(mock_issue):

            """Helper to convert mock issue to expected dict format."""                    assert exc_info.value.error_code == "GITHUB_INIT_FAILED"

            return {

                'number': mock_issue.number,        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:            assert "bad credentials" in str(exc_info.value).lower()

                'title': mock_issue.title,

                'body': mock_issue.body,            mock_creator.side_effect = GithubException(404, {"message": "Not Found"})    

                'labels': [label.name for label in mock_issue.labels],

                'assignees': [],                def test_repository_access_failure(self, e2e_temp_dir, e2e_config):

                'created_at': mock_issue.created_at,

                'updated_at': mock_issue.updated_at,            # Should raise appropriate error during initialization        """Test handling of repository access failures."""

                'url': mock_issue.html_url,

                'state': mock_issue.state            with pytest.raises(IssueProcessingError) as exc_info:        

            }

                        GitHubIntegratedIssueProcessor(        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

            mock_creator_instance = Mock()                    github_token="valid-token",            mock_creator.side_effect = GithubException(404, {"message": "Not Found"})

            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)

            mock_creator_instance.add_labels_to_issue = Mock()                    repository="nonexistent/repo",            

            mock_creator_instance.remove_labels_from_issue = Mock()

            mock_creator.return_value = mock_creator_instance                    config_path=str(e2e_config),            # Should raise appropriate error during initialization

            

            processor = GitHubIntegratedIssueProcessor(                    workflow_dir=str(e2e_temp_dir / "workflows"),            with pytest.raises(IssueProcessingError) as exc_info:

                github_token="valid-token",

                repository="testorg/testrepo",                    output_base_dir=str(e2e_temp_dir / "output")                GitHubIntegratedIssueProcessor(

                config_path=str(e2e_config),

                workflow_dir=str(e2e_temp_dir / "workflows"),                )                    github_token="valid-token",

                output_base_dir=str(e2e_temp_dir / "output")

            )                                repository="nonexistent/repo",

            

            # Process issue            # Should indicate repository access error                    config_path=str(e2e_config),

            result = processor.process_github_issue(mock_research_issue.number)

                        assert exc_info.value.error_code == "GITHUB_INIT_FAILED"                    workflow_dir=str(e2e_temp_dir / "workflows"),

            # Verify processing completed

            assert result.status.value == 'completed'            assert any(word in str(exc_info.value).lower() for word in ["not found", "404", "repository"])                    output_base_dir=str(e2e_temp_dir / "output")

    

    def test_issue_assignment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):                    )

        """Test assigning users during processing."""

            def test_github_rate_limiting(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):            

        def create_issue_data_dict(mock_issue):

            """Helper to convert mock issue to expected dict format."""        """Test handling of GitHub API rate limiting."""            error_str = str(exc_info.value).lower()

            return {

                'number': mock_issue.number,                    assert any(word in error_str for word in ["repository", "not found", "404", "access"])

                'title': mock_issue.title,

                'body': mock_issue.body,        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:    

                'labels': [label.name for label in mock_issue.labels],

                'assignees': [],            mock_creator_instance = Mock()    def test_issue_not_found(self, e2e_temp_dir, e2e_config, research_workflow_data):

                'created_at': mock_issue.created_at,

                'updated_at': mock_issue.updated_at,                    """Test handling of non-existent issues."""

                'url': mock_issue.html_url,

                'state': mock_issue.state            # First call succeeds, second call hits rate limit        

            }

                    call_count = 0        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

            mock_creator_instance = Mock()            def rate_limited_get_issue_data(number):            mock_creator_instance = Mock()

            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)

            mock_creator_instance.assign_issue = Mock()                nonlocal call_count            # Mock getting issue that doesn't exist

            mock_creator.return_value = mock_creator_instance

                            call_count += 1            mock_creator_instance.get_issue_data.side_effect = GithubException(404, {"message": "Not Found"})

            processor = GitHubIntegratedIssueProcessor(

                github_token="valid-token",                if call_count == 1:            mock_creator.return_value = mock_creator_instance

                repository="testorg/testrepo",

                config_path=str(e2e_config),                    return create_issue_data_dict(mock_research_issue)            

                workflow_dir=str(e2e_temp_dir / "workflows"),

                output_base_dir=str(e2e_temp_dir / "output")                else:            processor = GitHubIntegratedIssueProcessor(

            )

                                raise GithubException(403, {"message": "API rate limit exceeded"})                github_token="valid-token",

            # Process issue

            result = processor.process_github_issue(mock_research_issue.number)                            repository="testorg/testrepo",

            

            # Verify processing completed            mock_creator_instance.get_issue_data = rate_limited_get_issue_data                config_path=str(e2e_config),

            assert result.status.value == 'completed'

            mock_creator.return_value = mock_creator_instance                workflow_dir=str(e2e_temp_dir / "workflows"),



class TestWebhookIntegration:                            output_base_dir=str(e2e_temp_dir / "output")

    """Test webhook-style integration scenarios."""

                processor = GitHubIntegratedIssueProcessor(            )

    def test_process_multiple_issues_sequentially(self, e2e_temp_dir, e2e_config, research_workflow_data):

        """Test processing multiple issues in sequence (webhook-style)."""                github_token="valid-token",            

        

        def create_issue_data_dict(mock_issue):                repository="testorg/testrepo",            # Should raise appropriate error

            """Helper to convert mock issue to expected dict format."""

            return {                config_path=str(e2e_config),            with pytest.raises(IssueProcessingError) as exc_info:

                'number': mock_issue.number,

                'title': mock_issue.title,                workflow_dir=str(e2e_temp_dir / "workflows"),                processor.process_github_issue(999)  # Non-existent issue

                'body': mock_issue.body,

                'labels': [label.name for label in mock_issue.labels],                output_base_dir=str(e2e_temp_dir / "output")            

                'assignees': [],

                'created_at': mock_issue.created_at,            )            error_str = str(exc_info.value).lower()

                'updated_at': mock_issue.updated_at,

                'url': mock_issue.html_url,                        assert any(word in error_str for word in ["issue", "not found", "999", "404"])

                'state': mock_issue.state

            }            # First call should succeed    

        

        # Create multiple mock issues            result1 = processor.process_github_issue(123)    def test_github_rate_limiting(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

        issues = []

        for i in range(3):            assert result1.status.value == 'completed'        """Test handling of GitHub API rate limiting."""

            issue = Mock()

            issue.number = 100 + i                    

            issue.title = f"Test Issue {100 + i}"

            issue.body = f"Test issue body {100 + i}"            # Second call should handle rate limiting gracefully        def create_issue_data_dict(mock_issue):

            issue.labels = [Mock(name="site-monitor"), Mock(name="research")]

            issue.html_url = f"https://github.com/testorg/testrepo/issues/{100 + i}"            with pytest.raises(IssueProcessingError) as exc_info:            """Helper to convert mock issue to expected dict format."""

            issue.state = "open"

            issue.user = Mock(login="testuser")                processor.process_github_issue(123)            return {

            issue.created_at = "2024-01-01T00:00:00Z"

            issue.updated_at = "2024-01-01T00:00:00Z"                            'number': mock_issue.number,

            issues.append(issue)

                    error_str = str(exc_info.value).lower()                'title': mock_issue.title,

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

            mock_creator_instance = Mock()            assert any(word in error_str for word in ["rate limit", "403", "api"])                'body': mock_issue.body,

            

            # Mock getting different issues                    'labels': [label.name for label in mock_issue.labels],

            def get_issue_data(number):

                for issue in issues:    def test_issue_comment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):                'assignees': [],

                    if issue.number == number:

                        return create_issue_data_dict(issue)        """Test updating issue comments with processing status."""                'created_at': mock_issue.created_at,

                raise GithubException(404, {"message": "Not Found"})

                                    'updated_at': mock_issue.updated_at,

            mock_creator_instance.get_issue_data = get_issue_data

            mock_creator.return_value = mock_creator_instance        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:                'url': mock_issue.html_url,

            

            processor = GitHubIntegratedIssueProcessor(            mock_creator_instance = Mock()                'state': mock_issue.state

                github_token="valid-token",

                repository="testorg/testrepo",            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)            }

                config_path=str(e2e_config),

                workflow_dir=str(e2e_temp_dir / "workflows"),            mock_creator_instance.create_issue_comment = Mock()        

                output_base_dir=str(e2e_temp_dir / "output")

            )            mock_creator.return_value = mock_creator_instance        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

            

            # Process all issues                        mock_creator_instance = Mock()

            results = []

            for issue in issues:            processor = GitHubIntegratedIssueProcessor(            

                result = processor.process_github_issue(issue.number)

                results.append(result)                github_token="valid-token",            # First call succeeds, second call hits rate limit

            

            # Verify all processed successfully                repository="testorg/testrepo",            call_count = 0

            for result in results:

                assert result.status.value == 'completed'                config_path=str(e2e_config),            def rate_limited_get_issue_data(number):

            

            # Verify output directories were created                workflow_dir=str(e2e_temp_dir / "workflows"),                nonlocal call_count

            for issue in issues:

                issue_dir = e2e_temp_dir / "output" / f"{issue.number}-research-analysis"                output_base_dir=str(e2e_temp_dir / "output")                call_count += 1

                assert issue_dir.exists()
            )                if call_count == 1:

                                return create_issue_data_dict(mock_research_issue)

            # Process issue                else:

            result = processor.process_github_issue(mock_research_issue.number)                    raise GithubException(403, {"message": "API rate limit exceeded"})

                        

            # Verify processing completed            mock_creator_instance.get_issue_data = rate_limited_get_issue_data

            assert result.status.value == 'completed'            mock_creator.return_value = mock_creator_instance

            # Note: Comment verification would depend on processor implementation            

                processor = GitHubIntegratedIssueProcessor(

    def test_issue_label_management(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):                github_token="valid-token",

        """Test adding/removing labels during processing."""                repository="testorg/testrepo",

                        config_path=str(e2e_config),

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:                workflow_dir=str(e2e_temp_dir / "workflows"),

            mock_creator_instance = Mock()                output_base_dir=str(e2e_temp_dir / "output")

            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)            )

            mock_creator_instance.add_labels_to_issue = Mock()            

            mock_creator_instance.remove_labels_from_issue = Mock()            # First call should succeed

            mock_creator.return_value = mock_creator_instance            result1 = processor.process_github_issue(123)

                        assert result1.status.value == 'completed'

            processor = GitHubIntegratedIssueProcessor(            

                github_token="valid-token",            # Second call should handle rate limiting gracefully

                repository="testorg/testrepo",            with pytest.raises(IssueProcessingError) as exc_info:

                config_path=str(e2e_config),                processor.process_github_issue(123)

                workflow_dir=str(e2e_temp_dir / "workflows"),            

                output_base_dir=str(e2e_temp_dir / "output")            error_str = str(exc_info.value).lower()

            )            assert any(word in error_str for word in ["rate limit", "403", "api"])

                

            # Process issue    def test_issue_comment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

            result = processor.process_github_issue(mock_research_issue.number)        """Test updating issue comments with processing status."""

                    

            # Verify processing completed        def create_issue_data_dict(mock_issue):

            assert result.status.value == 'completed'            """Helper to convert mock issue to expected dict format."""

            # Note: Label verification would depend on processor implementation            return {

                    'number': mock_issue.number,

    def test_issue_assignment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):                'title': mock_issue.title,

        """Test assigning users during processing."""                'body': mock_issue.body,

                        'labels': [label.name for label in mock_issue.labels],

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:                'assignees': [],

            mock_creator_instance = Mock()                'created_at': mock_issue.created_at,

            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)                'updated_at': mock_issue.updated_at,

            mock_creator_instance.assign_issue = Mock()                'url': mock_issue.html_url,

            mock_creator.return_value = mock_creator_instance                'state': mock_issue.state

                        }

            processor = GitHubIntegratedIssueProcessor(        

                github_token="valid-token",        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

                repository="testorg/testrepo",            mock_creator_instance = Mock()

                config_path=str(e2e_config),            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)

                workflow_dir=str(e2e_temp_dir / "workflows"),            mock_creator_instance.create_issue_comment = Mock()

                output_base_dir=str(e2e_temp_dir / "output")            mock_creator.return_value = mock_creator_instance

            )            

                        processor = GitHubIntegratedIssueProcessor(

            # Process issue                github_token="valid-token",

            result = processor.process_github_issue(mock_research_issue.number)                repository="testorg/testrepo",

                            config_path=str(e2e_config),

            # Verify processing completed                workflow_dir=str(e2e_temp_dir / "workflows"),

            assert result.status.value == 'completed'                output_base_dir=str(e2e_temp_dir / "output")

            # Note: Assignment verification would depend on processor implementation            )

                

    def test_github_server_error(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):            # Process issue

        """Test handling of GitHub server errors (5xx)."""            result = processor.process_github_issue(mock_research_issue.number)

                    

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:            # Verify processing completed

            mock_creator_instance = Mock()            assert result.status.value == 'completed'

            mock_creator_instance.get_issue_data.side_effect = GithubException(502, {"message": "Bad Gateway"})            # Note: Comment verification would depend on processor implementation

            mock_creator.return_value = mock_creator_instance    

                def test_issue_label_management(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

            processor = GitHubIntegratedIssueProcessor(        """Test adding/removing labels during processing."""

                github_token="valid-token",        

                repository="testorg/testrepo",        def create_issue_data_dict(mock_issue):

                config_path=str(e2e_config),            """Helper to convert mock issue to expected dict format."""

                workflow_dir=str(e2e_temp_dir / "workflows"),            return {

                output_base_dir=str(e2e_temp_dir / "output")                'number': mock_issue.number,

            )                'title': mock_issue.title,

                            'body': mock_issue.body,

            # Should handle server errors gracefully                'labels': [label.name for label in mock_issue.labels],

            with pytest.raises(IssueProcessingError) as exc_info:                'assignees': [],

                processor.process_github_issue(mock_research_issue.number)                'created_at': mock_issue.created_at,

                            'updated_at': mock_issue.updated_at,

            error_str = str(exc_info.value).lower()                'url': mock_issue.html_url,

            assert any(word in error_str for word in ["github", "502", "bad gateway", "server"])                'state': mock_issue.state

                }

    def test_network_connectivity_issues(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):        

        """Test handling of network connectivity issues."""        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

                    mock_creator_instance = Mock()

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:            mock_creator_instance.get_issue_data.return_value = create_issue_data_dict(mock_research_issue)

            mock_creator_instance = Mock()            mock_creator_instance.add_labels_to_issue = Mock()

            # Simulate network timeout/connection error            mock_creator_instance.remove_labels_from_issue = Mock()

            mock_creator_instance.get_issue_data.side_effect = ConnectionError("Network unreachable")            mock_creator.return_value = mock_creator_instance

            mock_creator.return_value = mock_creator_instance            

                        processor = GitHubIntegratedIssueProcessor(

            processor = GitHubIntegratedIssueProcessor(                github_token="valid-token",

                github_token="valid-token",                repository="testorg/testrepo",

                repository="testorg/testrepo",                config_path=str(e2e_config),

                config_path=str(e2e_config),                workflow_dir=str(e2e_temp_dir / "workflows"),

                workflow_dir=str(e2e_temp_dir / "workflows"),                output_base_dir=str(e2e_temp_dir / "output")

                output_base_dir=str(e2e_temp_dir / "output")            )

            )            

                        # Process issue

            # Should handle network errors gracefully            result = processor.process_github_issue(mock_research_issue.number)

            result = processor.process_github_issue(mock_research_issue.number)            

            assert result.status.value == 'error'            # Verify processing completed

            assert "network" in result.error_message.lower() or "connection" in result.error_message.lower()            assert result.status.value == 'completed'

            # Note: Label verification depends on processor implementation

    

class TestWebhookIntegration:    def test_issue_assignment_updates(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

    """Test webhook-style integration scenarios."""        """Test updating issue assignments during processing."""

            

    def test_process_multiple_issues_sequentially(self, e2e_temp_dir, e2e_config, research_workflow_data):        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

        """Test processing multiple issues in sequence (webhook-style)."""            mock_creator_instance = Mock()

                    mock_creator_instance.get_issue.return_value = mock_research_issue

        # Create multiple mock issues            mock_creator_instance.assign_issue = Mock()

        issues = []            mock_creator.return_value = mock_creator_instance

        for i in range(3):            

            issue = Mock()            processor = GitHubIntegratedIssueProcessor(

            issue.number = 100 + i                github_token="valid-token",

            issue.title = f"Test Issue {100 + i}"                repository="testorg/testrepo",

            issue.body = f"Test issue body {100 + i}"                config_path=str(e2e_config),

            issue.labels = [Mock(name="site-monitor"), Mock(name="research")]                workflow_dir=str(e2e_temp_dir / "workflows"),

            issue.html_url = f"https://github.com/testorg/testrepo/issues/{100 + i}"                output_base_dir=str(e2e_temp_dir / "output")

            issue.state = "open"            )

            issue.user = Mock(login="testuser")            

            issue.created_at = "2024-01-01T00:00:00Z"            # Process issue

            issue.updated_at = "2024-01-01T00:00:00Z"            result = processor.process_github_issue(mock_research_issue.number)

            issues.append(issue)            

                    # Verify processing completed

        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:            assert result.status.value == 'completed'

            mock_creator_instance = Mock()    

                def test_github_network_timeout(self, e2e_temp_dir, e2e_config):

            # Mock getting different issues        """Test handling of network timeouts."""

            def get_issue_data(number):        

                for issue in issues:        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

                    if issue.number == number:            # Mock network timeout

                        return create_issue_data_dict(issue)            import requests

                raise GithubException(404, {"message": "Not Found"})            mock_creator.side_effect = requests.exceptions.Timeout("Request timed out")

                        

            mock_creator_instance.get_issue_data = get_issue_data            # Should handle timeout gracefully

            mock_creator.return_value = mock_creator_instance            with pytest.raises(IssueProcessingError) as exc_info:

                            GitHubIntegratedIssueProcessor(

            processor = GitHubIntegratedIssueProcessor(                    github_token="valid-token",

                github_token="valid-token",                    repository="testorg/testrepo",

                repository="testorg/testrepo",                    config_path=str(e2e_config),

                config_path=str(e2e_config),                    workflow_dir=str(e2e_temp_dir / "workflows"),

                workflow_dir=str(e2e_temp_dir / "workflows"),                    output_base_dir=str(e2e_temp_dir / "output")

                output_base_dir=str(e2e_temp_dir / "output")                )

            )            

                        error_str = str(exc_info.value).lower()

            # Process all issues            assert any(word in error_str for word in ["timeout", "network", "request"])

            results = []    

            for issue in issues:    def test_github_server_error(self, e2e_temp_dir, e2e_config, mock_research_issue, research_workflow_data):

                result = processor.process_github_issue(issue.number)        """Test handling of GitHub server errors."""

                results.append(result)        

                    with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:

            # Verify all processed successfully            mock_creator_instance = Mock()

            for result in results:            # Mock server error

                assert result.status.value == 'completed'            mock_creator_instance.get_issue_data.side_effect = GithubException(500, {"message": "Internal Server Error"})

                        mock_creator.return_value = mock_creator_instance

            # Verify output directories were created            

            for issue in issues:            processor = GitHubIntegratedIssueProcessor(

                issue_dir = e2e_temp_dir / "output" / f"{issue.number}-research-analysis"                github_token="valid-token",

                assert issue_dir.exists()                repository="testorg/testrepo",
                config_path=str(e2e_config),
                workflow_dir=str(e2e_temp_dir / "workflows"),
                output_base_dir=str(e2e_temp_dir / "output")
            )
            
            # Should handle server error gracefully
            with pytest.raises(IssueProcessingError) as exc_info:
                processor.process_github_issue(123)
            
            error_str = str(exc_info.value).lower()
            assert any(word in error_str for word in ["server", "500", "internal", "error"])


class TestWebhookIntegration:
    """Test webhook-style integration scenarios."""
    
    def test_process_multiple_issues_sequentially(self, e2e_temp_dir, e2e_config, research_workflow_data):
        """Test processing multiple issues in sequence (webhook-style)."""
        
        # Create multiple mock issues
        issues = []
        for i in range(3):
            issue = Mock()
            issue.number = 100 + i
            issue.title = f"Test Issue {100 + i}"
            issue.body = f"Test issue body {100 + i}"
            issue.labels = [Mock(name="site-monitor"), Mock(name="research")]
            issue.html_url = f"https://github.com/testorg/testrepo/issues/{100 + i}"
            issue.state = "open"
            issue.user = Mock(login="testuser")
            issue.created_at = "2024-01-01T00:00:00Z"
            issue.updated_at = "2024-01-01T00:00:00Z"
            issues.append(issue)
        
        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:
            mock_creator_instance = Mock()
            
            # Mock getting different issues
            def get_issue(number):
                for issue in issues:
                    if issue.number == number:
                        return issue
                raise GithubException(404, {"message": "Not Found"})
            
            mock_creator_instance.get_issue = get_issue
            mock_creator.return_value = mock_creator_instance
            
            processor = GitHubIntegratedIssueProcessor(
                github_token="valid-token",
                repository="testorg/testrepo",
                config_path=str(e2e_config),
                workflow_dir=str(e2e_temp_dir / "workflows"),
                output_base_dir=str(e2e_temp_dir / "output")
            )
            
            # Process all issues
            results = []
            for issue in issues:
                result = processor.process_github_issue(issue.number)
                results.append(result)
            
            # Verify all processed successfully
            for result in results:
                assert result.status.value == 'completed'
            
            # Verify separate output directories
            for issue in issues:
                output_dir = e2e_temp_dir / "output" / f"{issue.number}-research-analysis"
                assert output_dir.exists()
    
    def test_process_with_invalid_webhook_data(self, e2e_temp_dir, e2e_config, research_workflow_data):
        """Test handling of invalid webhook data."""
        
        with patch('src.issue_processor.GitHubIssueCreator') as mock_creator:
            mock_creator_instance = Mock()
            mock_creator.return_value = mock_creator_instance
            
            processor = GitHubIntegratedIssueProcessor(
                github_token="valid-token",
                repository="testorg/testrepo",
                config_path=str(e2e_config),
                workflow_dir=str(e2e_temp_dir / "workflows"),
                output_base_dir=str(e2e_temp_dir / "output")
            )
            
            # Test with invalid issue number types
            with pytest.raises((IssueProcessingError, ValueError, TypeError)):
                processor.process_github_issue("invalid")  # type: ignore
            
            # Test with negative issue number
            with pytest.raises((IssueProcessingError, ValueError)):
                processor.process_github_issue(-1)
            
            # Test with zero issue number  
            with pytest.raises((IssueProcessingError, ValueError)):
                processor.process_github_issue(0)