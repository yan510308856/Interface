test_huge_range_log is failing...

### Bug report

`lib/matplotlib/tests/test_image.py::test_huge_range_log` is failing quite a few of the CI runs with a Value Error.

I cannot reproduce locally, so I assume there was a numpy change somewhere...

This test came in #18458

The failure occurs in `lib/matplotlib/image.py` while a `LogNorm` is used to normalize a masked image with a very large range and non-positive values.
