# netfabric-mini

## Overview

`netfabric-mini` is a Python 3.11+ network observability and incident
investigation prototype. It combines synthetic offline RCA, a configurable
simulated network, deterministic monitoring, and an optional LLM-powered agent
layer.

By default, the project runs offline with deterministic tools and the mock agent
provider. Live OpenAI calls are optional and only used when explicitly
configured. No real network devices are contacted, no real remediation is
executed, and deterministic tools remain authoritative for network facts.

The project is organized around these implemented capability areas:

1. Phase 1: offline RCA over synthetic incident cases.
2. Phase 2: configurable simulated network, telemetry, monitoring, snapshots,
   diffs, alerts, and exports.
3. Phase 3: optional LLM-capable agent system with a mock provider by default
   and an optional OpenAI provider.
4. Phase 4: hardened OpenAI provider integration, a lightweight read-only
   developer UI, and evidence relevance evals.

The LLM layer, when used, is constrained by registered tools, schema validation,
evidence validation, redaction, data budgets, and guardrails.

## Capability Phases

### Phase 1: Offline RCA MVP

Phase 1 loads small synthetic incident cases into SQLite and runs a deterministic
RCA workflow. It includes:

- synthetic incident cases under `data/cases/`
- SQLite case loading
- deterministic log parsing
- NetworkX path inference
- ACL checking
- metric anomaly checks
- evidence-grounded Markdown and text RCA reports

Run the offline demos:

```bash
nfmini list-cases
nfmini demo --case link_down
nfmini demo --case acl_block
nfmini demo --case performance_degradation
nfmini demo --case all
```

Run the Phase 1 flow step by step:

```bash
nfmini init-db --case acl_block --db ./nfmini.db
nfmini parse-logs --db ./nfmini.db
nfmini investigate --db ./nfmini.db --ticket T-001 --format markdown
```

The module entry point also works:

```bash
python -m netfabric_mini.cli demo --case acl_block
```

Built-in synthetic cases:

| Case | Purpose |
|---|---|
| `link_down` | Zurich users cannot access App-B because a required link is down. |
| `acl_block` | The physical path exists, but HTTPS traffic is denied by an ACL on `r3`. |
| `performance_degradation` | The path and ACL allow traffic, but metrics/logs show degradation. |

### Phase 2: Configurable Simulated Network and Monitoring

Phase 2 adds a deterministic simulated network digital twin. The simulator
mutates only its own SQLite-backed simulated state and never contacts real
routers, switches, controllers, or external systems.

It includes:

- topology YAML files under `data/topologies/`
- mutable simulated device, interface, link, service, probe, and route-block state
- explicit logical ticks
- event injection for failures and degradations
- read-only collectors
- telemetry samples
- deterministic alerts
- full-state snapshots
- snapshot diffs
- JSON and JSONL exports
- future-agent context export

Initialize and inspect a simulated network:

```bash
nfmini sim list-topologies
nfmini sim validate --topology data/topologies/simple_branch_app.yaml
nfmini sim init --topology data/topologies/simple_branch_app.yaml --db ./sim.db
nfmini sim state --db ./sim.db
nfmini sim monitor --db ./sim.db --once
```

Inject a simulated incident and compare snapshots:

```bash
nfmini sim inject --db ./sim.db --event link_down --target link_r1_r2 --param reason=fiber_cut
nfmini sim tick --db ./sim.db --steps 1
nfmini sim monitor --db ./sim.db --once
nfmini sim diff --db ./sim.db --from latest-1 --to latest
```

Export state and telemetry:

```bash
nfmini sim export --db ./sim.db --format json
nfmini sim export --db ./sim.db --format latest-snapshot
nfmini sim export --db ./sim.db --format events-jsonl
nfmini sim export --db ./sim.db --format telemetry-jsonl
nfmini sim export --db ./sim.db --format llm-context
```

`llm-context` is only a budgeted, redacted export format for future or optional
agent use. It does not call an LLM.

Run built-in simulation scenarios:

