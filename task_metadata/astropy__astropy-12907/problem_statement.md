# Nested CompoundModels have an incorrect separability matrix

Astropy's `separability_matrix` does not compute separability correctly for nested `CompoundModel` expressions. The production fix is localized to the model-composition implementation in `astropy/modeling/separable.py`.
