# GitHub Actions Permissions Setup

This document explains how to resolve the "Permission denied" error when GitHub Actions tries to push commits.

## Problem

The GitHub Actions workflow for issue processing fails with:

```
remote: {"auth_status":"access_denied_to_user","body":"Permission to terrence-giggy/speculum-principum.git denied to github-actions[bot]."}
fatal: unable to access 'https://github.com/terrence-giggy/speculum-principum/': The requested URL returned error: 403
```

## Root Cause

This happens because:
1. The repository has branch protection rules
2. The default `GITHUB_TOKEN` doesn't have permission to push to protected branches
3. The workflow needs `contents: write` permission

## Solutions

### Solution 1: Use Personal Access Token (Recommended)

1. **Create a Personal Access Token:**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Create a new token with these permissions:
     - Repository access: `speculum-principum`
     - Contents: Read and write
     - Issues: Write
     - Pull requests: Read and write
     - Metadata: Read

2. **Add the token to repository secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add a new secret named `BOT_PAT` with your token value

3. **The workflow will automatically use this token** (already configured)

### Solution 2: Use Pull Request Mode

If you prefer to review changes before they're merged:

1. **Rename the current workflow:**
   ```bash
   mv .github/workflows/ops-issue-processing.yml .github/workflows/ops-issue-processing-direct.yml
   ```

2. **Use the PR mode workflow:**
   ```bash
   mv .github/workflows/ops-issue-processing-pr.yml .github/workflows/ops-issue-processing.yml
   ```

3. **This will create PRs instead of direct pushes** for you to review and merge

### Solution 3: Adjust Branch Protection Rules

If you want to allow the default GitHub token to push:

1. Go to repository Settings → Branches
2. Edit the main branch protection rule
3. Under "Restrict pushes that create files", add `github-actions[bot]` to the allowed actors
4. Or disable "Include administrators" if you're an admin

## Current Configuration

The workflow now has these permissions:
```yaml
permissions:
  contents: write  # Required for pushing commits with generated deliverables
  issues: write
  pull-requests: read
```

And uses the PAT token when available:
```yaml
token: ${{ secrets.BOT_PAT || secrets.GITHUB_TOKEN }}
```

## Testing

After implementing a solution, test with:

1. **Dry run mode (safe):**
   - Go to Actions → Operations - Issue Processing → Run workflow
   - Set "Perform dry run" to `true`

2. **Live mode (after dry run succeeds):**
   - Set "Perform dry run" to `false`
   - Monitor the workflow logs

## Troubleshooting

If the issue persists:

1. **Check token permissions:** Ensure the PAT has all required scopes
2. **Verify branch protection:** Check if there are additional restrictions
3. **Review workflow logs:** Look for specific error messages
4. **Test manually:** Try pushing from your local machine with the same token

## Security Considerations

- **PAT tokens have broad access:** Store them securely in GitHub Secrets
- **Limit token scope:** Only grant minimum required permissions
- **Regular rotation:** Consider rotating tokens periodically
- **Monitor usage:** Review token usage in GitHub settings