```bash
nfmini sim scenario --name link_failure
nfmini sim scenario --name congestion
nfmini sim scenario --name route_withdrawal
```

Built-in topology files:

| Topology | Purpose |
|---|---|
| `simple_branch_app.yaml` | Branch-to-app topology with primary and backup paths. |
| `ring_with_backup.yaml` | Ring-style topology for failover behavior. |
| `spine_leaf_mini.yaml` | Small spine/leaf-style topology. |

### Phase 3: LLM Agent System

Phase 3 adds an optional LLM-capable agent on top of the deterministic six-layer
architecture. The default provider is `mock`, so normal usage and tests run
offline. The OpenAI provider is optional.

The agent can:

- accept natural-language network questions
- build budgeted and redacted investigation context
- select registered tools
- trigger read-only monitoring cycles
- inspect alerts, reachability, paths, health, snapshots, events, and telemetry
- produce schema-validated, evidence-grounded reports
- persist sessions, runs, tool traces, usage, errors, and approvals

The agent does not directly query SQLite, directly mutate simulated state,
perform path or reachability reasoning itself, execute shell commands, or
perform real-world remediation. It must use deterministic tools for network
facts.

Mock provider examples:

```bash
nfmini agent config
nfmini agent tools
nfmini agent demo --scenario link_failure --provider mock
nfmini agent demo --scenario congestion --provider mock
nfmini agent demo --scenario route_withdrawal --provider mock
nfmini agent eval --provider mock
```

Ask questions against an existing simulation DB:

```bash
nfmini agent ask --db ./sim.db --provider mock --question "Why is App-B unreachable from Zurich?"
nfmini agent investigate --db ./sim.db --source client_zurich --service app_b --provider mock
nfmini agent monitor-summary --db ./sim.db --provider mock
```

Inspect persisted runs and tool traces:

```bash
nfmini agent runs --db ./sim.db
nfmini agent trace --db ./sim.db --run RUN_ID
```

Optional OpenAI provider:

```bash
pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model-name"
nfmini agent ask --db ./sim.db --provider openai --question "Why is App-B unreachable from Zurich?"
```

OpenAI calls do not happen by default.

### Phase 4: Provider Hardening, Developer UI, and Evidence Relevance

Phase 4 hardens the optional OpenAI provider, adds a local read-only developer
UI, and extends evals so reports are scored on evidence relevance, not only on
whether evidence IDs exist.

OpenAI integration uses the Responses API with function/tool calling and
structured `AgentReport` output. The model still cannot directly access SQLite
and cannot bypass registered tools.

The developer UI is a Streamlit console for inspecting simulated state,
snapshots, diffs, alerts, agent runs, tool traces, evidence, and mock eval
rubrics. It is read-only in this version and does not trigger OpenAI calls.

## Project Layout

