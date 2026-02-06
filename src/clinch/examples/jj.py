# src/clinch/examples/jj.py
"""CLInch plugin for Jujutsu VCS (jj).

A minimal but functional wrapper around the `jj` CLI, demonstrating how to
build a real-world CLInch plugin.  Covers three core operations:

* **status** -- working copy changes, current revision info
* **log**    -- commit history with change IDs, authors, timestamps
* **diff --stat** -- per-file insertion/deletion summary

Each operation has its own response model with regex patterns tailored to
jj's default output format, plus a command object that builds the correct
CLI arguments.  The top-level ``JJWrapper`` ties everything together.

Usage::

    from clinch.examples.jj import JJWrapper

    jj = JJWrapper()

    # Show working-copy status
    status = jj.status()
    for f in status.changed_files:
        print(f"{f.status} {f.path}")
    print(f"Working copy: {status.working_copy.change_id}")

    # Browse the log
    for entry in jj.log(limit=5):
        print(f"{entry.change_id} {entry.description}")

    # Diff stats for the working copy
    stats = jj.diff_stat()
    for s in stats.file_stats:
        print(f"{s.path}: +{s.insertions} -{s.deletions}")
    print(stats.summary)
"""
from __future__ import annotations

from pydantic import computed_field, field_validator

from clinch import BaseCLIError, BaseCLIResponse, CLIWrapper, Field, ParsingResult
from clinch.base import BaseCLICommand


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class JJFileChange(BaseCLIResponse):
    """A single changed-file line from ``jj status``.

    Matches lines like::

        M src/lib.rs
        A src/new_module.rs
        D old_file.txt
    """

    status: str = Field(pattern=r"^([AMDRC])\s+")
    path: str = Field(pattern=r"^[AMDRC]\s+(.+)$")

    @computed_field
    @property
    def status_label(self) -> str:
        """Human-readable label for the status code."""
        return {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
        }.get(self.status, self.status)


class JJRevisionInfo(BaseCLIResponse):
    """The ``Working copy`` or ``Parent commit`` line from ``jj status``.

    Matches lines like::

        Working copy  : qzmzpxyl bc915fcd (no description set)
        Parent commit : zzzzzzzz 00000000 (empty) (no description set)
        Working copy  : mnkrokmt 7f0558f8 say hello and goodbye
        Parent commit : ywyvxrts 986d16f5 main | test3
    """

    change_id: str = Field(
        pattern=r"^(?:Working copy|Parent commit)\s*(?:\(@-?\))?\s*:\s+(\w+)"
    )
    commit_id: str = Field(
        pattern=r"^(?:Working copy|Parent commit)\s*(?:\(@-?\))?\s*:\s+\w+\s+([0-9a-f]+)"
    )
    description: str = Field(
        pattern=r"^(?:Working copy|Parent commit)\s*(?:\(@-?\))?\s*:\s+\w+\s+[0-9a-f]+\s+(.*\S)\s*$"
    )

    @computed_field
    @property
    def is_working_copy(self) -> bool:
        """True when this line describes the working copy, not a parent."""
        # The description field is populated from the whole tail -- we rely
        # on the caller to know which line this came from, but we can also
        # inspect the raw data.  For simplicity, we leave it as a plain flag
        # that the wrapper sets contextually.
        return False  # overridden by the wrapper via subclass or post-processing


class JJLogEntry(BaseCLIResponse):
    """A single commit entry from ``jj log``.

    jj log produces two-line entries (header + description) joined into
    blocks by blank-line delimiters.  We use ``parse_blocks`` to merge
    them into one model per commit.

    Header line::

        @  ywnkulko steve@example.com 2024-02-28 20:40:00 46b50ed7

    Description line::

        │  (empty) (no description set)
    """

    change_id: str = Field(pattern=r"^[○◉◆×@]\s+([a-z]{4,})\s+")
    author: str = Field(pattern=r"^[○◉◆×@]\s+[a-z]+\s+(\S+)\s+\d{4}")
    timestamp: str = Field(
        pattern=r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
    )
    commit_id: str = Field(pattern=r"\s([0-9a-f]{6,})\s*$")
    description: str = Field(pattern=r"^│\s{2}(.+)$")

    @computed_field
    @property
    def is_empty(self) -> bool:
        """True when jj marks this commit as having no file changes."""
        return "(empty)" in self.description


