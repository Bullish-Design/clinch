# tests/test_jj_example.py
"""Tests for the Jujutsu VCS example plugin.

All tests exercise the parsing layer against realistic ``jj`` output.
No ``jj`` binary is required.
"""
from __future__ import annotations

from clinch.examples.jj import (
    JJDiffStatFile,
    JJDiffStatSummary,
    JJFileChange,
    JJLogEntry,
    JJRevisionInfo,
)


# ---------------------------------------------------------------------------
# jj status -- file change lines
# ---------------------------------------------------------------------------

JJ_STATUS_OUTPUT = """\
Working copy changes:
M src/lib.rs
M Cargo.toml
A src/new_module.rs
D old_file.txt
Working copy  : qzmzpxyl bc915fcd (no description set)
Parent commit : zzzzzzzz 00000000 (empty) (no description set)
"""


class TestJJFileChange:
    def test_parse_modified(self) -> None:
        result = JJFileChange.parse_output("M src/lib.rs")
        assert len(result.successes) == 1
        f = result.successes[0]
        assert f.status == "M"
        assert f.path == "src/lib.rs"
        assert f.status_label == "modified"

    def test_parse_added(self) -> None:
        result = JJFileChange.parse_output("A src/new_module.rs")
        f = result.successes[0]
        assert f.status == "A"
        assert f.path == "src/new_module.rs"
        assert f.status_label == "added"

    def test_parse_deleted(self) -> None:
        result = JJFileChange.parse_output("D old_file.txt")
        f = result.successes[0]
        assert f.status == "D"
        assert f.path == "old_file.txt"
        assert f.status_label == "deleted"

    def test_parse_full_status_output(self) -> None:
        result = JJFileChange.parse_output(JJ_STATUS_OUTPUT)
        # Should pick up the 4 file-change lines, skip the header and
        # revision info lines (which may show as failures -- that's fine).
        assert len(result.successes) == 4
        statuses = [f.status for f in result.successes]
        assert statuses == ["M", "M", "A", "D"]

    def test_paths_from_full_output(self) -> None:
        result = JJFileChange.parse_output(JJ_STATUS_OUTPUT)
        paths = [f.path for f in result.successes]
        assert paths == ["src/lib.rs", "Cargo.toml", "src/new_module.rs", "old_file.txt"]


# ---------------------------------------------------------------------------
# jj status -- revision info lines
# ---------------------------------------------------------------------------


class TestJJRevisionInfo:
    def test_working_copy_line(self) -> None:
        line = "Working copy  : qzmzpxyl bc915fcd (no description set)"
        result = JJRevisionInfo.parse_output(line)
        assert len(result.successes) == 1
        rev = result.successes[0]
        assert rev.change_id == "qzmzpxyl"
        assert rev.commit_id == "bc915fcd"
        assert rev.description == "(no description set)"

    def test_parent_commit_line(self) -> None:
        line = "Parent commit : zzzzzzzz 00000000 (empty) (no description set)"
        result = JJRevisionInfo.parse_output(line)
        rev = result.successes[0]
        assert rev.change_id == "zzzzzzzz"
        assert rev.commit_id == "00000000"
        assert "(empty)" in rev.description

    def test_parent_with_bookmark(self) -> None:
        line = "Parent commit : ywyvxrts 986d16f5 main | test3"
        result = JJRevisionInfo.parse_output(line)
        rev = result.successes[0]
        assert rev.change_id == "ywyvxrts"
        assert rev.commit_id == "986d16f5"
        assert "main" in rev.description

    def test_working_copy_with_description(self) -> None:
        line = "Working copy  : mnkrokmt 7f0558f8 say hello and goodbye"
        result = JJRevisionInfo.parse_output(line)
        rev = result.successes[0]
        assert rev.change_id == "mnkrokmt"
        assert rev.commit_id == "7f0558f8"
        assert rev.description == "say hello and goodbye"

    def test_multiple_parents(self) -> None:
        output = """\
Parent commit : zozvwmow ea93486e ssh-openssh | git: update error message for SSH error
Parent commit : qklyrnvv 579ecb73 push-qklyrnvvuksv | cli: print conflicted paths
"""
        result = JJRevisionInfo.parse_output(output)
        assert len(result.successes) == 2
        assert result.successes[0].change_id == "zozvwmow"
        assert result.successes[1].change_id == "qklyrnvv"


