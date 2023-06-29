from git import Repo
from datetime import datetime, timezone

# Set the path of the existing Linux-next repository
REPO_PATH = "/home/moe/kensato/patch-dataset/linux-next"

# Set the search term for commit messages
SEARCH_TERM = "Fixes:"

# Set the start date to find commits after
START_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Change the date as needed

# Open the existing Linux-next repository
repo = Repo(REPO_PATH)

# Fetch the latest commits
origin = repo.remotes.origin
origin.fetch()

# Iterate over the commit history and search for the specified search term in commit messages
for commit in repo.iter_commits():
    if commit.committed_datetime > START_DATE:
        if SEARCH_TERM in commit.message:
            commit_time = commit.committed_datetime.strftime("%Y-%m-%d")
            print(commit_time, commit.hexsha)
    else:
        break
