# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import datetime as dt
import math


def _coerce_seconds(value: dt.timedelta | float, *, name: str) -> float:
    seconds = (
        value.total_seconds() if isinstance(value, dt.timedelta) else value
    )

    if not math.isfinite(seconds):
        msg = f"{name} must be finite"
        raise ValueError(msg)

    return seconds


def _coerce_stop_timeout_seconds(
    timeout: dt.timedelta | float | None,
    *,
    max_seconds: float | None = None,
) -> float | None:
    if timeout is None:
        return None

    timeout_seconds = _coerce_seconds(timeout, name="stop timeout")
    if timeout_seconds < 0:
        msg = "stop timeout must be non-negative"
        raise ValueError(msg)

    if max_seconds is not None and timeout_seconds > max_seconds:
        msg = f"stop timeout must not exceed {max_seconds}"
        raise ValueError(msg)

    return timeout_seconds


def _coerce_cleanup_interval_seconds(
    interval: dt.timedelta | float,
    *,
    max_seconds: float | None = None,
) -> float:
    interval_seconds = _coerce_seconds(interval, name="cleanup interval")
    if interval_seconds <= 0:
        msg = "cleanup interval must be positive"
        raise ValueError(msg)

    if max_seconds is not None and interval_seconds > max_seconds:
        msg = f"cleanup interval must not exceed {max_seconds}"
        raise ValueError(msg)

    return interval_seconds