# ---------------------------------------------------------------------------
# jj log -- block parsing
# ---------------------------------------------------------------------------

JJ_LOG_OUTPUT = """\
@  ywnkulko steve@steveklabnik.com 2024-02-28 20:40:00 46b50ed7
│  (empty) (no description set)

○  puomrwxl steve@steveklabnik.com 2024-02-28 20:38:13 7a096b8a
│  it's important to comment our code

○  yyrsmnoo steve@steveklabnik.com 2024-02-28 20:24:56 ac691d85
│  hello world

◆  zzzzzzzz root() 00000000
"""

JJ_LOG_WITH_BOOKMARK = """\
@  youzwxvz christian@example.com 2025-11-03 22:12:08 e35b5e0f
│  Create jujutsu VCS tutorial outline

◆  pswmtnwq christian@example.com 2025-09-05 08:04:28 main 7cc5e620
│  Reorder content and fix headings
"""


class TestJJLogEntry:
    def test_single_header_requires_block_parsing(self) -> None:
        """A header line alone fails because ``description`` lives on
        the second line.  This confirms block parsing is required."""
        line = "@  ywnkulko steve@steveklabnik.com 2024-02-28 20:40:00 46b50ed7"
        result = JJLogEntry.parse_output(line)
        assert len(result.successes) == 0
        assert len(result.failures) == 1

    def test_two_line_entry_via_blocks(self) -> None:
        """A single two-line entry parsed as a block succeeds."""
        entry_text = (
            "@  ywnkulko steve@steveklabnik.com 2024-02-28 20:40:00 46b50ed7\n"
            "│  (empty) (no description set)"
        )
        result = JJLogEntry.parse_blocks(entry_text)
        assert len(result.successes) == 1
        entry = result.successes[0]
        assert entry.change_id == "ywnkulko"
        assert entry.author == "steve@steveklabnik.com"
        assert entry.timestamp == "2024-02-28 20:40:00"
        assert entry.commit_id == "46b50ed7"
        assert entry.description == "(empty) (no description set)"

    def test_parse_blocks(self) -> None:
        result = JJLogEntry.parse_blocks(JJ_LOG_OUTPUT)
        # The root commit line has no alpha change_id so it won't match --
        # that's expected. We should get the 3 normal commits.
        assert len(result.successes) >= 2
        first = result.successes[0]
        assert first.change_id == "ywnkulko"
        assert first.description == "(empty) (no description set)"
        assert first.is_empty is True

    def test_block_with_description(self) -> None:
        result = JJLogEntry.parse_blocks(JJ_LOG_OUTPUT)
        # Second entry should have a real description
        second = result.successes[1]
        assert second.change_id == "puomrwxl"
        assert second.description == "it's important to comment our code"
        assert second.is_empty is False

    def test_block_with_bookmark(self) -> None:
        result = JJLogEntry.parse_blocks(JJ_LOG_WITH_BOOKMARK)
        assert len(result.successes) >= 1
        first = result.successes[0]
        assert first.change_id == "youzwxvz"
        assert first.author == "christian@example.com"

    def test_timestamp_extraction(self) -> None:
        result = JJLogEntry.parse_blocks(JJ_LOG_OUTPUT)
        first = result.successes[0]
        assert first.timestamp == "2024-02-28 20:40:00"

    def test_commit_id_extraction(self) -> None:
        result = JJLogEntry.parse_blocks(JJ_LOG_OUTPUT)
        first = result.successes[0]
        assert first.commit_id == "46b50ed7"


# ---------------------------------------------------------------------------
# jj diff --stat -- per-file lines
# ---------------------------------------------------------------------------

