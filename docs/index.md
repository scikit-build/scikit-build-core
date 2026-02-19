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

[12:00 PM ET]: https://www.timeanddate.com/worldclock/fixedtime.html?iso=20260304T12&p1=179

<!-- prettier-ignore-end -->

<script>
function nextThirdFridayET(hour, minute) {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "numeric"
  });

  const parts = formatter.formatToParts(now);
  const year = parseInt(parts.find(p => p.type === "year").value);
  const month = parseInt(parts.find(p => p.type === "month").value) - 1;

  function thirdFriday(y, m) {
    const first = new Date(y, m, 1);
    const firstWeekday = first.getDay();
    const daysUntilFriday = (5 - firstWeekday + 7) % 7;
    const day = 1 + daysUntilFriday + 14;
    return new Date(y, m, day, hour, minute);
  }

  let candidate = thirdFriday(year, month);
  if (candidate <= now) {
    const nextMonth = new Date(year, month + 1, 1);
    candidate = thirdFriday(nextMonth.getFullYear(), nextMonth.getMonth());
  }

  return candidate;
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
