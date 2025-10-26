"""
GitHub repository manager for storing encrypted student submissions.
"""
import os
import base64
from pathlib import Path
from typing import List, Optional
from github import Github, Repository, GithubException, InputGitTreeElement
import logging

logger = logging.getLogger(__name__)


class GitHubManager:
    """Manages GitHub repository operations for student submissions."""

    def __init__(self, token: str, repo_name: str):
        """
        Initialize GitHub manager.

        Args:
            token: GitHub personal access token
            repo_name: Repository name in format 'username/repo'
        """
        self.github = Github(token)
        self.repo: Repository.Repository = self.github.get_repo(repo_name)
        logger.info(f"Connected to GitHub repository: {repo_name}")

    def get_or_create_branch(self, student_id: str, assignment_name: str) -> str:
        """
        Get or create a branch for a student's assignment.

        Args:
            student_id: Student identifier (email-based)
            assignment_name: Sanitized assignment name

        Returns:
            Branch name
        """
        branch_name = f"student-{student_id}/assignment-{assignment_name}"

        try:
            # Check if branch exists
            self.repo.get_branch(branch_name)
            logger.info(f"Branch {branch_name} already exists")
        except GithubException:
            # Create branch from main/master
            try:
                source_branch = self.repo.get_branch("main")
            except GithubException:
                source_branch = self.repo.get_branch("master")

            ref = f"refs/heads/{branch_name}"
            self.repo.create_git_ref(ref=ref, sha=source_branch.commit.sha)
            logger.info(f"Created branch {branch_name}")

        return branch_name

    def commit_file(
        self,
        file_path: Path,
        repo_path: str,
        branch_name: str,
        commit_message: str
    ) -> bool:
        """
        Commit a file to the repository.

        Args:
            file_path: Local path to the file
            repo_path: Path in the repository where file should be stored
            branch_name: Branch to commit to
            commit_message: Commit message

        Returns:
            True if successful, False otherwise
        """
        try:
            content = file_path.read_bytes()

            # Check if file already exists
            try:
                existing_file = self.repo.get_contents(repo_path, ref=branch_name)
                # Update existing file
                self.repo.update_file(
                    path=repo_path,
                    message=commit_message,
                    content=content,
                    sha=existing_file.sha,
                    branch=branch_name
                )
                logger.info(f"Updated {repo_path} in {branch_name}")
            except GithubException:
                # Create new file
                self.repo.create_file(
                    path=repo_path,
                    message=commit_message,
                    content=content,
                    branch=branch_name
                )
                logger.info(f"Created {repo_path} in {branch_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to commit {repo_path}: {e}")
            return False

    def commit_multiple_files(
        self,
        files: List[tuple[Path, str]],
        branch_name: str,
        commit_message: str
    ) -> bool:
        """
        Commit multiple files in a single commit.

        Args:
            files: List of tuples (local_path, repo_path)
            branch_name: Branch to commit to
            commit_message: Commit message

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the latest commit on the branch
            branch = self.repo.get_branch(branch_name)
            base_tree = self.repo.get_git_tree(branch.commit.sha)

            # Create blobs for each file
            tree_elements = []
            for local_path, repo_path in files:
                content = local_path.read_bytes()
                # Base64 encode binary content for GitHub API
                content_b64 = base64.b64encode(content).decode('utf-8')
                blob = self.repo.create_git_blob(content_b64, "base64")

                # Create proper InputGitTreeElement object
                element = InputGitTreeElement(
                    path=repo_path,
                    mode='100644',
                    type='blob',
                    sha=blob.sha
                )
                tree_elements.append(element)

            # Create tree
            tree = self.repo.create_git_tree(tree_elements, base_tree)

            # Create commit
            parent = self.repo.get_git_commit(branch.commit.sha)
            commit = self.repo.create_git_commit(commit_message, tree, [parent])

            # Update branch reference using the proper method
            ref_name = f"refs/heads/{branch_name}"
            try:
                # Try to update using the refs API directly
                ref = self.repo.get_git_ref(f"heads/{branch_name}")
                # Force update by setting sha and force=True
                ref.edit(sha=commit.sha, force=False)
            except Exception as e:
                # Fallback: update using low-level API
                logger.warning(f"Standard ref update failed: {e}, trying alternative method")
                # Use the update_ref method from the GitHub API
                url = f"{self.repo.url}/git/refs/heads/{branch_name}"
                headers, data = self.repo._requester.requestJsonAndCheck(
                    "PATCH",
                    url,
                    input={"sha": commit.sha, "force": False}
                )

            logger.info(f"Committed {len(files)} files to {branch_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to commit multiple files: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def get_file_content(self, file_path: str, branch_name: str) -> Optional[bytes]:
        """
        Get file content from repository.

        Args:
            file_path: Path to file in repository
            branch_name: Branch name

        Returns:
            File content as bytes, or None if not found
        """
        try:
            content = self.repo.get_contents(file_path, ref=branch_name)
            return content.decoded_content
        except GithubException:
            logger.warning(f"File {file_path} not found in {branch_name}")
            return None

    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main"
    ) -> Optional[str]:
        """
        Create a pull request for a student submission.

        Args:
            branch_name: Source branch name
            title: PR title
            body: PR description
            base_branch: Target branch (default: main)

        Returns:
            PR URL if successful, None otherwise
        """
        try:
            # Check if PR already exists
            existing_prs = self.repo.get_pulls(
                state='open',
                head=f"{self.repo.owner.login}:{branch_name}",
                base=base_branch
            )

            if existing_prs.totalCount > 0:
                pr = existing_prs[0]
                logger.info(f"PR already exists: {pr.html_url}")
                # Update PR body with new submission info
                pr.edit(body=body)
                return pr.html_url

            # Create new PR
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=base_branch
            )

            logger.info(f"Created PR: {pr.html_url}")
            return pr.html_url

        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return None
