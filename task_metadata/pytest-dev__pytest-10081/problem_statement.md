# Skipped unittest classes run tearDown under `--pdb`

When a `unittest.TestCase` class is marked with `unittest.skip`, running pytest with `--pdb` can still execute `tearDown()`. Class-level skip state must be considered when deciding whether to defer or suppress teardown. The production change is in `src/_pytest/unittest.py`.
