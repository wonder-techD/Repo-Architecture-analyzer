import os
from git import Repo
from git.exc import GitCommandError


def clone_repo(repo_url: str, target_dir: str) -> None:
    os.makedirs(target_dir, exist_ok=True)
    try:
        Repo.clone_from(repo_url, target_dir, depth=1)
    except GitCommandError as e:
        raise RuntimeError(f"Clone failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Clone failed: {e}") from e