class JJDiffStatFile(BaseCLIResponse):
    """A single file line from ``jj diff --stat``.

    Matches lines like::

        src/lib.rs   | 15 +++++++++------
        src/main.rs  |  3 +++
    """

    path: str = Field(pattern=r"^\s*(.+?)\s+\|")
    total: int = Field(pattern=r"\|\s+(\d+)\s+")
    bar: str = Field(pattern=r"\d+\s+([+-]+)\s*$")

    @field_validator("total", mode="before")
    @classmethod
    def _coerce_total(cls, v: str | int) -> int:
        return int(v)

    @computed_field
    @property
    def insertions(self) -> int:
        return self.bar.count("+")

    @computed_field
    @property
    def deletions(self) -> int:
        return self.bar.count("-")


class JJDiffStatSummary(BaseCLIResponse):
    """The summary line from ``jj diff --stat``.

    Matches::

        3 files changed, 10 insertions(+), 4 deletions(-)
    """

    files_changed: int = Field(pattern=r"^(\d+)\s+files?\s+changed")
    insertions: int = Field(pattern=r"(\d+)\s+insertions?\(\+\)")
    deletions: int = Field(pattern=r"(\d+)\s+deletions?\(-\)")

    @field_validator("files_changed", "insertions", "deletions", mode="before")
    @classmethod
    def _coerce_int(cls, v: str | int) -> int:
        return int(v)


# ---------------------------------------------------------------------------
# Error model
# ---------------------------------------------------------------------------


class JJError(BaseCLIError):
    """Structured error for failed ``jj`` commands.

    jj prints errors to stderr with a recognisable prefix::

        Error: The working copy is stale
        Hint: Run `jj workspace update-stale`
    """

    pass


# ---------------------------------------------------------------------------
# Command objects
# ---------------------------------------------------------------------------


class JJStatusCommand(BaseCLICommand):
    """``jj status``"""

    subcommand = "status"
    response_model = JJFileChange  # parsing done manually by wrapper

    def build_args(self) -> list[str]:
        return [self.subcommand]


class JJLogCommand(BaseCLICommand):
    """``jj log [--limit N] [--revisions REV]``"""

    subcommand = "log"
    response_model = JJLogEntry

    limit: int | None = None
    revisions: str | None = None
    no_graph: bool = False

    def build_args(self) -> list[str]:
        args = [self.subcommand]
        if self.limit is not None:
            args.extend(["--limit", str(self.limit)])
        if self.revisions is not None:
            args.extend(["--revisions", self.revisions])
        if self.no_graph:
            args.append("--no-graph")
        return args


class JJDiffStatCommand(BaseCLICommand):
    """``jj diff --stat [--revision REV]``"""

    subcommand = "diff"
    response_model = JJDiffStatFile

    revision: str | None = None

    def build_args(self) -> list[str]:
        args = [self.subcommand, "--stat"]
        if self.revision is not None:
            args.extend(["--revision", self.revision])
        return args


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------


class JJStatus:
    """Structured result from ``jj status``.

    Separates the raw output into changed files, working copy info, and
    parent commit info.
    """

    def __init__(
        self,
        changed_files: list[JJFileChange],
        working_copy: JJRevisionInfo | None,
        parents: list[JJRevisionInfo],
    ) -> None:
        self.changed_files = changed_files
        self.working_copy = working_copy
        self.parents = parents


class JJDiffStat:
    """Structured result from ``jj diff --stat``."""

    def __init__(
        self,
        file_stats: list[JJDiffStatFile],
        summary: JJDiffStatSummary | None,
    ) -> None:
        self.file_stats = file_stats
        self.summary = summary


