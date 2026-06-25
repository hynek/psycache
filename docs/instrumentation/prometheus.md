# Prometheus

[`PrometheusInstrumentation`][psycache.instrumentation.prometheus.PrometheusInstrumentation] exports metrics through the official [*prometheus-client*](https://github.com/prometheus/client_python) library.

It requires the `prometheus` extra:

```console
$ uv pip install "psycache[prometheus]"
```


## Exported metrics

| Metric | Type | Labels | Description |
| --- | --- | --- | --- |
| `psycache_hits_total` | Counter | `span_name` | Cache hits |
| `psycache_misses_total` | Counter | `span_name` | Cache misses |
| `psycache_get_duration_seconds` | Histogram | `span_name` | Get operation latency |
| `psycache_put_duration_seconds` | Histogram | `span_name` | Put operation latency |
| `psycache_remove_duration_seconds` | Histogram | | Remove operation latency |
| `psycache_flush_duration_seconds` | Histogram | | Flush operation latency |
| `psycache_item_size_bytes` | Histogram | `span_name` | Size of cache items (from `pg_column_size`) |
| `psycache_flushed_entries` | Histogram | | Entries removed per flush |
| `psycache_cleanup_last_run_timestamp_seconds` | Gauge | | Timestamp of last cleanup |
| `psycache_cleanup_deleted_entries` | Gauge | | Entries removed in last cleanup |

The `span_name` label is taken from the *span_name* argument to [`get_raw()`][psycache.PostgresCache.get_raw] and [`put_raw()`][psycache.PostgresCache.put_raw].
It defaults to `""` when not provided.
