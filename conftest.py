"""Repo-root pytest guard — fail fast when pytest is run from the wrong cwd.

The real test config lives in ``backend/pytest.ini`` (``asyncio_mode = auto``,
``testpaths``). Running a bare ``pytest`` from the repository root does NOT pick
it up: asyncio auto-mode stays off, every async fixture breaks with
"coroutine never awaited", and the run reports a wall of bogus failures instead
of telling you the working directory is wrong.

This conftest is loaded ONLY when pytest's rootdir is the repo root — i.e. you
invoked it from here, above ``backend/pytest.ini``. When you run it correctly
(``cd backend && pytest``, or ``pytest backend/tests`` from the root), pytest
discovers ``backend/pytest.ini``, sets rootdir to ``backend/``, and this file
sits above rootdir, so it is never loaded. Its firing therefore *means* the cwd
is wrong → we stop with a clear instruction rather than lie.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    # inipath is None only when no config file was discovered upward from the
    # args — which, given backend/pytest.ini exists, means pytest was launched
    # from the repo root with no path pointing into backend/.
    if config.inipath is None:
        raise pytest.UsageError(
            "pytest must be run from the backend/ directory.\n"
            "The test config (asyncio auto-mode, testpaths) lives in "
            "backend/pytest.ini and is NOT picked up from the repo root — "
            "that silently disables asyncio auto-mode and breaks every async "
            "fixture.\n"
            "Run:  cd backend && pytest"
        )