| Path | Purpose |
|---|---|
| `data/cases/` | Phase 1 synthetic RCA cases. |
| `data/topologies/` | Phase 2 simulated network topology YAML files. |
| `src/netfabric_mini/acl_checker.py` | Phase 1 ACL evaluation. |
| `src/netfabric_mini/db.py` | SQLite schema and persistence helpers for RCA, simulation, monitoring, and agent metadata. |
| `src/netfabric_mini/guardrails.py` | Phase 1 guardrail classifier. |
| `src/netfabric_mini/investigator.py` | Rule-based Phase 1 RCA workflow. |
| `src/netfabric_mini/llm_adapter.py` | Phase 1 compatibility/mock adapter around the rule-based investigator. |
| `src/netfabric_mini/log_parser.py` | Deterministic parser for supported synthetic log lines. |
| `src/netfabric_mini/metrics.py` | Phase 1 metric anomaly helpers. |
| `src/netfabric_mini/report.py` | Phase 1 report rendering. |
| `src/netfabric_mini/schemas.py` | Phase 1 Pydantic schemas. |
| `src/netfabric_mini/seed_loader.py` | Synthetic case loader. |
| `src/netfabric_mini/tools.py` | Phase 1 read-only tool facade. |
| `src/netfabric_mini/topology_model.py` | Phase 1 NetworkX path inference. |
| `src/netfabric_mini/sim/` | Simulated topology, runtime state, event engine, scenarios, telemetry, snapshots, exports, and pathing. |
| `src/netfabric_mini/ingestion/` | Read-only collectors over simulated state. |
| `src/netfabric_mini/normalization/` | Normalized inventory, observations, and normalizers. |
| `src/netfabric_mini/knowledge/` | KnowledgeBase and store wrappers for topology, state, events, telemetry, and snapshots. |
| `src/netfabric_mini/reasoning/` | Deterministic pathing, reachability, health, alerts, and snapshot diffs. |
| `src/netfabric_mini/orchestration/` | Monitoring workflow and investigation context builder. |
| `src/netfabric_mini/controls/` | Evidence helpers, guardrails, redaction, and data budgets. |
| `src/netfabric_mini/monitoring/` | Compatibility wrappers for monitoring collectors, alerts, diffs, and monitor runs. |
| `src/netfabric_mini/llm/` | LLM config, provider protocol, mock client, OpenAI client, and structured output helpers. |
| `src/netfabric_mini/agent/` | Agent schemas, prompts, registry, executor, loop, validation, approvals, run/session stores, and rendering. |
| `src/netfabric_mini/agent_tools/` | Registered agent tool wrappers over context, monitoring, knowledge, reasoning, snapshots, and simulation approvals. |
| `src/netfabric_mini/evals/` | Deterministic mock-agent eval scenarios, rubrics, and evidence relevance scoring. |
| `src/netfabric_mini/ui/` | Optional Streamlit developer UI and read-only UI data access helpers. |
| `src/netfabric_mini/cli.py` | Root Typer CLI and Phase 1 commands. |
| `src/netfabric_mini/cli_sim.py` | `nfmini sim` CLI commands. |
| `src/netfabric_mini/cli_agent.py` | `nfmini agent` CLI commands. |
| `tests/` | Offline test suite, including optional live OpenAI smoke marker. |

## Architecture

### Six-Layer Architecture

Phase 2 monitoring is organized into six deterministic layers:

1. Data ingestion: read-only collectors over simulated state.
2. Data normalization: collector output becomes stable inventory and observations.
3. Network knowledge base: `KnowledgeBase` coordinates topology, state, events,
   telemetry, snapshots, alerts, and evidence lookup.
4. Deterministic reasoning: pathing, reachability, health, alerts, and diffs.
5. Workflow / agent orchestration: monitoring cycles and future-agent context.
6. Safety and cost control: guardrails, evidence handling, redaction, and budgets.

The monitoring flow is:

```text
SimulationEngine current state
  -> ingestion collectors
  -> normalized observations
  -> KnowledgeBase update
  -> deterministic reasoning
  -> monitoring workflow result
  -> budgeted / redacted / evidence-grounded export
  -> optional LLM agent tools
```

Phase 2 uses this architecture without LLM calls. Phase 3 puts the agent on top
of the same architecture. The agent consumes registered tools and prepared
context; it does not bypass the architecture.

### Agent Architecture

```text
User question
  -> budgeted / redacted investigation context
  -> LLM planning and tool selection
  -> registered AgentTool calls only
  -> deterministic six-layer tools
  -> evidence validation
  -> structured AgentReport
  -> session/run/tool trace persistence
```

The deterministic layers remain authoritative for topology, current state, path
inference, reachability, probe results, telemetry, alerts, snapshot diffs, and
evidence references. The LLM plans, selects tools, interprets results, and
explains findings.

## Installation

Install for normal offline development and testing:

```bash
pip install -e ".[dev]"
```

Install optional OpenAI support:

```bash
pip install -e ".[dev,llm]"
```

Install optional developer UI support:

```bash
pip install -e ".[dev,ui]"
```

Normal operation, mock agent demos, and the standard test suite do not require
OpenAI or an API key.

