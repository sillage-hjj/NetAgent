# NetAgent Lab

NetAgent Lab is an independent Python 3.11+ research prototype for network
observability, deterministic incident investigation, simulated telemetry, and
evidence-grounded agent workflows.

It currently has four implemented capability areas:

1. Offline RCA over synthetic incident cases.
2. Configurable simulated network state and deterministic monitoring.
3. Optional LLM-capable agent system with the mock provider enabled by default.
4. OpenAI provider hardening, a read-only developer UI, and evidence relevance evals.

NetAgent Lab is independent and unaffiliated with NetFabric AG. Third-party
names, if mentioned, are used only for descriptive research context. This
repository does not contain vendor source code, proprietary network data,
logos, screenshots, or confidential material.

By default, the project runs offline. It does not contact real devices, does
not execute real-world remediation, and does not call external LLM APIs unless
the OpenAI provider is explicitly selected and configured.

## Quickstart

Install the project for local development:

```bash
pip install -e ".[dev]"
```

Run the original offline RCA demo:

```bash
netagent demo --case all
```

Run a simulated link-failure scenario:

```bash
netagent sim scenario --name link_failure
```

Run the mock agent against a built-in scenario:

```bash
netagent agent demo --scenario link_failure --provider mock
```

Run deterministic mock-agent evals:

```bash
netagent agent eval --provider mock --format json
```

The legacy CLI alias is still available:

```bash
nfmini --help
```

The package can also be invoked as a module:

```bash
python -m netagent_lab.cli --help
```

## Installation

Default offline development install:

```bash
pip install -e ".[dev]"
```

Optional OpenAI provider support:

```bash
pip install -e ".[dev,llm]"
```

Optional Streamlit developer UI:

```bash
pip install -e ".[dev,ui]"
```

Install everything optional:

```bash
pip install -e ".[dev,llm,ui]"
```

Normal tests and mock-agent workflows do not require OpenAI credentials.

## Capability Phases

### Phase 1: Offline RCA MVP

Phase 1 loads synthetic cases from `data/cases/` into SQLite, parses logs,
infers paths, checks ACLs, inspects metrics, and renders evidence-grounded RCA
reports.

Implemented case directories:

- `data/cases/link_down/`
- `data/cases/acl_block/`
- `data/cases/performance_degradation/`

Useful commands:

```bash
netagent list-cases
netagent demo --case link_down
netagent demo --case acl_block
netagent demo --case performance_degradation
netagent demo --case all
```

Step-by-step RCA flow:

```bash
netagent init-db --case acl_block --db ./nfmini.db
netagent parse-logs --db ./nfmini.db
netagent investigate --db ./nfmini.db --ticket T-001 --format markdown
```

### Phase 2: Simulated Network and Monitoring

Phase 2 adds a configurable simulated network. It is a metadata/state simulator,
not a packet-level simulator. It models topology, mutable simulated state,
logical ticks, event injection, telemetry, collectors, alerts, snapshots,
snapshot diffs, and JSON/JSONL exports.

Implemented topology files:

- `data/topologies/simple_branch_app.yaml`
- `data/topologies/ring_with_backup.yaml`
- `data/topologies/spine_leaf_mini.yaml`

Initialize and inspect a simulation database:

```bash
netagent sim list-topologies
netagent sim validate --topology data/topologies/simple_branch_app.yaml
netagent sim init --topology data/topologies/simple_branch_app.yaml --db ./sim.db
netagent sim state --db ./sim.db
```

Run monitoring and inspect state changes:

```bash
netagent sim monitor --db ./sim.db --once
netagent sim inject --db ./sim.db --event link_down --target link_r1_r2 --param reason=fiber_cut
netagent sim tick --db ./sim.db --steps 1
netagent sim monitor --db ./sim.db --once
netagent sim diff --db ./sim.db --from latest-1 --to latest
```

Export current context:

```bash
netagent sim export --db ./sim.db --format json
netagent sim export --db ./sim.db --format latest-snapshot
netagent sim export --db ./sim.db --format events-jsonl
netagent sim export --db ./sim.db --format telemetry-jsonl
netagent sim export --db ./sim.db --format llm-context
```

`llm-context` is only a budgeted, redacted export shape for future/optional
agent use. It does not call an LLM.

