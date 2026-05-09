# Third-Party Notices

This file summarizes direct project dependencies declared in `pyproject.toml`.
License information is provided on a best-effort basis for developer
convenience and should be verified against each dependency's own distribution
metadata before redistribution.

| Dependency | Usage | License notes |
|---|---|---|
| pydantic | Runtime schema validation | Commonly distributed under MIT. |
| PyYAML | YAML loading for cases and topologies | Commonly distributed under MIT. |
| networkx | Graph/path computation | Commonly distributed under BSD-3-Clause. |
| typer | CLI framework | Commonly distributed under MIT. |
| rich | CLI output formatting | Commonly distributed under MIT. |
| pytest | Development/test dependency | Commonly distributed under MIT. |
| openai | Optional LLM provider extra | Check the official package metadata for current license terms. |
| streamlit | Optional developer UI extra | Check the official package metadata for current license terms. |

Optional dependencies are not required for the default offline/mock workflow.