## Quickstart

### Phase 1 Offline RCA

```bash
nfmini demo --case all
nfmini demo --case acl_block
```

### Phase 2 Simulation and Monitoring

```bash
nfmini sim init --topology data/topologies/simple_branch_app.yaml --db ./sim.db
nfmini sim monitor --db ./sim.db --once
nfmini sim inject --db ./sim.db --event link_down --target link_r1_r2 --param reason=fiber_cut
nfmini sim tick --db ./sim.db --steps 1
nfmini sim monitor --db ./sim.db --once
nfmini sim diff --db ./sim.db --from latest-1 --to latest
```

### Phase 3 Mock Agent

```bash
nfmini agent demo --scenario link_failure --provider mock
nfmini agent ask --db ./sim.db --provider mock --question "Why is App-B unreachable from Zurich?"
nfmini agent eval --provider mock --format json
```

### Optional OpenAI Agent

```bash
pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model-name"
nfmini agent ask --db ./sim.db --provider openai --question "Why is App-B unreachable from Zurich?"
```

### Lightweight Developer UI

```bash
pip install -e ".[dev,ui]"
nfmini ui --db ./sim.db
```

Direct Streamlit launch also works:

```bash
streamlit run src/netfabric_mini/ui/streamlit_app.py -- --db ./sim.db
```

## CLI Reference

### Base RCA Commands

| Command | Purpose |
|---|---|
| `nfmini --version` | Print package version. |
| `nfmini list-cases` | List synthetic Phase 1 cases. |
| `nfmini init-db --case CASE --db PATH` | Create/load a Phase 1 RCA SQLite DB. |
| `nfmini parse-logs --db PATH` | Parse raw logs into structured events. |
| `nfmini investigate --db PATH --ticket T-001 --format markdown` | Run rule-based RCA for a ticket. |
| `nfmini demo --case CASE` | Run the full Phase 1 demo flow. |
| `nfmini demo --case all` | Run all Phase 1 demo cases. |

### Simulation Commands

| Command | Purpose |
|---|---|
| `nfmini sim list-topologies` | List built-in topology YAML files. |
| `nfmini sim validate --topology PATH` | Validate a topology YAML file. |
| `nfmini sim init --topology PATH --db PATH` | Initialize a simulation DB. |
| `nfmini sim state --db PATH` | Print summarized simulated state. |
| `nfmini sim tick --db PATH --steps N` | Advance the logical simulation tick. |
| `nfmini sim inject --db PATH --event EVENT --target TARGET --param KEY=VALUE` | Mutate simulated state through `SimulationEngine`. |
| `nfmini sim monitor --db PATH --once` | Run one monitoring cycle. |
| `nfmini sim snapshot --db PATH` | Create a snapshot without running a full monitor loop. |
| `nfmini sim snapshots --db PATH` | List snapshots. |
| `nfmini sim diff --db PATH --from latest-1 --to latest` | Diff two snapshots. |
| `nfmini sim export --db PATH --format json` | Export current simulated state. |
| `nfmini sim export --db PATH --format latest-snapshot` | Export latest snapshot. |
| `nfmini sim export --db PATH --format events-jsonl` | Export event log as JSONL. |
| `nfmini sim export --db PATH --format telemetry-jsonl` | Export telemetry as JSONL. |
| `nfmini sim export --db PATH --format llm-context` | Export budgeted, redacted future-agent context. |
| `nfmini sim scenario --name NAME` | Run a built-in scenario. |

`llm-ready` is also accepted as an alias for the `llm-context` export format.

### Agent Commands

