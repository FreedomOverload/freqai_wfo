# ft_userdata
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

# Create a Fresh Branch with a Single Commit
```bash
git checkout --orphan new-branch
git add .
git commit -m "Fresh start"
git push --force origin new-branch
git branch -D main  # Delete the old branch
git branch -m main  # Rename new-branch to main
git push --force origin main  # Overwrite remote history
git branch --unset-upstream  # Remove old tracking
git push --set-upstream origin main  # Set upstream again
```
