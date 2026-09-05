# Nominal scales should behave like categorical scales

Seaborn `Nominal` scales should use categorical-style limits, suppress the default grid, and invert the y-axis. The production implementation is localized to the plot scale setup/finalization code in `seaborn/_core/plot.py`.
