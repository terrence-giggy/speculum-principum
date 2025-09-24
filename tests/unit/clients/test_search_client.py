"""
Unit tests for the search client module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.clients.search_client import (
    SearchResult, RateLimiter, GoogleCustomSearchClient, 
    normalize_url, create_search_summary
)
from src.utils.config_manager import SiteConfig, SearchConfig


class TestSearchResult:
    """Test the SearchResult class"""
    
    def test_search_result_creation(self):
        """Test creating a SearchResult"""
        result = SearchResult(
            title="Test Title",
            link="https://example.com/page",
            snippet="Test snippet content"
        )
        
        assert result.title == "Test Title"
        assert result.link == "https://example.com/page"
        assert result.snippet == "Test snippet content"
        assert result.display_link == "https://example.com/page"
        assert result.formatted_url == "https://example.com/page"
        assert result.cache_id is None
        assert isinstance(result.discovered_at, datetime)
    
    def test_search_result_with_all_fields(self):
        """Test creating a SearchResult with all fields"""
        result = SearchResult(
            title="Test Title",
            link="https://example.com/page",
            snippet="Test snippet",
            display_link="example.com/page",
            formatted_url="https://example.com/page?formatted=true",
            cache_id="cache123"
        )
        
        assert result.display_link == "example.com/page"
        assert result.formatted_url == "https://example.com/page?formatted=true"
        assert result.cache_id == "cache123"
    

class TestRateLimiter:
    """Test the RateLimiter class"""
    
    def test_rate_limiter_creation(self):
        """Test creating a RateLimiter"""
        limiter = RateLimiter(daily_limit=100)
        
        assert limiter.daily_limit == 100
        assert limiter.calls_today == 0
        assert limiter.last_reset == datetime.utcnow().date()
    
    def test_can_make_request_under_limit(self):
        """Test can_make_request when under limit"""
        limiter = RateLimiter(daily_limit=100)
        limiter.calls_today = 50
        
        assert limiter.can_make_request() is True
    
    def test_can_make_request_at_limit(self):
        """Test can_make_request when at limit"""
        limiter = RateLimiter(daily_limit=100)
        limiter.calls_today = 100
        
        assert limiter.can_make_request() is False
    
    def test_record_request(self):
        """Test recording a request"""
        limiter = RateLimiter(daily_limit=100)
        initial_calls = limiter.calls_today
        
        with patch('time.time', return_value=1234567890):
            limiter.record_request()
        
        assert limiter.calls_today == initial_calls + 1
        assert limiter.last_call_time == 1234567890
    
    @patch('time.time')
    @patch('time.sleep')
    def test_wait_if_needed(self, mock_sleep, mock_time):
        """Test waiting when rate limiting is needed"""
        limiter = RateLimiter(daily_limit=100)
        limiter.min_interval = 1.0
        limiter.last_call_time = 1000
        
        # Simulate current time being shortly after last call
        mock_time.return_value = 1000.5
        
        limiter.wait_if_needed()
        
        # Should sleep for 0.5 seconds
        mock_sleep.assert_called_once_with(0.5)
    
    def test_daily_reset(self):
        """Test that daily reset works correctly"""
        limiter = RateLimiter(daily_limit=100)
        limiter.calls_today = 50
        limiter.last_reset = datetime.utcnow().date() - timedelta(days=1)
        
        # Should reset when checking if we can make a request
        assert limiter.can_make_request() is True
        assert limiter.calls_today == 0
        assert limiter.last_reset == datetime.utcnow().date()


class TestGoogleCustomSearchClient:
    """Test the GoogleCustomSearchClient class"""
    
    @pytest.fixture
    def search_config(self):
        """Fixture providing a SearchConfig"""
        return SearchConfig(
            api_key="test-api-key",
            search_engine_id="test-search-engine-id",
            daily_query_limit=90,
            results_per_query=10,
            date_range_days=1
        )
    
    @pytest.fixture
    def site_config(self):
        """Fixture providing a SiteConfig"""
        return SiteConfig(
            url="example.com",
            name="Example Site",
            keywords=["documentation", "updates"],
            max_results=10,
            search_paths=["/docs"],
            exclude_paths=["/admin"]
        )
    
    @patch('src.clients.search_client.build')
    def test_client_initialization(self, mock_build, search_config):
        """Test initializing the Google Custom Search client"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        client = GoogleCustomSearchClient(search_config)
        
        assert client.config == search_config
        assert client.service == mock_service
        assert client.rate_limiter.daily_limit == 90
        
        mock_build.assert_called_once_with('customsearch', 'v1', developerKey='test-api-key')
    
    def test_build_search_query_basic(self, site_config):
        """Test building a basic search query"""
        with patch('src.clients.search_client.build'):
            search_config = SearchConfig(api_key="key", search_engine_id="engine")
            client = GoogleCustomSearchClient(search_config)
            
            query = client._build_search_query(site_config)
            
            assert "site:example.com" in query
            assert '("documentation" OR "updates")' in query
            assert "(inurl:/docs)" in query
            assert "-inurl:/admin" in query
    
    def test_build_search_query_minimal(self):
        """Test building search query with minimal site config"""
        with patch('src.clients.search_client.build'):
            search_config = SearchConfig(api_key="key", search_engine_id="engine")
            client = GoogleCustomSearchClient(search_config)
            
            minimal_site = SiteConfig(url="example.com", name="Example")
            query = client._build_search_query(minimal_site)
            
            assert query == "site:example.com"
    
    def test_is_valid_result_valid(self, site_config):
        """Test validating a valid search result"""
        with patch('src.clients.search_client.build'):
            search_config = SearchConfig(api_key="key", search_engine_id="engine")
            client = GoogleCustomSearchClient(search_config)
            
            result = SearchResult(
                title="Test Title",
                link="https://example.com/docs/page",
                snippet="Test snippet"
            )
            
            assert client._is_valid_result(result, site_config) is True
    
    def test_is_valid_result_wrong_domain(self, site_config):
        """Test validating result from wrong domain"""
        with patch('src.clients.search_client.build'):
            search_config = SearchConfig(api_key="key", search_engine_id="engine")
            client = GoogleCustomSearchClient(search_config)
            
            result = SearchResult(
                title="Test Title",
                link="https://different.com/page",
                snippet="Test snippet"
            )
            
            assert client._is_valid_result(result, site_config) is False
    
    def test_is_valid_result_excluded_path(self, site_config):
        """Test validating result with excluded path"""
        with patch('src.clients.search_client.build'):
            search_config = SearchConfig(api_key="key", search_engine_id="engine")
            client = GoogleCustomSearchClient(search_config)
            
            result = SearchResult(
                title="Test Title",
                link="https://example.com/admin/page",
                snippet="Test snippet"
            )
            
            assert client._is_valid_result(result, site_config) is False
    
    @patch('src.clients.search_client.build')
    def test_parse_search_results(self, mock_build, site_config):
        """Test parsing Google Search API response"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        client = GoogleCustomSearchClient(SearchConfig(api_key="key", search_engine_id="engine"))
        
        api_response = {
            'items': [
                {
                    'title': 'Test Title 1',
                    'link': 'https://example.com/docs/page1',
                    'snippet': 'Test snippet 1',
                    'displayLink': 'example.com',
                    'formattedUrl': 'https://example.com/docs/page1',
                    'cacheId': 'cache1'
                },
                {
                    'title': 'Test Title 2',
                    'link': 'https://example.com/docs/page2',
                    'snippet': 'Test snippet 2'
                }
            ],
            'searchInformation': {'totalResults': '2'}
        }
        
        results = client._parse_search_results(api_response, site_config)
        
        assert len(results) == 2
        assert results[0].title == 'Test Title 1'
        assert results[0].cache_id == 'cache1'
        assert results[1].title == 'Test Title 2'
        assert results[1].cache_id is None
    
    @patch('src.clients.search_client.build')
    def test_get_rate_limit_status(self, mock_build):
        """Test getting rate limit status"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        search_config = SearchConfig(api_key="key", search_engine_id="engine", daily_query_limit=100)
        client = GoogleCustomSearchClient(search_config)
        client.rate_limiter.calls_today = 25
        
        status = client.get_rate_limit_status()
        
        assert status['calls_made_today'] == 25
        assert status['daily_limit'] == 100
        assert status['calls_remaining'] == 75
        assert 'reset_date' in status


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_normalize_url_basic(self):
        """Test basic URL normalization"""
        url = "HTTPS://EXAMPLE.COM/PAGE/"
        normalized = normalize_url(url)
        
        assert normalized == "https://example.com/page"
    
    def test_normalize_url_with_tracking_params(self):
        """Test URL normalization with tracking parameters"""
        url = "https://example.com/page?utm_source=test&utm_medium=email&param=keep"
        normalized = normalize_url(url)
        
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "param=keep" in normalized
    
    def test_normalize_url_error_handling(self):
        """Test URL normalization error handling"""
        invalid_url = "not-a-valid-url"
        normalized = normalize_url(invalid_url)
        
        # Should fallback to lowercase
        assert normalized == "not-a-valid-url"
    
    def test_create_search_summary(self):
        """Test creating search summary"""
        results = {
            'Site 1': [
                SearchResult("Title 1", "https://example.com/1", "Snippet 1"),
                SearchResult("Title 2", "https://example.com/2", "Snippet 2")
            ],
            'Site 2': [
                SearchResult("Title 3", "https://example.com/3", "Snippet 3")
            ],
            'Site 3': []
        }
        
        summary = create_search_summary(results)
        
        assert summary['total_results'] == 3
        assert summary['sites_searched'] == 3
        assert summary['sites_with_results'] == 2
        assert 'top_keywords' in summary
        assert 'search_timestamp' in summary
        assert 'sites_summary' in summary
        
        sites_summary = summary['sites_summary']
        assert sites_summary['Site 1']['result_count'] == 2
        assert sites_summary['Site 1']['has_results'] is True
        assert sites_summary['Site 3']['result_count'] == 0
        assert sites_summary['Site 3']['has_results'] is False


