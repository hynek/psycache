---
icon: material/api
---

# API Reference

## Core

::: psycache
    options:
      members:
        - init_db
        - PostgresCache
        - AsyncPostgresCache
        - CleanupService
        - AsyncCleanupService


## Pool adapters

### *psycopg_pool*

::: psycache.psycopg_pool.PsycopgCachePool
    options:
      show_root_heading: true
      members: false
      heading_level: 4

::: psycache.psycopg_pool.AsyncPsycopgCachePool
    options:
      show_root_heading: true
      members: false
      heading_level: 4

### SQLAlchemy

::: psycache.sqlalchemy.SQLAlchemyCachePool
    options:
      show_root_heading: true
      members: false

::: psycache.sqlalchemy.AsyncSQLAlchemyCachePool
    options:
      show_root_heading: true
      members: false


## Instrumentation

::: psycache.instrumentation.prometheus.PrometheusInstrumentation
    options:
      show_root_heading: true
      members: false

::: psycache.instrumentation.sentry.SentryInstrumentation
    options:
      show_root_heading: true
      members: false
