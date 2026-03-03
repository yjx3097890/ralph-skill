"""
Git 管理器单元测试

测试 GitManager 类的所有功能:
- 分支创建、切换、合并、删除
- 代码提交和回滚
- WIP 分支管理
- 仓库状态查询
"""

import tempfile
from pathlib import Path

import pytest
from git import Repo

from ralph.managers.git_manager import (
    BranchOperationError,
    CommitOperationError,
    GitManager,
    RepositoryNotFoundError,
)


@pytest.fixture
def temp_git_repo():
    """创建临时 Git 仓库用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化 Git 仓库
        repo = Repo.init(tmpdir)

        # 配置 Git 用户信息
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        # 创建初始提交
        test_file = Path(tmpdir) / "README.md"
        test_file.write_text("# Test Repository\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        yield tmpdir


@pytest.fixture
def git_manager(temp_git_repo):
    """创建 GitManager 实例"""
    return GitManager(temp_git_repo)


class TestGitManagerInit:
    """测试 GitManager 初始化"""

    def test_init_with_valid_repo(self, temp_git_repo):
        """测试使用有效仓库初始化"""
        manager = GitManager(temp_git_repo)
        assert manager.repo_path == Path(temp_git_repo)
        assert manager.repo is not None

    def test_init_with_invalid_repo(self):
        """测试使用无效仓库初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 空目录,不是 Git 仓库
            with pytest.raises(RepositoryNotFoundError):
                GitManager(tmpdir)


class TestBranchManagement:
    """测试分支管理功能"""

    def test_create_branch(self, git_manager):
        """测试创建分支"""
        git_manager.create_branch("feature-test")
        assert "feature-test" in git_manager.list_branches()

    def test_create_branch_from_start_point(self, git_manager):
        """测试从指定起始点创建分支"""
        # 创建一个提交
        test_file = git_manager.repo_path / "test.txt"
        test_file.write_text("test content")
        commit_hash = git_manager.commit_changes("Add test file")

        # 从该提交创建分支
        git_manager.create_branch("feature-from-commit", commit_hash)
        assert "feature-from-commit" in git_manager.list_branches()

    def test_checkout_existing_branch(self, git_manager):
        """测试切换到已存在的分支"""
        git_manager.create_branch("feature-test")
        git_manager.checkout_branch("feature-test")
        assert git_manager.get_current_branch() == "feature-test"

    def test_checkout_nonexistent_branch_without_create(self, git_manager):
        """测试切换到不存在的分支(不创建)"""
        with pytest.raises(BranchOperationError):
            git_manager.checkout_branch("nonexistent-branch", create_if_missing=False)

    def test_checkout_nonexistent_branch_with_create(self, git_manager):
        """测试切换到不存在的分支(自动创建)"""
        git_manager.checkout_branch("new-branch", create_if_missing=True)
        assert git_manager.get_current_branch() == "new-branch"
        assert "new-branch" in git_manager.list_branches()

    def test_merge_branch(self, git_manager):
        """测试合并分支"""
        # 创建并切换到新分支
        git_manager.create_branch("feature-branch")
        git_manager.checkout_branch("feature-branch")

        # 在新分支上创建提交
        test_file = git_manager.repo_path / "feature.txt"
        test_file.write_text("feature content")
        git_manager.commit_changes("Add feature file")

        # 切换回主分支并合并
        main_branch = git_manager._get_main_branch()
        git_manager.checkout_branch(main_branch)
        git_manager.merge_branch("feature-branch")

        # 验证文件存在
        assert (git_manager.repo_path / "feature.txt").exists()

    def test_merge_nonexistent_branch(self, git_manager):
        """测试合并不存在的分支"""
        with pytest.raises(BranchOperationError):
            git_manager.merge_branch("nonexistent-branch")

    def test_delete_branch(self, git_manager):
        """测试删除分支"""
        git_manager.create_branch("temp-branch")
        assert "temp-branch" in git_manager.list_branches()

        git_manager.delete_branch("temp-branch")
        assert "temp-branch" not in git_manager.list_branches()

    def test_delete_current_branch(self, git_manager):
        """测试删除当前分支(应该失败)"""
        current_branch = git_manager.get_current_branch()
        with pytest.raises(BranchOperationError):
            git_manager.delete_branch(current_branch)

    def test_delete_nonexistent_branch(self, git_manager):
        """测试删除不存在的分支(应该静默成功)"""
        # 不应该抛出异常
        git_manager.delete_branch("nonexistent-branch")

    def test_list_branches(self, git_manager):
        """测试列出分支"""
        git_manager.create_branch("branch1")
        git_manager.create_branch("branch2")

        branches = git_manager.list_branches()
        assert "branch1" in branches
        assert "branch2" in branches


