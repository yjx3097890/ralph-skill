"""
Git 管理器模块

提供 Git 版本控制功能,包括:
- 分支创建、切换、合并
- 代码提交和回滚
- WIP 分支管理
- 仓库状态查询

## 主要功能

### 分支管理
- create_branch: 创建新分支
- checkout_branch: 切换分支
- merge_branch: 合并分支
- delete_branch: 删除分支
- list_branches: 列出所有分支

### 提交管理
- commit_changes: 提交代码变更
- rollback_to_commit: 回滚到指定提交
- get_commit_history: 获取提交历史

### WIP 分支管理
- create_wip_branch: 创建 WIP 分支(任务ID+时间戳)
- cleanup_wip_branch: 清理 WIP 分支

### 仓库状态
- get_current_branch: 获取当前分支
- get_repo_status: 获取仓库状态
- has_uncommitted_changes: 检查是否有未提交的变更
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from git import GitCommandError, InvalidGitRepositoryError, Repo

from ralph.models.constants import (
    GIT_OPERATION_TIMEOUT,
    MAX_COMMIT_MESSAGE_LENGTH,
    TIMESTAMP_FORMAT,
    WIP_BRANCH_PREFIX,
)

logger = logging.getLogger(__name__)


class GitManagerError(Exception):
    """Git 管理器异常基类"""

    pass


class RepositoryNotFoundError(GitManagerError):
    """仓库未找到异常"""

    pass


class BranchOperationError(GitManagerError):
    """分支操作异常"""

    pass


class CommitOperationError(GitManagerError):
    """提交操作异常"""

    pass


class MergeConflictError(GitManagerError):
    """合并冲突异常"""

    def __init__(self, message: str, conflicts: List[str]):
        super().__init__(message)
        self.conflicts = conflicts


class GitManager:
    """
    Git 管理器类

    封装 GitPython 操作,提供高级 Git 功能接口。

    Attributes:
        repo_path: Git 仓库路径
        repo: GitPython Repo 对象
        timeout: Git 操作超时时间(秒)
    """

    def __init__(self, repo_path: str, timeout: int = GIT_OPERATION_TIMEOUT):
        """
        初始化 Git 管理器

        Args:
            repo_path: Git 仓库路径
            timeout: Git 操作超时时间(秒)

        Raises:
            RepositoryNotFoundError: 仓库不存在或无效
        """
        self.repo_path = Path(repo_path)
        self.timeout = timeout

        try:
            self.repo = Repo(repo_path)
            logger.info(f"成功初始化 Git 仓库: {repo_path}")
        except InvalidGitRepositoryError as e:
            error_msg = f"无效的 Git 仓库: {repo_path}"
            logger.error(error_msg)
            raise RepositoryNotFoundError(error_msg) from e

    # ========================================================================
    # 分支管理
    # ========================================================================

    def create_branch(self, branch_name: str, start_point: Optional[str] = None) -> None:
        """
        创建新分支

        Args:
            branch_name: 分支名称
            start_point: 起始点(提交哈希或分支名),默认为当前 HEAD

        Raises:
            BranchOperationError: 分支创建失败
        """
        try:
            if start_point:
                self.repo.create_head(branch_name, start_point)
                logger.info(f"创建分支 '{branch_name}' 从 '{start_point}'")
            else:
                self.repo.create_head(branch_name)
                logger.info(f"创建分支 '{branch_name}' 从当前 HEAD")
        except GitCommandError as e:
            error_msg = f"创建分支失败: {branch_name}"
            logger.error(f"{error_msg} - {str(e)}")
            raise BranchOperationError(error_msg) from e

    def checkout_branch(self, branch_name: str, create_if_missing: bool = False) -> None:
        """
        切换到指定分支

        Args:
            branch_name: 分支名称
            create_if_missing: 如果分支不存在是否创建

        Raises:
            BranchOperationError: 分支切换失败
        """
        try:
            # 检查分支是否存在
            if branch_name not in self.repo.heads:
                if create_if_missing:
                    self.create_branch(branch_name)
                else:
                    raise BranchOperationError(f"分支不存在: {branch_name}")

            # 切换分支
            self.repo.heads[branch_name].checkout()
            logger.info(f"切换到分支: {branch_name}")
        except GitCommandError as e:
            error_msg = f"切换分支失败: {branch_name}"
            logger.error(f"{error_msg} - {str(e)}")
            raise BranchOperationError(error_msg) from e

    def merge_branch(
        self, source_branch: str, target_branch: Optional[str] = None, no_ff: bool = True
    ) -> None:
        """
        合并分支

        Args:
            source_branch: 源分支名称
            target_branch: 目标分支名称,默认为当前分支
            no_ff: 是否使用 --no-ff 模式(创建合并提交)

        Raises:
            BranchOperationError: 分支不存在
            MergeConflictError: 合并冲突
        """
        try:
            # 如果指定了目标分支,先切换到目标分支
            if target_branch:
                self.checkout_branch(target_branch)

            current_branch = self.get_current_branch()

            # 检查源分支是否存在
            if source_branch not in self.repo.heads:
                raise BranchOperationError(f"源分支不存在: {source_branch}")

            # 执行合并
            source_ref = self.repo.heads[source_branch]

            # 使用 --no-ff 模式合并
            if no_ff:
                self.repo.git.merge(source_ref, no_ff=True)
            else:
                self.repo.git.merge(source_ref)

            logger.info(f"成功合并分支 '{source_branch}' 到 '{current_branch}'")

        except GitCommandError as e:
            error_output = str(e)

            # 检查是否是合并冲突
            if "CONFLICT" in error_output or "conflict" in error_output.lower():
                conflicts = self._extract_conflicts()
                error_msg = f"合并冲突: {source_branch} -> {current_branch}"
                logger.error(f"{error_msg}, 冲突文件: {conflicts}")
                raise MergeConflictError(error_msg, conflicts) from e
            else:
                error_msg = f"合并分支失败: {source_branch}"
                logger.error(f"{error_msg} - {error_output}")
                raise BranchOperationError(error_msg) from e

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """
        删除分支

        Args:
            branch_name: 分支名称
            force: 是否强制删除(即使未合并)

        Raises:
            BranchOperationError: 分支删除失败
        """
        try:
            if branch_name not in self.repo.heads:
                logger.warning(f"分支不存在,无需删除: {branch_name}")
                return

            # 不能删除当前分支
            current_branch = self.get_current_branch()
            if branch_name == current_branch:
                raise BranchOperationError(f"不能删除当前分支: {branch_name}")

            # 删除分支
            if force:
                self.repo.delete_head(branch_name, force=True)
                logger.info(f"强制删除分支: {branch_name}")
            else:
                self.repo.delete_head(branch_name)
                logger.info(f"删除分支: {branch_name}")

        except GitCommandError as e:
            error_msg = f"删除分支失败: {branch_name}"
            logger.error(f"{error_msg} - {str(e)}")
            raise BranchOperationError(error_msg) from e

    def list_branches(self, remote: bool = False) -> List[str]:
        """
        列出所有分支

        Args:
            remote: 是否列出远程分支

        Returns:
            分支名称列表
        """
        if remote:
            branches = [ref.name for ref in self.repo.remote().refs]
        else:
            branches = [head.name for head in self.repo.heads]

        return branches

    # ========================================================================
    # 提交管理
    # ========================================================================

    def commit_changes(
        self, message: str, add_all: bool = True, files: Optional[List[str]] = None
    ) -> str:
        """
        提交代码变更

        Args:
            message: 提交消息
            add_all: 是否添加所有变更文件
            files: 要添加的文件列表(如果 add_all 为 False)

        Returns:
            提交哈希值

        Raises:
            CommitOperationError: 提交失败
        """
        try:
            # 截断过长的提交消息
            if len(message) > MAX_COMMIT_MESSAGE_LENGTH:
                message = message[:MAX_COMMIT_MESSAGE_LENGTH] + "..."
                logger.warning(f"提交消息过长,已截断到 {MAX_COMMIT_MESSAGE_LENGTH} 字符")

            # 添加文件到暂存区
            if add_all:
                self.repo.git.add(A=True)
                logger.debug("添加所有变更文件到暂存区")
            elif files:
                self.repo.index.add(files)
                logger.debug(f"添加指定文件到暂存区: {files}")
            else:
                raise CommitOperationError("必须指定 add_all=True 或提供 files 列表")

            # 检查是否有变更需要提交
            if not self.repo.is_dirty(untracked_files=True):
                logger.info("没有变更需要提交")
                return self.repo.head.commit.hexsha

            # 执行提交
            commit = self.repo.index.commit(message)
            commit_hash = commit.hexsha[:8]  # 短哈希
            logger.info(f"成功提交变更: {commit_hash} - {message}")

            return commit.hexsha

        except GitCommandError as e:
            error_msg = "提交变更失败"
            logger.error(f"{error_msg} - {str(e)}")
            raise CommitOperationError(error_msg) from e

    def rollback_to_commit(self, commit_hash: str, hard: bool = True) -> None:
        """
        回滚到指定提交

        Args:
            commit_hash: 提交哈希值
            hard: 是否使用 hard 模式(丢弃所有变更)

        Raises:
            CommitOperationError: 回滚失败
        """
        try:
            if hard:
                self.repo.git.reset("--hard", commit_hash)
                logger.info(f"硬回滚到提交: {commit_hash}")
            else:
                self.repo.git.reset("--soft", commit_hash)
                logger.info(f"软回滚到提交: {commit_hash}")

        except GitCommandError as e:
            error_msg = f"回滚到提交失败: {commit_hash}"
            logger.error(f"{error_msg} - {str(e)}")
            raise CommitOperationError(error_msg) from e

    def get_commit_history(self, max_count: int = 10) -> List[dict]:
        """
        获取提交历史

        Args:
            max_count: 最大返回数量

        Returns:
            提交历史列表,每个元素包含:
            - hash: 提交哈希
            - short_hash: 短哈希
            - message: 提交消息
            - author: 作者
            - date: 提交日期
        """
        commits = []
        for commit in self.repo.iter_commits(max_count=max_count):
            commits.append(
                {
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                }
            )

        return commits

    # ========================================================================
    # WIP 分支管理
    # ========================================================================

    def create_wip_branch(self, task_id: str) -> str:
        """
        创建 WIP 分支

        分支命名规则: wip_<task_id>_<timestamp>
        例如: wip_task_123_20241201_143022

        Args:
            task_id: 任务 ID

        Returns:
            创建的 WIP 分支名称

        Raises:
            BranchOperationError: 分支创建失败
        """
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        branch_name = f"{WIP_BRANCH_PREFIX}_{task_id}_{timestamp}"

        try:
            self.create_branch(branch_name)
            self.checkout_branch(branch_name)
            logger.info(f"创建并切换到 WIP 分支: {branch_name}")
            return branch_name
        except BranchOperationError as e:
            error_msg = f"创建 WIP 分支失败: {task_id}"
            logger.error(error_msg)
            raise BranchOperationError(error_msg) from e

    def cleanup_wip_branch(self, branch_name: str, merge_to_main: bool = False) -> None:
        """
        清理 WIP 分支

        Args:
            branch_name: WIP 分支名称
            merge_to_main: 是否先合并到主分支

        Raises:
            BranchOperationError: 清理失败
        """
        try:
            # 如果需要合并,先合并到主分支
            if merge_to_main:
                main_branch = self._get_main_branch()
                self.checkout_branch(main_branch)
                self.merge_branch(branch_name)
                logger.info(f"已合并 WIP 分支 '{branch_name}' 到 '{main_branch}'")
            else:
                # 切换到主分支
                main_branch = self._get_main_branch()
                self.checkout_branch(main_branch)

            # 删除 WIP 分支
            self.delete_branch(branch_name, force=not merge_to_main)
            logger.info(f"已清理 WIP 分支: {branch_name}")

        except (BranchOperationError, MergeConflictError) as e:
            error_msg = f"清理 WIP 分支失败: {branch_name}"
            logger.error(error_msg)
            raise BranchOperationError(error_msg) from e

    # ========================================================================
    # 仓库状态
    # ========================================================================

    def get_current_branch(self) -> str:
        """
        获取当前分支名称

        Returns:
            当前分支名称
        """
        return self.repo.active_branch.name

    def get_repo_status(self) -> dict:
        """
        获取仓库状态

        Returns:
            仓库状态字典,包含:
            - current_branch: 当前分支
            - is_dirty: 是否有未提交的变更
            - untracked_files: 未跟踪的文件列表
            - modified_files: 已修改的文件列表
            - staged_files: 已暂存的文件列表
        """
        return {
            "current_branch": self.get_current_branch(),
            "is_dirty": self.repo.is_dirty(untracked_files=True),
            "untracked_files": self.repo.untracked_files,
            "modified_files": [item.a_path for item in self.repo.index.diff(None)],
            "staged_files": [item.a_path for item in self.repo.index.diff("HEAD")],
        }

    def has_uncommitted_changes(self) -> bool:
        """
        检查是否有未提交的变更

        Returns:
            True 如果有未提交的变更,否则 False
        """
        return self.repo.is_dirty(untracked_files=True)

    # ========================================================================
    # 私有辅助方法
    # ========================================================================

    def _get_main_branch(self) -> str:
        """
        获取主分支名称

        尝试按顺序查找: main, master

        Returns:
            主分支名称

        Raises:
            BranchOperationError: 找不到主分支
        """
        for branch_name in ["main", "master"]:
            if branch_name in self.repo.heads:
                return branch_name

        raise BranchOperationError("找不到主分支(main 或 master)")

    def _extract_conflicts(self) -> List[str]:
        """
        提取合并冲突的文件列表

        Returns:
            冲突文件路径列表
        """
        conflicts = []

        # 从 git status 输出中提取冲突文件
        try:
            status_output = self.repo.git.status()
            for line in status_output.split("\n"):
                if "both modified:" in line or "both added:" in line:
                    # 提取文件路径
                    file_path = line.split(":", 1)[1].strip()
                    conflicts.append(file_path)
        except GitCommandError:
            logger.warning("无法提取冲突文件列表")

        return conflicts
