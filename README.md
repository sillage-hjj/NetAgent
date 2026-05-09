# NetAgent Lab

NetAgent Lab is a Python 3.11+ network observability and agentic incident
investigation research prototype. It combines synthetic offline RCA,
configurable simulated network state, deterministic monitoring, and an optional
LLM-powered agent layer.

NetAgent Lab is independent and unaffiliated with NetFabric AG. Third-party
names, if mentioned, are used only for descriptive research context.

By default, NetAgent Lab runs offline with deterministic tools and the mock
agent provider. Live OpenAI calls are optional and only used when explicitly
configured. The project does not contact real network devices, does not execute
real remediation, and keeps deterministic tools authoritative for network facts.

## Capability Phases

### Phase 1: Offline RCA MVP

Phase 1 loads synthetic incident cases into SQLite and runs a deterministic RCA
workflow:

- synthetic cases under `data/cases/`
- deterministic log parsing
- NetworkX path inference
- ACL checking
- metric anomaly checks
- evidence-grounded Markdown/text reports

```bash
netagent list-cases
netagent demo --case link_down
netagent demo --case acl_block
netagent demo --case performance_degradation
netagent demo --case all
```

Step-by-step flow:

```bash
netagent init-db --case acl_block --db ./nfmini.db
netagent parse-logs --db ./nfmini.db
netagent investigate --db ./nfmini.db --ticket T-001 --format markdown
```

The legacy compatibility command `nfmini` is still provided:

```bash
nfmini demo --case all
```

### Phase 2: Configurable Simulated Network and Monitoring

Phase 2 adds a deterministic simulated network digital twin. It models
topology, mutable simulated state, logical ticks, event injection, collectors,
telemetry, alerts, snapshots, diffs, and JSON/JSONL exports.

```bash
netagent sim list-topologies
netagent sim validate --topology data/topologies/simple_branch_app.yaml
netagent sim init --topology data/topologies/simple_branch_app.yaml --db ./sim.db
netagent sim state --db ./sim.db
netagent sim monitor --db ./sim.db --once
netagent sim inject --db ./sim.db --event link_down --target link_r1_r2 --param reason=fiber_cut
netagent sim tick --db ./sim.db --steps 1
netagent sim diff --db ./sim.db --from latest-1 --to latest
netagent sim export --db ./sim.db --format json
netagent sim export --db ./sim.db --format latest-snapshot
netagent sim export --db ./sim.db --format events-jsonl
netagent sim export --db ./sim.db --format telemetry-jsonl
netagent sim export --db ./sim.db --format llm-context
netagent sim scenario --name link_failure
netagent sim scenario --name congestion
netagent sim scenario --name route_withdrawal
```

`llm-context` is only a budgeted/redacted export format. It does not call an
LLM.

### Phase 3: Optional LLM Agent System

The agent accepts natural-language questions, builds budgeted/redacted
investigation context, selects registered tools, and produces
schema-validated, evidence-grounded reports. The default provider is `mock`;
OpenAI is optional.

The LLM:

- does not directly query SQLite
- does not directly mutate simulated state
- does not perform path/reachability reasoning itself
- must use deterministic registered tools for network facts
- must cite evidence IDs for major claims

```bash
netagent agent config
netagent agent tools
netagent agent demo --scenario link_failure --provider mock
netagent agent demo --scenario congestion --provider mock
netagent agent demo --scenario route_withdrawal --provider mock
netagent agent eval --provider mock --format json
```

Run against an existing simulation DB:

```bash
netagent agent ask --db ./sim.db --provider mock --question "Why is App-B unreachable from Zurich?"
netagent agent investigate --db ./sim.db --source client_zurich --service app_b --provider mock
netagent agent monitor-summary --db ./sim.db --provider mock
netagent agent runs --db ./sim.db
netagent agent trace --db ./sim.db --run RUN_ID
```

Optional OpenAI provider:

```bash
pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model-name"
netagent agent ask --db ./sim.db --provider openai --question "Why is App-B unreachable from Zurich?"
```

### Phase 4: Provider Hardening, UI, and Evidence Relevance

Phase 4 adds hardened OpenAI Responses API integration, a read-only Streamlit
developer UI, and deterministic evidence relevance scoring for mock-agent
evals.

