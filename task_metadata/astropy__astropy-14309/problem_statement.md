# `identify_format` raises IndexError for a non-FITS filename

`astropy.io.registry.identify_format("write", Table, "bububu.ecsv", None, [], {})` can raise `IndexError` from the FITS identifier when the filename is not a FITS filename and no extra positional object is supplied. The production fix is localized to `astropy/io/fits/connect.py`.