class TestCommitManagement:
    """测试提交管理功能"""

    def test_commit_changes_with_add_all(self, git_manager):
        """测试提交所有变更"""
        # 创建新文件
        test_file = git_manager.repo_path / "new_file.txt"
        test_file.write_text("new content")

        commit_hash = git_manager.commit_changes("Add new file")
        assert commit_hash is not None
        assert len(commit_hash) == 40  # SHA-1 哈希长度

    def test_commit_changes_with_specific_files(self, git_manager):
        """测试提交指定文件"""
        # 创建多个文件
        file1 = git_manager.repo_path / "file1.txt"
        file2 = git_manager.repo_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        # 只提交 file1
        commit_hash = git_manager.commit_changes("Add file1", add_all=False, files=["file1.txt"])
        assert commit_hash is not None

        # file2 应该仍然是未跟踪状态
        status = git_manager.get_repo_status()
        assert "file2.txt" in status["untracked_files"]

    def test_commit_with_no_changes(self, git_manager):
        """测试在没有变更时提交"""
        # 获取当前提交哈希
        current_hash = git_manager.repo.head.commit.hexsha

        # 尝试提交(没有变更)
        commit_hash = git_manager.commit_changes("No changes")

        # 应该返回当前提交哈希
        assert commit_hash == current_hash

    def test_commit_with_long_message(self, git_manager):
        """测试使用过长的提交消息"""
        # 创建新文件
        test_file = git_manager.repo_path / "test.txt"
        test_file.write_text("test")

        # 使用超长消息
        long_message = "A" * 600
        commit_hash = git_manager.commit_changes(long_message)

        # 验证提交成功
        assert commit_hash is not None

        # 验证消息被截断
        commit = git_manager.repo.head.commit
        assert len(commit.message) <= 503  # 500 + "..."

    def test_rollback_to_commit_hard(self, git_manager):
        """测试硬回滚到指定提交"""
        # 创建第一个提交
        file1 = git_manager.repo_path / "file1.txt"
        file1.write_text("content 1")
        commit1_hash = git_manager.commit_changes("Commit 1")

        # 创建第二个提交
        file2 = git_manager.repo_path / "file2.txt"
        file2.write_text("content 2")
        git_manager.commit_changes("Commit 2")

        # 回滚到第一个提交
        git_manager.rollback_to_commit(commit1_hash, hard=True)

        # 验证 file2 不存在
        assert not file2.exists()
        assert file1.exists()

    def test_rollback_to_commit_soft(self, git_manager):
        """测试软回滚到指定提交"""
        # 创建第一个提交
        file1 = git_manager.repo_path / "file1.txt"
        file1.write_text("content 1")
        commit1_hash = git_manager.commit_changes("Commit 1")

        # 创建第二个提交
        file2 = git_manager.repo_path / "file2.txt"
        file2.write_text("content 2")
        git_manager.commit_changes("Commit 2")

        # 软回滚到第一个提交
        git_manager.rollback_to_commit(commit1_hash, hard=False)

        # 文件应该仍然存在,但在暂存区
        assert file2.exists()
        status = git_manager.get_repo_status()
        assert "file2.txt" in status["staged_files"]

    def test_get_commit_history(self, git_manager):
        """测试获取提交历史"""
        # 创建几个提交
        for i in range(3):
            test_file = git_manager.repo_path / f"file{i}.txt"
            test_file.write_text(f"content {i}")
            git_manager.commit_changes(f"Commit {i}")

        # 获取提交历史
        history = git_manager.get_commit_history(max_count=5)

        # 验证历史记录
        assert len(history) >= 3  # 至少有我们创建的 3 个提交
        assert all("hash" in commit for commit in history)
        assert all("message" in commit for commit in history)
        assert all("author" in commit for commit in history)