```bash
pip install -e ".[dev,ui]"
netagent ui --db ./sim.db
streamlit run src/netagent_lab/ui/streamlit_app.py -- --db ./sim.db
netagent agent eval --provider mock --format json
```

## Project Layout

| Path | Purpose |
|---|---|
| `src/netagent_lab/` | Main Python package. |
| `src/netagent_lab/sim/` | Simulated topology, runtime state, event engine, scenarios, telemetry, snapshots, exports, and pathing. |
| `src/netagent_lab/ingestion/` | Read-only collectors over simulated state. |
| `src/netagent_lab/normalization/` | Normalized inventory, observations, and normalizers. |
| `src/netagent_lab/knowledge/` | KnowledgeBase and store wrappers for topology, state, events, telemetry, and snapshots. |
| `src/netagent_lab/reasoning/` | Deterministic pathing, reachability, health, alerts, and snapshot diffs. |
| `src/netagent_lab/orchestration/` | Monitoring workflow and investigation context builder. |
| `src/netagent_lab/controls/` | Evidence helpers, guardrails, redaction, and data budgets. |
| `src/netagent_lab/llm/` | LLM config, provider protocol, mock client, OpenAI client, and structured output helpers. |
| `src/netagent_lab/agent/` | Agent schemas, prompts, registry, executor, loop, validation, approvals, run/session stores, and rendering. |
| `src/netagent_lab/agent_tools/` | Registered agent tool wrappers over the six-layer architecture. |
| `src/netagent_lab/evals/` | Deterministic mock-agent eval scenarios, rubrics, and evidence relevance scoring. |
| `src/netagent_lab/ui/` | Optional read-only Streamlit developer UI. |
| `data/cases/` | Synthetic Phase 1 RCA cases. |
| `data/topologies/` | Synthetic simulated topologies. |
| `docs/research_notes.md` | Neutral architecture research notes. |

## Architecture

### Six-Layer Architecture

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

The six layers are:

1. Data ingestion
2. Data normalization
3. Network knowledge base
4. Deterministic reasoning
5. Workflow / agent orchestration
6. Safety and cost control

Phase 2 uses this architecture without LLM calls. Phase 3 puts the agent on top
of the architecture; the agent consumes tools and context rather than bypassing
the deterministic layers.

### Agent Architecture

```text
User question
  -> budgeted / redacted investigation context
  -> LLM planning and tool selection
  -> registered AgentTool calls only
  -> deterministic six-layer tools
  -> evidence validation
  -> structured AgentReport
  -> session / run / tool trace persistence
```

## Installation

Default offline/test installation:

```bash
pip install -e ".[dev]"
```

Optional OpenAI support:

```bash
pip install -e ".[dev,llm]"
```

Optional Streamlit developer UI:

```bash
pip install -e ".[dev,ui]"
```

Normal tests and mock-agent workflows do not require OpenAI.

## CLI Reference

| Command | Purpose |
|---|---|
| `netagent --version` | Print package version. |
| `netagent list-cases` | List synthetic Phase 1 cases. |
| `netagent init-db --case CASE --db PATH` | Create/load a Phase 1 RCA SQLite DB. |
| `netagent parse-logs --db PATH` | Parse raw logs into structured events. |
| `netagent investigate --db PATH --ticket T-001 --format markdown` | Run rule-based RCA for a ticket. |
| `netagent demo --case CASE` | Run Phase 1 demo flow. |
| `netagent sim ...` | Run simulation, monitoring, snapshot, diff, export, and scenario commands. |
| `netagent agent ...` | Run agent config, tools, ask, investigate, demos, evals, traces, and approvals. |
| `netagent ui --db PATH` | Launch the optional read-only Streamlit UI. |
| `nfmini ...` | Backward-compatible CLI alias. |

## Configuration

| Variable | Purpose |
|---|---|
| `NFM_AGENT_PROVIDER` | `mock` or `openai`; default is `mock`. |
| `OPENAI_API_KEY` | Required only when the OpenAI provider is selected. |
| `OPENAI_MODEL` | Optional model override. If unset, the code uses the default in `llm/config.py`. |
| `NFM_AGENT_MAX_TOOL_CALLS` | Maximum tool calls per run. |
| `NFM_AGENT_MAX_CONTEXT_EVENTS` | Context event budget. |
| `NFM_AGENT_MAX_CONTEXT_TELEMETRY` | Context telemetry budget. |
| `NFM_AGENT_REQUIRE_EVIDENCE` | Whether final reports require evidence. |
| `NFM_AGENT_ALLOW_SIM_MUTATION` | Enables approval-gated simulated mutation tools; default is false. |

