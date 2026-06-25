# Instrumentation

*psycache* has pluggable instrumentation for observability.
Pass one or more providers to the `instrumentations` parameter of [`PostgresCache`][psycache.PostgresCache] (or [`AsyncPostgresCache`][psycache.AsyncPostgresCache]) and every cache operation is reported to them:

```python
from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.instrumentation.prometheus import PrometheusInstrumentation
from psycache.instrumentation.sentry import SentryInstrumentation
from psycache.sqlalchemy import SQLAlchemyCachePool


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(
    SQLAlchemyCachePool(engine),
    instrumentations=(
        SentryInstrumentation(),
        PrometheusInstrumentation(),
    ),
)

engine.dispose()
```

Two providers ship with *psycache*:

- [Prometheus](prometheus.md): counters, histograms, and gauges for metrics scraping.
- [Sentry](sentry.md): cache spans for distributed tracing.

You can also write your own; see [Custom Instrumentation](custom.md).
