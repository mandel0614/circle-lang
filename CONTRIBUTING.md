# Contributing to Circle

circle-lang is an MIT-licensed research preview. Public issues and pull requests will be available when the GitHub repository is published.

For development, use Python 3.10+ and `python -m pip install -e .`, then run `python -m unittest discover -s tests -v`. The suite uses only the standard library and NumPy. Keep syntax, semantic validation, compilation, execution, and evidence reporting separate. Add behavioral tests for new supported programs and rejection tests for unsupported programs.

Do not silently relax a frozen profile. Changing a research kernel, RNG order, metric sampling window, rounding policy, initial condition, or allocation constant changes numerical semantics. Introduce a new versioned kernel when needed, document the difference, and preserve existing fixtures. Never update archived expected results to make a changed algorithm pass. Record provenance for imported code/data and explain any transformation.

Reports must distinguish compile success, completed execution, requested contract success, and certification. No contribution may infer certification from an empirical pass. Tests and already observed scenarios must not be represented as blind validation. External backend support needs backend-specific tests and evidence before being advertised.

Use issues for reproducible defects: include source, configuration, seeds, Circle/Python/NumPy versions, expected behavior, and the relevant receipt. Avoid uploading unpublished manuscripts or private research conversations.