API keys are not stored in SQLite. Do not commit secrets. `netagent agent
config` redacts API key status.

## OpenAI Provider Implementation

The optional OpenAI provider uses the OpenAI Responses API, registered function
tools, and structured `AgentReport` output. The model cannot directly access
SQLite or simulator internals; it only receives budgeted/redacted context and
registered tool results. Live OpenAI tests are opt-in only.

## Evidence Model

Reports cite evidence IDs such as:

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

Unsupported claims must be labeled. Deterministic tools are authoritative for
network facts.

## Evidence Relevance Rubric

Evidence validation checks that referenced IDs exist. Evidence relevance evals
go further and score whether evidence is relevant, specific, recent, and
causally aligned with the scenario. Generic-only evidence, such as only citing a
ticket or context object, cannot pass incident relevance scoring.

```bash
netagent agent eval --provider mock --format json
```

## Lightweight Developer UI

The optional Streamlit UI is a local, read-only developer console for:

- topology and current tick overview
- devices, links, services, probes, and link metadata
- snapshots and diffs
- agent runs and final reports
- tool traces and tool outputs
- evidence exploration
- mock eval/rubric results

```bash
pip install -e ".[dev,ui]"
netagent ui --db ./sim.db
```

The UI does not inject events or call OpenAI by default.

## Safety, Guardrails, and Approvals

By default, NetAgent Lab does not:

- contact real devices
- use SSH, SNMP, NETCONF, RESTCONF, gNMI, or production CLIs
- execute shell commands from model output
- execute real-world remediation
- give the model direct SQLite access
- call external LLM APIs unless the OpenAI provider is explicitly selected and configured

Simulation mutations happen only through the simulation engine. Agent mutation
tools are disabled by default and, when enabled, are approval-gated for
simulated state only:

```bash
netagent agent approvals list --db ./sim.db
netagent agent approvals approve APPROVAL_ID --db ./sim.db
netagent agent approvals reject APPROVAL_ID --db ./sim.db
```

## Data Budgeting and Redaction

Future/optional LLM context is budgeted and redacted. Raw payloads are excluded
by default where applicable. Event, telemetry, alert, and link lists may be
truncated. Management IPs, passwords, tokens, secrets, and community strings are
redacted. Context exports include evidence references.

## Testing

```bash
python -m compileall src
pytest -q -m "not live_openai"
```

Optional live OpenAI smoke tests:

```bash
export OPENAI_API_KEY="..."
RUN_LIVE_OPENAI_TESTS=1 pytest -q -m live_openai
```

Live tests may incur cost and should not run in normal CI unless explicitly
enabled.

Useful smoke commands:

```bash
netagent demo --case all
netagent sim scenario --name link_failure
netagent sim scenario --name congestion
netagent sim scenario --name route_withdrawal
netagent agent demo --scenario link_failure --provider mock
netagent agent eval --provider mock --format json
nfmini --help
```

## Legal and Compliance Notes

See:

- `LICENSE`
- `NOTICE`
- `DISCLAIMER.md`
- `THIRD_PARTY_NOTICES.md`
- `docs/research_notes.md`

NetAgent Lab contains synthetic data only. It does not contain vendor source
code, proprietary network data, logos, screenshots, or confidential material.

## Limitations

- Synthetic/simulated data only unless future integrations are added.
- No packet-level simulation.
- No real control-plane lab.
- Simple deterministic thresholds.
- Limited parser coverage.
- Mock provider uses deterministic scripts/templates.
- OpenAI provider depends on the official SDK and configured key.
- Approval-gated mutation is simulated only.
- Evidence validation checks references and deterministic tool outputs, not full semantic truth beyond those tools.

## Roadmap

- Web UI polish for simulation, monitoring, and agent traces.
- Optional Containerlab + FRRouting protocol lab.
- Batfish integration for configuration and reachability analysis.
- LLM-assisted log parser generation behind validation tests.
- Richer event correlation and root-cause ranking.
- Benchmark datasets and eval reports.
- Long multi-turn memory summarization.
- Richer telemetry pipeline and visualization.