| Command | Purpose |
|---|---|
| `nfmini agent config` | Print active agent config with secrets redacted. |
| `nfmini agent tools` | List registered agent tools. |
| `nfmini agent ask --db PATH --question TEXT --provider mock` | Run a one-shot agent question. |
| `nfmini agent investigate --db PATH --source DEVICE --service SERVICE --provider mock` | Run a focused source-to-service investigation. |
| `nfmini agent monitor-summary --db PATH --provider mock` | Ask the agent to summarize current alerts and risk. |
| `nfmini agent chat --db PATH --provider mock` | Start a simple interactive chat loop. |
| `nfmini agent runs --db PATH` | List persisted agent runs. |
| `nfmini agent trace --db PATH --run RUN_ID` | Show tool calls for a run. |
| `nfmini agent demo --scenario NAME --provider mock` | Run a built-in scenario and agent investigation. |
| `nfmini agent eval --provider mock --format json` | Run deterministic mock-agent evals with relevance scores. |
| `nfmini agent approvals list --db PATH` | List pending simulated-mutation approvals. |
| `nfmini agent approvals approve APPROVAL_ID --db PATH` | Approve a simulated-mutation request. |
| `nfmini agent approvals reject APPROVAL_ID --db PATH` | Reject a simulated-mutation request. |

### UI Command

| Command | Purpose |
|---|---|
| `nfmini ui --db PATH` | Launch the optional read-only Streamlit developer UI. |

## Configuration

The following environment variables are supported by `llm/config.py`:

| Variable | Purpose |
|---|---|
| `NFM_AGENT_PROVIDER` | `mock` or `openai`; default is `mock`. |
| `OPENAI_API_KEY` | Required only when the OpenAI provider is selected. |
| `OPENAI_MODEL` | Optional model override. If unset, the code uses the project default configured in `llm/config.py`; check OpenAI documentation for currently available model IDs. |
| `NFM_AGENT_MAX_TOOL_CALLS` | Maximum tool calls per agent run. |
| `NFM_AGENT_MAX_OUTPUT_TOKENS` | Maximum provider output tokens requested by the agent. |
| `NFM_AGENT_TEMPERATURE` | Provider temperature setting. |
| `NFM_AGENT_MAX_CONTEXT_EVENTS` | Event count budget for investigation context. |
| `NFM_AGENT_MAX_CONTEXT_TELEMETRY` | Telemetry sample budget for investigation context. |
| `NFM_AGENT_REQUIRE_EVIDENCE` | Whether reports are expected to require evidence. |
| `NFM_AGENT_ALLOW_SIM_MUTATION` | Enables approval-gated simulated mutation tools when true. |
| `NFM_AGENT_TIMEOUT_SECONDS` | Provider timeout configuration. |

API keys are not stored in SQLite. Do not commit secrets. `nfmini agent config`
redacts the OpenAI API key status.

## OpenAI Provider Implementation

`OpenAIResponsesClient` stays behind `LLMClientProtocol`. It imports the
official `openai` package lazily, uses `client.responses.create(...)`, converts
registered `LLMToolSpec` objects into Responses API function tools, and requests
structured final output with the `AgentReport` JSON Schema.

Provider responses are normalized into internal `LLMResponse` objects. Tool
calls become `LLMToolCall` objects, final JSON text becomes structured output
when possible, and usage metadata is captured when the SDK provides it. Provider
errors are wrapped in safe exceptions that do not include API keys or raw
credentials.

## Evidence Model

Reports and tool outputs use evidence references so that conclusions can be
traced back to deterministic data.

Evidence IDs can include:

- ticket IDs such as `T-001`
- raw log IDs such as `rawlog-0001`
- parsed event IDs such as `event-0001`
- ACL rule IDs such as `ACL-DENY-ZRH-APPB-HTTPS`
- metric IDs such as `MET-PD-R2-CPU-1003`
- path result IDs such as `path-client_zurich-to-app_b`
- simulation event IDs such as `event-0-0001`
- telemetry sample IDs such as `telemetry-0-0001`
- snapshot IDs such as `snapshot-1-0002`
- alert IDs such as `alert-1-0001`
- tool trace IDs such as `trace-...`

Final reports must cite evidence for major claims. Unsupported claims should be
labeled explicitly. Deterministic tools are authoritative for network facts.

## Evidence Relevance Rubric

