# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import secrets

import pytest
import sentry_sdk

from sentry_sdk.transport import Transport

from psycache import PostgresCache
from psycache.instrumentation.sentry import SentryInstrumentation


class CapturingTransport(Transport):
    """
    Keep Sentry envelopes in memory instead of sending them.
    """

    def __init__(self) -> None:
        super().__init__()
        self.envelopes = []

    def capture_envelope(self, envelope):
        self.envelopes.append(envelope)

    def spans(self):
        """
        Flush the client and return all sent spans by name, with plain
        attribute values.
        """
        sentry_sdk.flush()

        return {
            span["name"]: {
                **span,
                "attributes": {
                    key: attribute["value"]
                    for key, attribute in span["attributes"].items()
                },
            }
            for envelope in self.envelopes
            for item in envelope.items
            if item.type == "span"
            for span in item.payload.json["items"]
        }


@pytest.fixture(name="sentry")
def _sentry():
    """
    Install a real Sentry client that sends to memory, and run the test in a
    fresh isolation scope.
    """
    transport = CapturingTransport()
    sentry_sdk.init(
        transport=transport,
        traces_sample_rate=1.0,
        default_integrations=False,
    )

    with sentry_sdk.isolation_scope():
        yield transport

    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


@pytest.fixture(name="sentry_cache")
def _sentry_cache(raw_pool):
    return PostgresCache(raw_pool, instrumentations=(SentryInstrumentation(),))


@pytest.fixture(name="key")
def _key():
    return secrets.token_urlsafe()


def test_put_and_get_hit(sentry_cache, sentry, key):
    """
    A put and a get that hits record cache spans with the key, the item size,
    and the hit.
    """
    sentry_cache.put_raw(key, {"foo": "bar"}, 60)
    sentry_cache.get_raw(key)

    spans = sentry.spans()

    assert {"psycache put", "psycache get"} == spans.keys()

    put = spans["psycache put"]["attributes"]
    get = spans["psycache get"]["attributes"]

    assert "cache.put" == put["sentry.op"]
    assert [key] == put["cache.key"]
    assert put["cache.item_size"] > 0
    assert put["cache.success"] is True

    assert "cache.get" == get["sentry.op"]
    assert [key] == get["cache.key"]
    assert get["cache.hit"] is True
    assert put["cache.item_size"] == get["cache.item_size"]
    assert get["cache.success"] is True


def test_get_miss(sentry_cache, sentry, key):
    """
    A get that misses records the miss and no item size.
    """
    assert None is sentry_cache.get_raw(key)

    get = sentry.spans()["psycache get"]["attributes"]

    assert "cache.get" == get["sentry.op"]
    assert [key] == get["cache.key"]
    assert get["cache.hit"] is False
    assert "cache.item_size" not in get
    assert get["cache.success"] is True


def test_custom_span_names(sentry_cache, sentry, key):
    """
    The span_name arguments of put_raw and get_raw become the span names.
    """
    sentry_cache.put_raw(key, {}, 60, span_name="my put")
    sentry_cache.get_raw(key, span_name="my get")

    assert {"my put", "my get"} == sentry.spans().keys()


def test_remove(sentry_cache, sentry, key):
    """
    A remove records a cache.remove span with the key.
    """
    sentry_cache.remove(key)

    remove = sentry.spans()["psycache remove"]["attributes"]

    assert "cache.remove" == remove["sentry.op"]
    assert [key] == remove["cache.key"]
    assert remove["cache.success"] is True


def test_flush(sentry_cache, sentry):
    """
    A flush records a cache.flush span with the number of flushed entries.
    """
    sentry_cache.put_raw("a", {}, 60)
    sentry_cache.put_raw("b", {}, 60)

    sentry_cache.flush()

    flush = sentry.spans()["psycache flush"]["attributes"]

    assert "cache.flush" == flush["sentry.op"]
    assert 2 == flush["cache.num_flushed"]


def test_cleanup_records_no_span(sentry_cache, sentry):
    """
    Cleaning up expired entries is not instrumented.
    """
    sentry_cache.cleanup_expired()

    assert {} == sentry.spans()
