# Speculum Principum

A Python application framework designed to run operations via GitHub Actions. This project demonstrates how to automate repository operations using GitHub Actions workflows that trigger Python scripts.

## Features

- **Issue Creation**: Automatically create GitHub issues with customizable titles, descriptions, labels, and assignees
- **Scheduled Operations**: Run daily, weekly, or monthly automated tasks
- **GitHub Actions Integration**: All operations run via GitHub Actions with proper permissions
- **Extensible Framework**: Easy to add new operations and workflows

## Project Structure

```
speculum-principum/
├── .github/
│   └── workflows/
│       ├── create-issue.yml          # Manual issue creation workflow
│       └── scheduled-operations.yml  # Automated scheduled operations
├── src/
│   ├── __init__.py
│   └── github_operations.py         # GitHub API operations
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
└── README.md                        # This file
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/speculum-principum.git
cd speculum-principum
```

### 2. Install Dependencies (for local development)

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your values:
- `GITHUB_TOKEN`: Your GitHub personal access token
- `GITHUB_REPOSITORY`: Your repository in format `owner/repo`

### 4. GitHub Token Setup

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Create a new token with the following permissions:
   - `repo` (full repository access)
   - `workflow` (if you want to trigger workflows)
3. The `GITHUB_TOKEN` secret is automatically available in GitHub Actions

## Usage

### Manual Issue Creation

You can manually trigger issue creation through GitHub Actions:

1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Select "Create Issue" workflow
4. Click "Run workflow"
5. Fill in the form:
   - **Title**: Required issue title
   - **Body**: Optional issue description
   - **Labels**: Comma-separated labels (e.g., `bug,urgent`)
   - **Assignees**: Comma-separated usernames (e.g., `user1,user2`)

### Scheduled Operations

The project includes automated scheduled operations:

- **Daily Standup Issues**: Created every day at 9 AM UTC
- **Weekly Review Issues**: Can be triggered manually
- **Monthly Report Issues**: Can be triggered manually

### Local Development

Run the application locally (requires proper environment setup):

```bash
# Create a simple issue
python main.py create-issue --title "Test Issue" --body "This is a test issue"

# Create an issue with labels and assignees
python main.py create-issue --title "Bug Report" --body "Found a bug" --labels bug urgent --assignees username1 username2
```

## Available Operations

### create-issue

Creates a new GitHub issue in the repository.

**Arguments:**
- `--title` (required): Issue title
- `--body` (optional): Issue description/body
- `--labels` (optional): Space-separated list of labels
- `--assignees` (optional): Space-separated list of usernames to assign

**Example:**
```bash
python main.py create-issue \
  --title "New Feature Request" \
  --body "Detailed description of the feature" \
  --labels "enhancement" "feature-request" \
  --assignees "developer1" "developer2"
```

## GitHub Actions Workflows

### create-issue.yml

Manual workflow for creating issues with custom parameters.

**Triggers:**
- Manual dispatch (`workflow_dispatch`)

**Inputs:**
- `title`: Issue title (required)
- `body`: Issue description (optional)
- `labels`: Comma-separated labels (optional)
- `assignees`: Comma-separated assignees (optional)

### scheduled-operations.yml

Automated and manual operations for regular maintenance tasks.

**Triggers:**
- Scheduled: Daily at 9 AM UTC
- Manual dispatch with operation type selection

**Operations:**
- `daily-standup-issue`: Creates daily standup template
- `weekly-review-issue`: Creates weekly review template
- `monthly-report-issue`: Creates monthly report template

## Extending the Framework

### Adding New Operations

1. **Add the operation to `main.py`**:
   ```python
   parser.add_argument('operation', choices=['create-issue', 'your-new-operation'])
   ```

2. **Implement the operation in `src/github_operations.py`**:
   ```python
   def your_new_operation(self, **kwargs):
       # Implementation here
       pass
   ```

3. **Add the operation logic to `main.py`**:
   ```python
   elif args.operation == 'your-new-operation':
       # Handle your new operation
   ```

### Adding New Workflows

Create new workflow files in `.github/workflows/` following the existing patterns:

```yaml
name: Your New Workflow

on:
  workflow_dispatch:
    # Your trigger configuration

jobs:
  your-job:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write  # Add permissions as needed
    steps:
      # Your workflow steps
```

## Security Considerations

- The `GITHUB_TOKEN` is automatically provided in GitHub Actions
- Workflows run with minimal required permissions
- No sensitive data is logged or exposed
- All operations are auditable through GitHub Actions logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite: `./run_tests.sh all`
6. Submit a pull request

## Testing

The project includes a comprehensive test suite with unit tests, integration tests, and automated CI/CD testing.

### Running Tests

**Quick test run:**
```bash
./run_tests.sh unit
```

**Full test suite with coverage:**
```bash
./run_tests.sh coverage
```

**All available test options:**
```bash
./run_tests.sh help
```

**Using Make (alternative):**
```bash
make test          # Run all tests
make test-unit     # Run unit tests only
make coverage      # Run with coverage report
make lint          # Run linting checks
make security      # Run security scans
```

**Manual pytest execution:**
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov=main --cov-report=html

# Run only unit tests
pytest tests/ -v -m "not integration"

# Run only integration tests
pytest tests/ -v -m integration
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Test fixtures and configuration
├── test_smoke.py            # Basic smoke tests
├── test_github_operations.py # Unit tests for GitHub operations
└── test_main.py            # Integration tests for main application
```

### Test Categories

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test complete workflows and CLI interactions
- **Smoke Tests**: Basic tests to validate test suite setup

### Continuous Integration

The project uses GitHub Actions for automated testing:

- **test.yml**: Runs full test suite on multiple Python versions
- Tests run on every push and pull request
- Includes linting, security scanning, and type checking
- Coverage reports are uploaded to Codecov

### Test Configuration

Test configuration is managed through:
- `pyproject.toml`: pytest and coverage settings
- `conftest.py`: shared fixtures and test utilities
- GitHub Actions workflows for CI/CD

## License

This project is open source. Please check the LICENSE file for details.

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your GitHub token has the necessary permissions
2. **Invalid Labels**: Labels must exist in the repository before they can be applied
3. **Invalid Assignees**: Users must have access to the repository to be assigned

### Debugging

Check the GitHub Actions logs for detailed error messages and execution traces.

### Getting Help

- Create an issue in this repository for bugs or feature requests
- Check the GitHub Actions documentation for workflow-related questions