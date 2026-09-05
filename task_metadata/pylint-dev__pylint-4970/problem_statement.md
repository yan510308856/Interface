# `min-similarity-lines=0` should disable duplicate-code checking

Setting `min-similarity-lines` to `0` currently treats every line as duplicate code and reports errors. A zero value should disable the duplicate-code checker cleanly. The production change is in `pylint/checkers/similar.py`.