Built-in scenarios:

```bash
netagent sim scenario --name link_failure
netagent sim scenario --name congestion
netagent sim scenario --name route_withdrawal
```

### Phase 3: Optional LLM-Capable Agent

Phase 3 adds an agent framework. The default provider is `mock`, so normal
runs are deterministic and offline. The optional OpenAI provider is only used
when explicitly selected.

The agent can:

- accept natural-language network questions
- build budgeted/redacted investigation context
- call registered tools only
- trigger read-only monitoring cycles
- inspect alerts, reachability, paths, health, snapshots, events, and telemetry
- produce schema-validated, evidence-grounded reports
- persist sessions, runs, tool traces, usage, errors, and approvals

The agent cannot directly query SQLite, run shell commands, contact real
network devices, perform path/reachability reasoning itself, or execute
real-world remediation.

Inspect configuration and registered tools:

```bash
netagent agent config
netagent agent tools
```

Run mock demos:

```bash
netagent agent demo --scenario link_failure --provider mock
netagent agent demo --scenario congestion --provider mock
netagent agent demo --scenario route_withdrawal --provider mock
```

Ask questions against an existing simulation DB:

```bash
netagent agent ask --db ./sim.db --provider mock --question "Why is App-B unreachable from Zurich?"
netagent agent investigate --db ./sim.db --source client_zurich --service app_b --provider mock
netagent agent monitor-summary --db ./sim.db --provider mock
```

Inspect persisted runs and traces:

```bash
netagent agent runs --db ./sim.db
netagent agent trace --db ./sim.db --run RUN_ID
```

Approval queue commands for simulated mutation requests:

```bash
netagent agent approvals list --db ./sim.db
netagent agent approvals approve APPROVAL_ID --db ./sim.db
netagent agent approvals reject APPROVAL_ID --db ./sim.db
```

### Phase 4: OpenAI Hardening, UI, and Evidence Relevance

Phase 4 hardens the OpenAI provider, adds a read-only Streamlit developer UI,
and extends eval scoring from "evidence exists" to "evidence is relevant,
specific, recent, and causally aligned."

Run evidence relevance evals:

```bash
netagent agent eval --provider mock --format json
netagent agent eval --provider mock --format text
```

Launch the UI:

```bash
pip install -e ".[dev,ui]"
netagent ui --db ./sim.db
```

Equivalent direct Streamlit command:

```bash
streamlit run src/netagent_lab/ui/streamlit_app.py -- --db ./sim.db
```

The UI is read-only in the current implementation.

## Project Layout

Generated files such as `sim.db`, `__pycache__/`, `.pytest_cache/`, and
`*.egg-info/` may appear after local runs, but they are ignored and are not
source files.

