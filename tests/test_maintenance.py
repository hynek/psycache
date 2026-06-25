# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio
import datetime as dt
import secrets
import threading
import time

import pytest

from psycache import (
    AsyncCleanupService,
    AsyncPostgresCache,
    CleanupService,
    PostgresCache,
)
from psycache._async import _cleanup_loop as _async_cleanup_loop
from psycache._sync import _cleanup_loop


def test_cleanup_expired(cache: PostgresCache):
    """
    Expired cache entries are deleted. Unexpired aren't touched.
    """

    gone_key = secrets.token_urlsafe()
    alive_key = secrets.token_urlsafe()
    alive_key_2 = secrets.token_urlsafe()

    cache.put_raw(gone_key, {"foo": "bar"}, ttl=-1)
    cache.put_raw(alive_key, {"foo": "bar"}, ttl=10)
    cache.put_raw(alive_key_2, {"foo": "bar"}, ttl=dt.timedelta(days=1))

    assert 1 == cache.cleanup_expired()
    assert cache.get_raw(gone_key) is None
    assert {"foo": "bar"} == cache.get_raw(alive_key)
    assert {"foo": "bar"} == cache.get_raw(alive_key_2)


def test_flush(cache: PostgresCache):
    """
    Flushing the cache deletes all entries.
    """

    def count():
        with cache._pool.connect() as conn:
            return conn.execute("SELECT count(*) FROM psycache").fetchone()[0]

    assert 0 == count()

    cache.put_raw(secrets.token_urlsafe(), {"foo": "bar"}, ttl=10)
    cache.put_raw(secrets.token_urlsafe(), {"foo": "bar"}, ttl=10)
    cache.put_raw(secrets.token_urlsafe(), {"foo": "bar"}, ttl=10)
    cache.put_raw(secrets.token_urlsafe(), {"foo": "bar"}, ttl=10)

    assert 4 == count()

    assert 4 == cache.flush()

    assert 0 == count()


class TestCleanupThread:
    @pytest.mark.parametrize(
        "interval", [0.0005, dt.timedelta(microseconds=5)]
    )
    def test_cleans_up_expired_entries(self, cache: PostgresCache, interval):
        """
        The cleanup thread deletes expired entries.
        """
        cache.put_raw("expired", {"v": 1}, ttl=-1)
        cache.put_raw("alive", {"v": 2}, ttl=300)

        svc = cache.start_cleanup_thread(interval=interval)
        time.sleep(0.0001)  # Give the thread time to run at least once.
        svc.stop()

        assert cache.get_raw("expired") is None
        assert {"v": 2} == cache.get_raw("alive")

    def test_stop(self, cache: PostgresCache):
        """
        stop() causes the thread to terminate.
        """
        svc = cache.start_cleanup_thread(interval=60)

        assert svc._thread.is_alive()
        assert svc.stop() is True
        assert not svc._thread.is_alive()

        # Stop is idempotent
        assert svc.stop(timeout=None) is True

    def test_stop_wait_forever(self, cache: PostgresCache):
        """
        stop(timeout=None) waits without imposing a timeout.
        """
        svc = cache.start_cleanup_thread(interval=60)

        assert svc._thread.is_alive()
        assert svc.stop(timeout=None) is True
        assert not svc._thread.is_alive()

        # Stop is idempotent
        assert svc.stop(timeout=None) is True

    def test_context_manager(self, cache: PostgresCache):
        """
        CleanupService works as a context manager and stops the thread on exit.
        """
        with cache.start_cleanup_thread(interval=60) as svc:
            assert isinstance(svc, CleanupService)
            assert svc._thread.is_alive()

        assert not svc._thread.is_alive()

    @pytest.mark.parametrize(
        "interval",
        [
            0.0,
            -1.0,
            float("nan"),
            float("inf"),
            threading.TIMEOUT_MAX + 1,
            dt.timedelta.max,
        ],
    )
    def test_rejects_invalid_intervals(
        self, cache: PostgresCache, interval: float | dt.timedelta
    ):
        """
        start_cleanup_thread() validates interval values before spawning.
        """
        with pytest.raises(ValueError):
            cache.start_cleanup_thread(interval=interval)

    def test_error_does_not_stop_thread(self):
        """
        If cleanup raises, the thread logs the error and keeps running.
        """

        def _raise_runtime_error():
            raise RuntimeError("boom")

        stop_event = threading.Event()
        thread = threading.Thread(
            target=_cleanup_loop,
            args=(_raise_runtime_error, 0.0005, stop_event),
            daemon=True,
        )
        thread.start()
        time.sleep(0.01)

        # Thread survived the errors.
        assert thread.is_alive()

        stop_event.set()
        thread.join()

    def test_stop_timeout_returns_false_for_blocked_cleanup(
        self, caplog: pytest.LogCaptureFixture
    ):
        """
        stop() returns False instead of hanging if cleanup is blocked.
        """

        cleanup_started = threading.Event()
        cleanup_finished = threading.Event()
        stop_event = threading.Event()

        def _block() -> int:
            cleanup_started.set()
            cleanup_finished.wait()
            return 0

        thread = threading.Thread(
            target=_cleanup_loop,
            args=(_block, 60, stop_event),
            daemon=True,
        )
        thread.start()

        assert cleanup_started.wait(timeout=0.01)

        svc = CleanupService(thread=thread, stop_event=stop_event)
        with caplog.at_level("WARNING"):
            assert svc.stop(timeout=0.0) is False

        assert thread.is_alive()
        assert "Cleanup thread did not stop within timeout=0.0" in caplog.text

        cleanup_finished.set()
        thread.join(timeout=1)

        assert not thread.is_alive()

    @pytest.mark.parametrize("timeout", [-1.0, float("nan")])
    def test_stop_rejects_invalid_timeout(self, timeout: float):
        """
        stop() validates timeout values before joining the thread.
        """
        stop_event = threading.Event()
        thread = threading.Thread(target=stop_event.wait, daemon=True)
        svc = CleanupService(thread=thread, stop_event=stop_event)

        with pytest.raises(ValueError):
            svc.stop(timeout=timeout)

        # We never started the thread, so we don't have to stop it.

    @pytest.mark.parametrize(
        "timeout", [threading.TIMEOUT_MAX + 1, dt.timedelta.max]
    )
    def test_stop_rejects_too_large_timeout(
        self, timeout: float | dt.timedelta
    ):
        """
        stop() rejects timeouts beyond threading.TIMEOUT_MAX.
        """
        stop_event = threading.Event()
        thread = threading.Thread(target=stop_event.wait, daemon=True)
        svc = CleanupService(thread=thread, stop_event=stop_event)

        with pytest.raises(ValueError):
            svc.stop(timeout=timeout)

        # We never started the thread, so we don't have to stop it.