Evidence validity and evidence relevance are separate. A report can cite real
evidence IDs but still cite weak or unrelated evidence. The eval rubric now
scores:

- existence: cited evidence can be resolved
- relevance: evidence types match the expected incident class
- specificity: evidence targets the affected object
- recency: evidence is close to the incident tick or snapshot window
- causal alignment: evidence supports the causal chain
- irrelevant evidence count
- missing expected evidence

Run mock evals with relevance output:

```bash
nfmini agent eval --provider mock --format json
```

Core mock scenarios include `link_failure`, `congestion`, and
`route_withdrawal`.

## Lightweight Developer UI

The optional Streamlit UI is a local developer console. It reads an existing
simulation SQLite DB and applies existing redaction helpers before display.

Install and launch:

```bash
pip install -e ".[dev,ui]"
nfmini ui --db ./sim.db
```

Alternative direct launch:

```bash
streamlit run src/netfabric_mini/ui/streamlit_app.py -- --db ./sim.db
```

Tabs include:

- Overview
- Simulation State
- Snapshots and Diffs
- Agent Runs
- Tool Trace
- Evidence Explorer
- Eval / Rubric

The UI is read-only in this version. It does not inject simulation events and
does not call OpenAI.

## Safety, Guardrails, and Approvals

By default:

- no real devices are contacted
- no SSH or production CLIs are used
- no SNMP, NETCONF, RESTCONF, or gNMI is used
- no shell execution happens from model output
- no real-world remediation is implemented or executed
- no direct model access to SQLite is provided
- no external LLM APIs are called unless the OpenAI provider is explicitly
  selected and `OPENAI_API_KEY` is configured
- simulation mutations happen only through `SimulationEngine`
- agent mutation tools are disabled by default
- approval-gated mutation applies only to simulated state

Approval commands for simulated mutation requests:

```bash
nfmini agent approvals list --db ./sim.db
nfmini agent approvals approve APPROVAL_ID --db ./sim.db
nfmini agent approvals reject APPROVAL_ID --db ./sim.db
```

## Data Budgeting and Redaction

Future/optional LLM context is budgeted and redacted before it is sent to a
provider. Raw payloads are excluded by default where applicable. Event,
telemetry, alert, and link lists may be truncated by budget settings.

The redaction layer removes management IPs, passwords, tokens, secrets, and
community strings. Context exports include evidence references so downstream
agents can cite deterministic data.

## Testing

Run the normal offline test suite:

```bash
pytest -q
```

Run normal tests while excluding optional live OpenAI tests:

```bash
pytest -q -m "not live_openai"
```

Run optional live OpenAI tests only when explicitly enabled:

```bash
export OPENAI_API_KEY="..."
RUN_LIVE_OPENAI_TESTS=1 pytest -q -m live_openai
```

Live tests may incur cost and should not run in normal CI unless deliberately
enabled.

Useful smoke commands:

```bash
nfmini demo --case all
nfmini sim scenario --name link_failure
nfmini sim scenario --name congestion
nfmini sim scenario --name route_withdrawal
nfmini agent demo --scenario link_failure --provider mock
nfmini agent eval --provider mock --format json
```

## Limitations

- Synthetic and simulated data only unless future integrations are added.
- No packet-level simulation.
- No real control-plane protocol lab unless future Containerlab/FRRouting
  integration is added.
- Simple deterministic thresholds for health and alerts.
- Limited deterministic log parser coverage.
- The mock provider uses deterministic scripts/templates.
- The OpenAI provider depends on the installed official SDK and configured key.
- Approval-gated mutation is simulated only.
- Evidence validation checks references and deterministic tool outputs, not full
  semantic truth beyond those tools.

## Roadmap

- Containerlab + FRRouting optional protocol lab.
- Batfish integration for configuration and reachability analysis.
- LLM-assisted log parser generation behind validation tests.
- Richer event correlation and root-cause ranking.
- Benchmark datasets and eval reports.
- Long multi-turn memory summarization.
- Richer telemetry pipeline and visualization.