class TestWIPBranchManagement:
    """测试 WIP 分支管理功能"""

    def test_create_wip_branch(self, git_manager):
        """测试创建 WIP 分支"""
        task_id = "task_123"
        wip_branch = git_manager.create_wip_branch(task_id)

        # 验证分支名称格式
        assert wip_branch.startswith(f"wip_{task_id}_")
        assert wip_branch in git_manager.list_branches()
        assert git_manager.get_current_branch() == wip_branch

    def test_cleanup_wip_branch_without_merge(self, git_manager):
        """测试清理 WIP 分支(不合并)"""
        # 创建 WIP 分支
        wip_branch = git_manager.create_wip_branch("task_456")

        # 在 WIP 分支上创建提交
        test_file = git_manager.repo_path / "wip_file.txt"
        test_file.write_text("wip content")
        git_manager.commit_changes("WIP commit")

        # 清理 WIP 分支(不合并)
        git_manager.cleanup_wip_branch(wip_branch, merge_to_main=False)

        # 验证分支已删除
        assert wip_branch not in git_manager.list_branches()

        # 验证已切换回主分支
        main_branch = git_manager._get_main_branch()
        assert git_manager.get_current_branch() == main_branch

        # 验证 WIP 文件不存在(因为没有合并)
        assert not test_file.exists()

    def test_cleanup_wip_branch_with_merge(self, git_manager):
        """测试清理 WIP 分支(合并到主分支)"""
        # 创建 WIP 分支
        wip_branch = git_manager.create_wip_branch("task_789")

        # 在 WIP 分支上创建提交
        test_file = git_manager.repo_path / "wip_file.txt"
        test_file.write_text("wip content")
        git_manager.commit_changes("WIP commit")

        # 清理 WIP 分支(合并到主分支)
        git_manager.cleanup_wip_branch(wip_branch, merge_to_main=True)

        # 验证分支已删除
        assert wip_branch not in git_manager.list_branches()

        # 验证已切换回主分支
        main_branch = git_manager._get_main_branch()
        assert git_manager.get_current_branch() == main_branch

        # 验证 WIP 文件存在(因为已合并)
        assert test_file.exists()


class TestRepoStatus:
    """测试仓库状态查询功能"""

    def test_get_current_branch(self, git_manager):
        """测试获取当前分支"""
        current_branch = git_manager.get_current_branch()
        assert current_branch in ["main", "master"]

    def test_get_repo_status_clean(self, git_manager):
        """测试获取干净仓库的状态"""
        status = git_manager.get_repo_status()

        assert "current_branch" in status
        assert status["is_dirty"] is False
        assert len(status["untracked_files"]) == 0
        assert len(status["modified_files"]) == 0

    def test_get_repo_status_with_changes(self, git_manager):
        """测试获取有变更的仓库状态"""
        # 创建未跟踪文件
        untracked_file = git_manager.repo_path / "untracked.txt"
        untracked_file.write_text("untracked")

        # 修改已跟踪文件
        readme = git_manager.repo_path / "README.md"
        readme.write_text("# Modified\n")

        status = git_manager.get_repo_status()

        assert status["is_dirty"] is True
        assert "untracked.txt" in status["untracked_files"]
        assert "README.md" in status["modified_files"]

    def test_has_uncommitted_changes_false(self, git_manager):
        """测试检查未提交变更(无变更)"""
        assert git_manager.has_uncommitted_changes() is False

    def test_has_uncommitted_changes_true(self, git_manager):
        """测试检查未提交变更(有变更)"""
        # 创建新文件
        test_file = git_manager.repo_path / "test.txt"
        test_file.write_text("test")

        assert git_manager.has_uncommitted_changes() is True


class TestPrivateMethods:
    """测试私有辅助方法"""

    def test_get_main_branch_with_main(self, git_manager):
        """测试获取主分支(main 存在)"""
        # 默认创建的是 master 分支,重命名为 main
        if "master" in git_manager.list_branches():
            git_manager.repo.git.branch("-m", "master", "main")

        main_branch = git_manager._get_main_branch()
        assert main_branch == "main"

    def test_get_main_branch_with_master(self, git_manager):
        """测试获取主分支(master 存在)"""
        # 确保使用 master 分支
        if "main" in git_manager.list_branches():
            git_manager.repo.git.branch("-m", "main", "master")

        main_branch = git_manager._get_main_branch()
        assert main_branch == "master"

    def test_get_main_branch_not_found(self, git_manager):
        """测试获取主分支(都不存在)"""
        # 重命名主分支为其他名称
        current_branch = git_manager.get_current_branch()
        git_manager.repo.git.branch("-m", current_branch, "develop")

        with pytest.raises(BranchOperationError):
            git_manager._get_main_branch()


class TestErrorHandling:
    """测试错误处理"""

    def test_commit_without_files_or_add_all(self, git_manager):
        """测试提交时既不指定文件也不使用 add_all"""
        with pytest.raises(CommitOperationError):
            git_manager.commit_changes("Test", add_all=False, files=None)

    def test_rollback_to_invalid_commit(self, git_manager):
        """测试回滚到无效的提交"""
        with pytest.raises(CommitOperationError):
            git_manager.rollback_to_commit("invalid_hash")