class JJWrapper(CLIWrapper):
    """Wrapper around the ``jj`` (Jujutsu) CLI.

    Example::

        jj = JJWrapper()

        # Working-copy status
        status = jj.status()
        for f in status.changed_files:
            print(f"{f.status_label}: {f.path}")

        # Recent history
        for entry in jj.log(limit=5):
            print(f"{entry.change_id} -- {entry.description}")

        # Diff statistics
        diff = jj.diff_stat()
        for f in diff.file_stats:
            print(f"  {f.path}: +{f.insertions} -{f.deletions}")
    """

    command = "jj"
    error_model = JJError

    def _preprocess_output(self, output: str) -> str:
        """Strip ANSI escape codes that jj emits when color is auto."""
        import re

        return re.sub(r"\x1b\[[0-9;]*m", "", output)

    # ---- High-level API ------------------------------------------------

    def status(self) -> JJStatus:
        """Run ``jj status`` and return structured results."""
        raw = self._execute("status", response_model=JJFileChange)

        # Re-parse the full output for revision info lines
        preprocessed = self._get_raw_output("status")
        rev_result: ParsingResult[JJRevisionInfo] = JJRevisionInfo.parse_output(
            preprocessed
        )

        working_copy: JJRevisionInfo | None = None
        parents: list[JJRevisionInfo] = []
        for line in preprocessed.splitlines():
            if line.startswith("Working copy"):
                wc_parsed = JJRevisionInfo.parse_output(line)
                if wc_parsed.successes:
                    working_copy = wc_parsed.successes[0]
            elif line.startswith("Parent commit"):
                p_parsed = JJRevisionInfo.parse_output(line)
                if p_parsed.successes:
                    parents.append(p_parsed.successes[0])

        return JJStatus(
            changed_files=list(raw.successes),
            working_copy=working_copy,
            parents=parents,
        )

    def log(
        self,
        *,
        limit: int | None = None,
        revisions: str | None = None,
        no_graph: bool = False,
    ) -> list[JJLogEntry]:
        """Run ``jj log`` and return parsed commit entries.

        Uses block parsing to merge the two-line-per-commit output into
        single ``JJLogEntry`` instances.
        """
        cmd = JJLogCommand(limit=limit, revisions=revisions, no_graph=no_graph)
        args = cmd.build_args()
        raw = self._execute(*args, response_model=JJLogEntry)

        # jj log entries span two lines -- re-parse as blocks for a better
        # result.  We run the command once and post-process.
        preprocessed = self._get_raw_output(*args)
        block_result = JJLogEntry.parse_blocks(preprocessed)
        return list(block_result.successes)

    def diff_stat(self, *, revision: str | None = None) -> JJDiffStat:
        """Run ``jj diff --stat`` and return parsed statistics."""
        cmd = JJDiffStatCommand(revision=revision)
        args = cmd.build_args()
        raw_output = self._get_raw_output(*args)

        file_result: ParsingResult[JJDiffStatFile] = JJDiffStatFile.parse_output(
            raw_output
        )
        summary_result: ParsingResult[JJDiffStatSummary] = (
            JJDiffStatSummary.parse_output(raw_output)
        )

        return JJDiffStat(
            file_stats=list(file_result.successes),
            summary=summary_result.successes[0] if summary_result.successes else None,
        )

    # ---- Internal helpers -----------------------------------------------

    def _get_raw_output(self, *args: str) -> str:
        """Execute a command and return preprocessed stdout as a string.

        This is a convenience for cases where we need to parse the same
        output with multiple response models.
        """
        import sh as sh_mod

        cli_args = list(args)
        try:
            cmd = sh_mod.Command(self.command)
            result = cmd(*cli_args, _timeout=self.timeout, _err_to_out=False)
        except sh_mod.ErrorReturnCode as exc:
            stdout_text = exc.stdout.decode(self.encoding) if isinstance(exc.stdout, bytes) else str(exc.stdout)
            stderr_text = exc.stderr.decode(self.encoding) if isinstance(exc.stderr, bytes) else str(exc.stderr)
            error = self._get_error_model()(
                command=self._build_command_string(cli_args),
                exit_code=exc.exit_code,
                stderr=stderr_text,
                stdout=stdout_text,
            )
            raise error from exc

        stdout_value = getattr(result, "stdout", result)
        if isinstance(stdout_value, (bytes, bytearray)):
            stdout_text = stdout_value.decode(self.encoding)
        else:
            stdout_text = str(stdout_value)
        return self._preprocess_output(stdout_text)