@pytest.fixture
def mock_google_api_response():
    """Fixture providing a mock Google API response"""
    return {
        'items': [
            {
                'title': 'Test Documentation Update',
                'link': 'https://example.com/docs/update',
                'snippet': 'New documentation features have been released.',
                'displayLink': 'example.com',
                'formattedUrl': 'https://example.com/docs/update',
                'cacheId': 'test-cache-id'
            }
        ],
        'searchInformation': {
            'totalResults': '1'
        }
    }


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    @patch('src.clients.search_client.build')
    def test_successful_search_flow(self, mock_build, mock_google_api_response):
        """Test a complete successful search flow"""
        # Setup mock service
        mock_service = Mock()
        mock_cse = Mock()
        mock_list = Mock()
        
        mock_service.cse.return_value = mock_cse
        mock_cse.list.return_value = mock_list
        mock_list.execute.return_value = mock_google_api_response
        mock_build.return_value = mock_service
        
        # Create client and config
        search_config = SearchConfig(api_key="key", search_engine_id="engine")
        site_config = SiteConfig(url="example.com", name="Example Site")
        
        client = GoogleCustomSearchClient(search_config)
        
        # Perform search
        results = client.search_site_for_updates(site_config)
        
        # Verify results
        assert len(results) == 1
        assert results[0].title == 'Test Documentation Update'
        assert results[0].link == 'https://example.com/docs/update'
        
        # Verify API was called correctly
        mock_list.execute.assert_called_once()
        
        # Check rate limiter was updated
        assert client.rate_limiter.calls_today == 1
    
    @patch('src.clients.search_client.build')
    def test_rate_limit_exceeded(self, mock_build):
        """Test behavior when rate limit is exceeded"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        search_config = SearchConfig(api_key="key", search_engine_id="engine", daily_query_limit=1)
        site_config = SiteConfig(url="example.com", name="Example Site")
        
        client = GoogleCustomSearchClient(search_config)
        client.rate_limiter.calls_today = 1  # At limit
        
        with pytest.raises(RuntimeError, match="Daily API rate limit.*exceeded"):
            client.search_site_for_updates(site_config)