| Path | Purpose |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, pytest config, CLI entry points. |
| `.github/workflows/ci.yml` | CI workflow: compile, install, and run non-live tests. |
| `.gitignore` | Ignore generated caches, local DBs, env files, and build artifacts. |
| `LICENSE`, `NOTICE`, `DISCLAIMER.md`, `THIRD_PARTY_NOTICES.md` | Open-source license, notices, independence disclaimer, dependency notices. |
| `docs/research_notes.md` | Neutral research note on AI-assisted network observability patterns. |
| `data/cases/` | Synthetic Phase 1 RCA data: topology, ACLs, logs, metrics, tickets. |
| `data/topologies/` | Synthetic Phase 2 simulation topology YAML files. |
| `src/netagent_lab/` | Main Python package. |
| `src/netagent_lab/cli.py` | Root Typer CLI, Phase 1 commands, UI launcher, sub-app registration. |
| `src/netagent_lab/cli_sim.py` | `netagent sim ...` commands. |
| `src/netagent_lab/cli_agent.py` | `netagent agent ...` commands. |
| `src/netagent_lab/db.py` | SQLite schema and persistence helpers for RCA, simulation, monitoring, and agent state. |
| `src/netagent_lab/schemas.py` | Phase 1 Pydantic schemas. |
| `src/netagent_lab/seed_loader.py` | Synthetic case loader. |
| `src/netagent_lab/log_parser.py` | Deterministic log parser. |
| `src/netagent_lab/topology_model.py` | Phase 1 NetworkX path inference. |
| `src/netagent_lab/acl_checker.py` | Deterministic ACL checker. |
| `src/netagent_lab/metrics.py` | Phase 1 metric lookup/anomaly helpers. |
| `src/netagent_lab/tools.py` | Phase 1 read-only tool facade. |
| `src/netagent_lab/investigator.py` | Rule-based Phase 1 investigator. |
| `src/netagent_lab/report.py` | Phase 1 report rendering. |
| `src/netagent_lab/sim/` | Simulation schemas, topology loader, state store, event engine, scenarios, telemetry, snapshots, exports, and pathing. |
| `src/netagent_lab/ingestion/` | Read-only collectors over simulated state. |
| `src/netagent_lab/normalization/` | Normalized inventory/observation schemas and normalizers. |
| `src/netagent_lab/knowledge/` | KnowledgeBase and store wrappers for topology, state, events, telemetry, and snapshots. |
| `src/netagent_lab/reasoning/` | Deterministic pathing, reachability, health, alerts, and snapshot diffs. |
| `src/netagent_lab/orchestration/` | Monitoring workflow and investigation-context builder. |
| `src/netagent_lab/controls/` | Guardrails, evidence helpers, redaction, and data budgets. |
| `src/netagent_lab/monitoring/` | Compatibility wrappers for monitoring collectors, alerts, diffs, and monitor runs. |
| `src/netagent_lab/llm/` | LLM config, provider protocol, mock client, OpenAI client, messages, usage, structured output helpers. |
| `src/netagent_lab/agent/` | Agent schemas, prompts, tool registry/executor, loop, validation, approvals, run/session stores, rendering. |
| `src/netagent_lab/agent_tools/` | Registered agent tool wrappers over the six-layer architecture. |
| `src/netagent_lab/evals/` | Mock-agent scenarios, rubrics, expected evidence, and evidence relevance scoring. |
| `src/netagent_lab/ui/` | Optional read-only Streamlit developer UI. |
| `tests/` | Pytest suite covering RCA, simulation, six-layer monitoring, agent, OpenAI contract, UI data access, and evals. |

## Architecture

### Six-Layer Monitoring Architecture

```text
SimulationEngine current state
  -> ingestion collectors
  -> normalized observations
  -> KnowledgeBase update
  -> deterministic reasoning
  -> monitoring workflow result
  -> budgeted / redacted / evidence-grounded export
  -> optional agent tools
```

Layers:

1. Data ingestion: read-only collectors.
2. Data normalization: stable observation schemas.
3. Network knowledge base: persisted topology, state, events, telemetry, snapshots, and evidence lookup.
4. Deterministic reasoning: pathing, reachability, health, alerts, and diffs.
5. Workflow / agent orchestration: monitoring cycles, investigation context, agent runs.
6. Safety and cost control: guardrails, redaction, evidence validation, data budgets, approvals.

Phase 2 uses the six-layer architecture without LLM calls. Phase 3 places the
agent on top of it. The agent consumes registered tools and budgeted context;
it does not bypass deterministic layers.

### Agent Flow

```text
User question
  -> budgeted / redacted investigation context
  -> LLM or mock-provider planning and tool selection
  -> registered AgentTool calls only
  -> deterministic six-layer tools
  -> evidence validation
  -> structured AgentReport
  -> session / run / tool trace persistence
```

The mock provider follows deterministic scripts/templates. The optional OpenAI
provider uses the same tool contracts and report validation path.

## CLI Reference

### Base RCA Commands

| Command | Purpose |
|---|---|
| `netagent --help` | Show root CLI help. |
| `netagent --version` | Show package version. |
| `netagent list-cases` | List synthetic incident cases. |
| `netagent init-db --case CASE --db PATH` | Create a SQLite DB and load a Phase 1 case. |
| `netagent parse-logs --db PATH` | Parse raw logs into structured events. |
| `netagent investigate --db PATH --ticket T-001 --format markdown` | Run rule-based RCA. |
| `netagent demo --case CASE` | Run full Phase 1 load, parse, investigate flow. |
| `nfmini ...` | Backward-compatible alias for `netagent ...`. |

### Simulation Commands

