# Scikit-build-core

Scikit-build-core is a complete ground-up rewrite of scikit-build on top of
modern packaging APIs. It provides a bridge between CMake and the Python build
system, allowing you to make Python modules with CMake.

:::{admonition} Scikit-build community meeting

We have a public Scikit-build community meeting every month!
[Join us on Google Meet](https://meet.google.com/tgz-umhu-onf) on the third
Friday of every month at [12:00 PM ET][] (<span id="meeting-time"></span> your
time). Some of our past meeting minutes are
[available here](https://github.com/orgs/scikit-build/discussions/categories/community-meeting-notes).

:::

## Features

```{include} ../README.md
:start-after: <!-- SPHINX-START -->
```

## Contents

```{toctree}
:maxdepth: 2
:titlesonly:
:caption: Guide

guide/getting_started
guide/cmakelists
guide/dynamic_link
guide/crosscompile
guide/migration_guide
guide/build
guide/faqs
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: Configuration

configuration/index
configuration/overrides
configuration/dynamic
configuration/formatted
configuration/search_paths
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: Plugins

plugins/setuptools
plugins/hatchling
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: About project

about/projects
about/changelog
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: API docs

api/scikit_build_core
schema
reference/configs
reference/cli
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`

Generated using scikit-build-core {{ version }}.

<!-- prettier-ignore-start -->

[12:00 PM ET]: https://howlonghowmany.com/my-time/eastern-time/12-pm

<!-- prettier-ignore-end -->

<script>
function getThirdFriday(year, month) {
  const first = new Date(year, month, 1);
  const firstWeekday = first.getDay(); // 0=Sun ... 6=Sat
  const daysUntilFriday = (5 - firstWeekday + 7) % 7;
  return 1 + daysUntilFriday + 14;
}

const nyDateFormat = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "2-digit",
  day: "2-digit"
});

const nyOffsetFormat = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  timeZoneName: "shortOffset"
});

function nyOffsetMinutes(date) {
  const offset = nyOffsetFormat
    .formatToParts(date)
    .find((part) => part.type === "timeZoneName").value;

  if (offset === "GMT") {
    return 0;
  }

  const match = offset.match(/^GMT([+-])(\d{1,2})(?::?(\d{2}))?$/);
  if (!match) {
    throw new Error(`Unexpected time zone offset: ${offset}`);
  }

  const sign = match[1] === "+" ? 1 : -1;
  const hours = Number(match[2]);
  const minutes = Number(match[3] || 0);
  return sign * (hours * 60 + minutes);
}

function newYorkTimeToDate(year, month, day, hour, minute) {
  const localAsUTC = Date.UTC(year, month, day, hour, minute, 0);
  const offsetMinutes = nyOffsetMinutes(new Date(localAsUTC));
  return new Date(localAsUTC - offsetMinutes * 60_000);
}

function nextThirdFridayET(hour, minute) {
  const now = new Date();
  const nyNow = Object.fromEntries(
    nyDateFormat
      .formatToParts(now)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value])
  );

  let year = Number(nyNow.year);
  let month = Number(nyNow.month) - 1;

  function buildMeeting(y, m) {
    const day = getThirdFriday(y, m);
    return newYorkTimeToDate(y, m, day, hour, minute);
  }

  let meeting = buildMeeting(year, month);

  if (meeting <= now) {
    month += 1;
    if (month === 12) {
      month = 0;
      year += 1;
    }
    meeting = buildMeeting(year, month);
  }

  return meeting;
}

const meeting = nextThirdFridayET(12, 0);

document.getElementById("meeting-time").textContent =
  meeting.toLocaleString([], {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short"
  });
</script>
