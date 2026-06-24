# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Instrumentation for cache operations.
"""

from ._spans import NoopAnySpan


__all__ = ["NoopAnySpan"]