| Command | Purpose |
|---|---|
| `netagent sim list-topologies` | List topology YAML files. |
| `netagent sim validate --topology PATH` | Validate topology YAML. |
| `netagent sim init --topology PATH --db PATH` | Initialize a simulation DB. |
| `netagent sim state --db PATH` | Print current simulation summary. |
| `netagent sim tick --db PATH --steps N` | Advance logical ticks. |
| `netagent sim inject --db PATH --event EVENT --target TARGET --param KEY=VALUE` | Inject a simulated event. |
| `netagent sim monitor --db PATH --once` | Run one monitoring cycle. |
| `netagent sim snapshot --db PATH` | Create a monitoring snapshot. |
| `netagent sim snapshots --db PATH` | List snapshots. |
| `netagent sim diff --db PATH --from latest-1 --to latest` | Diff snapshots. |
| `netagent sim export --db PATH --format FORMAT` | Export current state, latest snapshot, events JSONL, telemetry JSONL, or LLM context. |
| `netagent sim scenario --name NAME` | Run a built-in scenario. |

### Agent Commands

| Command | Purpose |
|---|---|
| `netagent agent config` | Print redacted agent config. |
| `netagent agent tools` | List registered tools. |
| `netagent agent ask --db PATH --question TEXT --provider mock` | Ask a one-shot question. |
| `netagent agent investigate --db PATH --source DEVICE --service SERVICE --provider mock` | Run a focused service investigation. |
| `netagent agent monitor-summary --db PATH --provider mock` | Summarize alerts and network risk. |
| `netagent agent chat --db PATH --provider mock` | Simple interactive chat loop. |
| `netagent agent runs --db PATH` | List agent runs. |
| `netagent agent trace --db PATH --run RUN_ID` | Show tool calls for a run. |
| `netagent agent approvals list --db PATH` | List pending simulated-mutation approvals. |
| `netagent agent approvals approve APPROVAL_ID --db PATH` | Approve a pending simulated mutation request. |
| `netagent agent approvals reject APPROVAL_ID --db PATH` | Reject a pending simulated mutation request. |
| `netagent agent demo --scenario NAME --provider mock` | Run a built-in mock-agent scenario. |
| `netagent agent eval --provider mock --format json` | Run deterministic mock evals. |

### UI Command

| Command | Purpose |
|---|---|
| `netagent ui --db PATH` | Launch the optional read-only Streamlit UI. |

## Configuration

Environment variables used by the optional agent/LLM layer:

| Variable | Purpose |
|---|---|
| `NFM_AGENT_PROVIDER` | `mock` or `openai`; default is `mock`. |
| `OPENAI_API_KEY` | Required only when using `--provider openai` or `NFM_AGENT_PROVIDER=openai`. |
| `OPENAI_MODEL` | Optional model override. If unset, the code uses the default in `src/netagent_lab/llm/config.py`. |
| `NFM_AGENT_MAX_TOOL_CALLS` | Max tool calls per agent run. |
| `NFM_AGENT_MAX_CONTEXT_EVENTS` | Event count budget for investigation context. |
| `NFM_AGENT_MAX_CONTEXT_TELEMETRY` | Telemetry count budget for investigation context. |
| `NFM_AGENT_REQUIRE_EVIDENCE` | Whether final reports require evidence. |
| `NFM_AGENT_ALLOW_SIM_MUTATION` | Enables approval-gated simulated mutation tools; default is false. |

API keys are not stored in SQLite. Do not commit `.env` files or secrets.
`netagent agent config` reports redacted diagnostics only.

### PowerShell Example

Session-only variables:

```powershell
$env:NFM_AGENT_PROVIDER = "openai"
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "your-model-name"
```

Persistent user-level variables:

```powershell
[Environment]::SetEnvironmentVariable("NFM_AGENT_PROVIDER", "openai", "User")
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("OPENAI_MODEL", "your-model-name", "User")
```

Open a new PowerShell after setting persistent variables.

## Optional OpenAI Provider

The OpenAI provider is optional and uses the OpenAI Responses API with
registered function tools and structured `AgentReport` output. The model cannot
directly access SQLite or simulator internals.

```bash
pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model-name"
netagent agent ask --db ./sim.db --provider openai --question "Why is App-B unreachable from Zurich?"
```

