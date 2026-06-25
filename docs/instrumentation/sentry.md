# Sentry

[`SentryInstrumentation`][psycache.instrumentation.sentry.SentryInstrumentation] creates [Sentry cache spans](https://docs.sentry.io/platforms/python/tracing/instrumentation/custom-instrumentation/caches-module/) for `get`, `put`, `remove`, and `flush` operations, recording `cache.hit`, `cache.item_size`, and `cache.key` data.
These show up in Sentry's [Cache Monitoring](https://docs.sentry.io/product/insights/caches/) views.

The *span_name* argument to [`get_raw()`][psycache.PostgresCache.get_raw] and [`put_raw()`][psycache.PostgresCache.put_raw] is used as the Sentry span name (it defaults to `"psycache get"` / `"psycache put"`).

It requires the `sentry` extra:

```console
$ uv pip install "psycache[sentry]"
```
