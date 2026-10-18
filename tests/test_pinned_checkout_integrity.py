"""Pure host Git fixtures: no private Oreslang source or guest compiler required."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_pinned_checkouts import verify_pinned_checkouts


class PinnedCheckoutIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repos, self.commits, self.trees = {}, {}, {}
        for name in ('oreslang-tensor', 'oreslang-autograd', 'oreslang-ml'):
            repo = self.root / name
            repo.mkdir()
            self.cmd(repo, 'init', '-q')
            self.cmd(repo, 'config', 'user.email', 'synthetic@example.invalid')
            self.cmd(repo, 'config', 'user.name', 'Synthetic Test')
            (repo / 'fixture.txt').write_text('version one\n')
            self.cmd(repo, 'add', 'fixture.txt')
            self.cmd(repo, 'commit', '-qm', 'synthetic v1')
            self.repos[name] = repo
            self.commits[name] = self.cmd(repo, 'rev-parse', 'HEAD')
            self.trees[name] = self.cmd(repo, 'show', '-s', '--format=%T', 'HEAD')

    @staticmethod
    def cmd(repo, *args):
        return subprocess.run(['git', '-C', str(repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_pinned_pristine_three_repos_accepted(self):
        self.assertIsNone(verify_pinned_checkouts(self.repos, self.commits, self.trees))

    def test_clean_new_commit_denied(self):
        repo = self.repos['oreslang-tensor']
        (repo / 'fixture.txt').write_text('version two\n')
        self.cmd(repo, 'commit', '-qam', 'synthetic v2')
        self.assertEqual(self.cmd(repo, 'status', '--porcelain'), '')
        with self.assertRaisesRegex(ValueError, 'commit changed'):
            verify_pinned_checkouts(self.repos, self.commits, self.trees)

    def test_dirty_tracked_change_denied(self):
        (self.repos['oreslang-ml'] / 'fixture.txt').write_text('tamper\n')
        with self.assertRaisesRegex(ValueError, 'checkout dirty'):
            verify_pinned_checkouts(self.repos, self.commits, self.trees)

    def test_untracked_file_denied(self):
        (self.repos['oreslang-autograd'] / 'untracked.txt').write_text('tamper\n')
        with self.assertRaisesRegex(ValueError, 'checkout dirty'):
            verify_pinned_checkouts(self.repos, self.commits, self.trees)

    def test_wrong_tree_pin_denied(self):
        self.trees['oreslang-ml'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'Git tree changed'):
            verify_pinned_checkouts(self.repos, self.commits, self.trees)

    def test_missing_repository_denied(self):
        self.repos.pop('oreslang-ml')
        with self.assertRaisesRegex(ValueError, 'incomplete repository identity map'):
            verify_pinned_checkouts(self.repos, self.commits, self.trees)

    def test_git_dir_environment_override_ignored(self):
        # The integrity checker must not follow an injected Git directory.
        with patch.dict(os.environ, {'GIT_DIR': str(self.repos['oreslang-tensor'] / '.git'),
                                     'GIT_WORK_TREE': str(self.repos['oreslang-tensor'])}):
            self.assertIsNone(verify_pinned_checkouts(self.repos, self.commits, self.trees))


if __name__ == '__main__':
    unittest.main()
