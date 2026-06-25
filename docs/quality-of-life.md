---
icon: material/beach
---


# Quality of Life

In practice, you don't want to sling raw dictionaries around your codebase and remember to pass a *span_name* at every call site.
Wrap [`PostgresCache`][psycache.PostgresCache] in your own class to store and retrieve structured data instead:

```python
from dataclasses import dataclass
from typing import Self

from sqlalchemy import Engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


@dataclass
class UserScore:
    name: str
    score: int


class UserCache:
    @classmethod
    def from_engine(cls, engine: Engine, *, ttl: int = 300) -> Self:
        return cls(PostgresCache(SQLAlchemyCachePool(engine)), ttl)

    def __init__(self, cache: PostgresCache, ttl: int) -> None:
        self._raw_cache = cache
        self._ttl = ttl

    def look_up_user(self, user_name: str) -> UserScore | None:
        data = self._raw_cache.get_raw(
            f"user:{user_name}",
            span_name="look up user score",
        )
        if data is None:
            return None

        return UserScore(name=user_name, score=data["score"])

    def store_user(self, user: UserScore) -> None:
        self._raw_cache.put_raw(
            f"user:{user.name}",
            {"score": user.score},
            ttl=self._ttl,
            span_name="store user score",
        )
```

Now the rest of your application deals in `UserScore` objects and never sees a cache key or a span name:

```python
from sqlalchemy import create_engine


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
users = UserCache.from_engine(engine)

users.store_user(UserScore(name="alice", score=42))
alice = users.look_up_user("alice")
# UserScore(name="alice", score=42)

engine.dispose()
```

!!! tip

    Packages like [*cattrs*](https://cattrs.org/) or [Pydantic](https://docs.pydantic.dev/) can collapse the serialization boilerplate even for more complex models.
