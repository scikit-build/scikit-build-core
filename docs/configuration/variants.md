# Building wheel variants

```{versionadded} 1.0

```

```{warning}
This is an early preview of [PEP 817][] wheel variant support. The interface may
change, and it must be opted into with `experimental = true`.
```

Scikit-build-core can attach variant metadata to a wheel, producing a
variant-labeled filename (the label becomes the final field of the wheel name)
and a `variant.json` file inside `*.dist-info`. This lets you ship several
wheels for the same version that differ by hardware or library features (CPU
ABI, CUDA version, BLAS implementation, etc.).

Because each variant of a build needs different settings, the variant options
are **only allowed in config-settings or `[[tool.scikit-build.overrides]]`**;
they cannot be hard-coded at the top level of `pyproject.toml`. The relevant
settings are:

- `variant` / `variant-name`: variant properties in
  `namespace :: feature :: value` form (repeatable).
- `variant-label`: override the computed label used in the wheel filename.
- `null-variant`: build the null variant (mutually exclusive with the above).

When any of these are set, [`variantlib`][] is automatically injected as a build
requirement, and the experimental flag must be enabled. For example, to build a
CPU-ABI variant with `pip`:

```bash
pip wheel . \
  -Cexperimental=true \
  -Cvariant="cpu :: abi :: cp313" \
  -Cvariant-label=cpu
```

Or to enable it for everyone via an override (still keeping the per-build values
in config-settings), put the experimental flag in `pyproject.toml`:

```toml
[tool.scikit-build]
experimental = true
```

Pass `-Cvariant=...` (and friends) at build time to select which variant to
produce.

<!-- prettier-ignore-start -->

[pep 817]: https://peps.python.org/pep-0817
[`variantlib`]: https://github.com/wheelnext/variantlib

<!-- prettier-ignore-end -->