Live OpenAI tests are opt-in and should not run in normal CI.

## Lightweight Developer UI

The optional Streamlit UI is a local developer console for inspecting:

- topology name, current tick, counts, active alerts, latest snapshot
- devices, links, services, probes, and full link metadata
- snapshots and diffs
- agent runs and final reports
- tool traces and tool outputs
- report evidence references
- mock eval/rubric results

Install and launch:

```bash
pip install -e ".[dev,ui]"
netagent ui --db ./sim.db
```

Direct Streamlit launch:

```bash
streamlit run src/netagent_lab/ui/streamlit_app.py -- --db ./sim.db
```

The current UI is read-only. It does not inject events or call OpenAI by
default.

## Evidence Model

Reports and tool outputs use evidence references. Common evidence IDs include:

- ticket IDs
- raw log IDs
- parsed event IDs
- ACL rule IDs
- metric IDs
- path result IDs
- simulation event IDs
- telemetry sample IDs
- snapshot IDs
- alert IDs
- tool trace IDs

Every major claim in an RCA or agent report should cite evidence. Unsupported
claims must be labeled as unsupported. Deterministic tools remain authoritative
for network facts.

## Evidence Relevance Evals

Evidence validation checks whether cited IDs exist. Evidence relevance evals
also score whether the cited evidence is:

- relevant to the expected incident type
- specific to the affected object
- recent enough for the incident/snapshot window
- causally aligned with the reported hypothesis

Run:

```bash
netagent agent eval --provider mock --format json
netagent agent eval --provider mock --format text
```

## Safety, Guardrails, and Approvals

By default, NetAgent Lab does not:

- contact real devices
- use SSH, SNMP, NETCONF, RESTCONF, gNMI, or production CLIs
- execute shell commands from model output
- execute real-world remediation
- give the model direct SQLite access
- call external LLM APIs unless OpenAI is explicitly selected and configured

Simulation mutation is limited to internal simulated state and must go through
the simulation engine. Agent mutation tools are disabled by default and are
approval-gated when enabled. No real remediation is implemented.

## Data Budgeting and Redaction

Agent context and LLM-context exports are budgeted and redacted. Raw payloads
are excluded by default where applicable. Event, telemetry, alert, and link
lists may be truncated. Sensitive fields such as management IPs, passwords,
tokens, secrets, and community strings are redacted.

## Testing

Run local non-live verification:

```bash
python -m compileall src
pytest -q -m "not live_openai"
```

Optional live OpenAI smoke tests:

```bash
export OPENAI_API_KEY="..."
RUN_LIVE_OPENAI_TESTS=1 pytest -q -m live_openai
```

Useful smoke commands:

```bash
netagent --help
netagent demo --case all
netagent sim scenario --name link_failure
netagent sim scenario --name congestion
netagent sim scenario --name route_withdrawal
netagent agent demo --scenario link_failure --provider mock
netagent agent eval --provider mock --format json
nfmini --help
```

CI runs compile, install, and non-live tests only.

## Legal and Compliance Notes

See:

- `LICENSE`
- `NOTICE`
- `DISCLAIMER.md`
- `THIRD_PARTY_NOTICES.md`
- `docs/research_notes.md`

NetAgent Lab is an independent educational/research prototype. It is not
affiliated with, endorsed by, sponsored by, or derived from NetFabric AG or any
other vendor.

## Limitations

- Synthetic and simulated data only unless future integrations are added.
- No packet-level simulation.
- No real control-plane lab.
- No real device polling.
- No real remediation.
- Simple deterministic thresholds.
- Limited parser coverage.
- Mock provider uses deterministic scripts/templates.
- OpenAI provider depends on the optional official SDK and configured key.
- Approval-gated mutation applies only to simulated state.
- Evidence validation checks references and deterministic tool outputs, not all possible semantic truth beyond those tools.

## Roadmap

- Web UI polish for simulation, monitoring, and agent traces.
- Optional Containerlab + FRRouting protocol lab.
- Optional Batfish integration for configuration and reachability analysis.
- LLM-assisted log parser generation behind validation tests.
- Richer event correlation and root-cause ranking.
- Benchmark datasets and eval reports.
- Long multi-turn memory summarization.
- Richer telemetry pipeline and visualization.
