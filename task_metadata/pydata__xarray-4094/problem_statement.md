# `to_unstacked_dataset` fails for single-dimension variables

Stacking a dataset whose variables each have one dimension and then calling `to_unstacked_dataset` raises a `MergeError` about conflicting coordinate values. The production fix is localized to `xarray/core/dataarray.py` and should preserve the single-dimension roundtrip.