JJ_DIFF_STAT_OUTPUT = """\
src/lib.rs   | 15 +++++++++------
src/main.rs  |  3 +++
README.md    |  2 +-
3 files changed, 10 insertions(+), 4 deletions(-)
"""


class TestJJDiffStatFile:
    def test_parse_single_line(self) -> None:
        line = "src/lib.rs   | 15 +++++++++------"
        result = JJDiffStatFile.parse_output(line)
        assert len(result.successes) == 1
        s = result.successes[0]
        assert s.path == "src/lib.rs"
        assert s.total == 15
        assert s.insertions == 9
        assert s.deletions == 6

    def test_parse_additions_only(self) -> None:
        line = "src/main.rs  |  3 +++"
        result = JJDiffStatFile.parse_output(line)
        s = result.successes[0]
        assert s.path == "src/main.rs"
        assert s.total == 3
        assert s.insertions == 3
        assert s.deletions == 0

    def test_parse_mixed(self) -> None:
        line = "README.md    |  2 +-"
        result = JJDiffStatFile.parse_output(line)
        s = result.successes[0]
        assert s.path == "README.md"
        assert s.total == 2
        assert s.insertions == 1
        assert s.deletions == 1

    def test_parse_full_diff_stat(self) -> None:
        result = JJDiffStatFile.parse_output(JJ_DIFF_STAT_OUTPUT)
        assert len(result.successes) == 3
        paths = [s.path for s in result.successes]
        assert paths == ["src/lib.rs", "src/main.rs", "README.md"]


# ---------------------------------------------------------------------------
# jj diff --stat -- summary line
# ---------------------------------------------------------------------------


class TestJJDiffStatSummary:
    def test_parse_summary(self) -> None:
        line = "3 files changed, 10 insertions(+), 4 deletions(-)"
        result = JJDiffStatSummary.parse_output(line)
        assert len(result.successes) == 1
        s = result.successes[0]
        assert s.files_changed == 3
        assert s.insertions == 10
        assert s.deletions == 4

    def test_singular_forms(self) -> None:
        line = "1 file changed, 1 insertion(+), 0 deletions(-)"
        result = JJDiffStatSummary.parse_output(line)
        s = result.successes[0]
        assert s.files_changed == 1
        assert s.insertions == 1
        assert s.deletions == 0

    def test_from_full_output(self) -> None:
        result = JJDiffStatSummary.parse_output(JJ_DIFF_STAT_OUTPUT)
        assert len(result.successes) == 1
        assert result.successes[0].files_changed == 3


# ---------------------------------------------------------------------------
# Command objects
# ---------------------------------------------------------------------------

from clinch.examples.jj import JJDiffStatCommand, JJLogCommand, JJStatusCommand


class TestJJCommands:
    def test_status_command_args(self) -> None:
        cmd = JJStatusCommand()
        assert cmd.build_args() == ["status"]

    def test_log_command_defaults(self) -> None:
        cmd = JJLogCommand()
        assert cmd.build_args() == ["log"]

    def test_log_command_with_limit(self) -> None:
        cmd = JJLogCommand(limit=5)
        assert cmd.build_args() == ["log", "--limit", "5"]

    def test_log_command_with_revisions(self) -> None:
        cmd = JJLogCommand(revisions="main..")
        assert cmd.build_args() == ["log", "--revisions", "main.."]

    def test_log_command_no_graph(self) -> None:
        cmd = JJLogCommand(no_graph=True)
        assert cmd.build_args() == ["log", "--no-graph"]

    def test_log_command_all_options(self) -> None:
        cmd = JJLogCommand(limit=10, revisions="@-", no_graph=True)
        assert cmd.build_args() == ["log", "--limit", "10", "--revisions", "@-", "--no-graph"]

    def test_diff_stat_command_defaults(self) -> None:
        cmd = JJDiffStatCommand()
        assert cmd.build_args() == ["diff", "--stat"]

    def test_diff_stat_command_with_revision(self) -> None:
        cmd = JJDiffStatCommand(revision="@-")
        assert cmd.build_args() == ["diff", "--stat", "--revision", "@-"]