@pytest.mark.asyncio
class TestCleanupTask:
    @pytest.mark.parametrize(
        "interval", [0.0005, dt.timedelta(microseconds=5)]
    )
    async def test_cleans_up_expired_entries(
        self, acache: AsyncPostgresCache, interval
    ):
        """
        The cleanup task deletes expired entries.
        """
        await acache.put_raw("expired", {"v": 1}, ttl=-1)
        await acache.put_raw("alive", {"v": 2}, ttl=300)

        svc = acache.start_cleanup_task(interval=interval)
        # Give the task time to run at least once.
        await asyncio.sleep(0.001)
        await svc.stop()

        assert await acache.get_raw("expired") is None
        assert {"v": 2} == await acache.get_raw("alive")

    async def test_stop(self, acache: AsyncPostgresCache):
        """
        stop() causes the task to terminate.
        """
        svc = acache.start_cleanup_task(interval=60)

        assert not svc._task.done()
        assert await svc.stop() is True
        assert svc._task.done()

        # Stop is idempotent
        assert await svc.stop() is True

    async def test_stop_wait_forever(self, acache: AsyncPostgresCache):
        """
        stop(timeout=None) waits without imposing a timeout.
        """
        svc = acache.start_cleanup_task(interval=60)

        assert not svc._task.done()
        assert await svc.stop(timeout=None) is True
        assert svc._task.done()

        # Stop is idempotent
        assert await svc.stop(timeout=None) is True

    async def test_context_manager(self, acache: AsyncPostgresCache):
        """
        AsyncCleanupService works as a context manager and stops the task on
        exit.
        """
        async with acache.start_cleanup_task(interval=60) as svc:
            assert isinstance(svc, AsyncCleanupService)
            assert not svc._task.done()

        assert svc._task.done()

    @pytest.mark.parametrize(
        "interval",
        [
            0.0,
            -1.0,
            float("nan"),
            float("inf"),
        ],
    )
    async def test_rejects_invalid_intervals(
        self, acache: AsyncPostgresCache, interval: float
    ):
        """
        start_cleanup_task() validates interval values before spawning.
        """
        with pytest.raises(ValueError):
            acache.start_cleanup_task(interval=interval)

    async def test_error_does_not_stop_task(self):
        """
        If cleanup raises, the task logs the error and keeps running.
        """

        async def _raise_runtime_error() -> int:
            raise RuntimeError("boom")

        stop_event = asyncio.Event()
        task = asyncio.create_task(
            _async_cleanup_loop(_raise_runtime_error, 0.005, stop_event)
        )
        try:
            await asyncio.sleep(0.05)

            # Task survived the errors.
            assert not task.done()
        finally:
            stop_event.set()
            await asyncio.wait_for(task, timeout=1)

    async def test_stop_timeout_returns_false_for_blocked_cleanup(
        self, caplog: pytest.LogCaptureFixture
    ):
        """
        stop() returns False instead of hanging if cleanup is blocked.
        """

        cleanup_started = asyncio.Event()
        cleanup_finished = asyncio.Event()
        stop_event = asyncio.Event()

        async def _block() -> int:
            cleanup_started.set()
            await cleanup_finished.wait()
            return 0

        task = asyncio.create_task(_async_cleanup_loop(_block, 60, stop_event))

        await asyncio.wait_for(cleanup_started.wait(), timeout=1)

        svc = AsyncCleanupService(task=task, stop_event=stop_event)
        with caplog.at_level("WARNING"):
            assert await svc.stop(timeout=0.0) is False

        assert not task.done()
        assert "Cleanup task did not stop within timeout=0.0" in caplog.text

        cleanup_finished.set()
        await asyncio.wait_for(task, timeout=1)

        assert task.done()

    @pytest.mark.parametrize("bad_timeout", [-1.0, float("nan"), float("inf")])
    async def test_stop_rejects_invalid_timeout(self, bad_timeout: float):
        """
        stop() validates timeout values before joining the task.
        """

        async def _wait_for_stop(stop_event: asyncio.Event) -> None:
            await stop_event.wait()

        stop_event = asyncio.Event()
        task = asyncio.create_task(_wait_for_stop(stop_event))
        svc = AsyncCleanupService(task=task, stop_event=stop_event)

        with pytest.raises(ValueError):
            await svc.stop(timeout=bad_timeout)

        stop_event.set()
        await asyncio.wait_for(task, timeout=1)
