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
function getThirdFriday(year, month) {
  const first = new Date(year, month, 1);
  const firstWeekday = first.getDay(); // 0=Sun ... 6=Sat
  const daysUntilFriday = (5 - firstWeekday + 7) % 7;
  return 1 + daysUntilFriday + 14;
}

function nextThirdFridayET(hour, minute) {
  const now = new Date();

  // Get current date in New York
  const nyNow = new Date(
    now.toLocaleString("en-US", { timeZone: "America/New_York" })
  );

  let year = nyNow.getFullYear();
  let month = nyNow.getMonth();

  function buildMeeting(y, m) {
    const day = getThirdFriday(y, m);

    // Construct a string interpreted in New York time
    const localString =
      `${y}-${String(m + 1).padStart(2, "0")}-${String(day).padStart(2, "0")} ` +
      `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00`;

    // Parse as New York time
    const parts = new Date(
      localString + " America/New_York"
    );

    return parts;
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
