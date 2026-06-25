# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/) and this project adheres to [Calendar Versioning](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

> [!IMPORTANT]
> This package is currently in beta and looks forward to your feedback.
> The code is battle-tested, but APIs may change.

<!-- changelog follows -->

## [26.2.0](https://github.com/hynek/psycache/compare/26.1.0...26.2.0) - 2026-06-25

### Added

- Proper docs at <https://psycache.hynek.me/>.
  [#2](https://github.com/hynek/psycache/pull/2)


## Changed

- Replaced *attrs* by hand-written classes.
  Sadly, the documentation ecosystem is not ready and *dataclasses* are not fit for public APIs.
  This means *psycopg* is the **only** dependency.
  [#3](https://github.com/hynek/psycache/pull/3)


## [26.1.0](https://github.com/hynek/psycache/tree/26.1.0) - 2026-06-24

Initial release.
