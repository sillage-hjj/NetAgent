层级	NetFabric 可能做的事	技术含义
1. 数据接入层	接入 logs、SNMP traps、BMP、gNMI/gRPC/YANG-Push、CLI、REST API、SNMP、NETCONF/RESTCONF、metrics、NetFlow/IPFIX、packet captures、synthetic probes、runbooks、ticket history、vendor docs 等	覆盖 events、state、traffic、active checks、context 五类数据，而不是只看 dashboard
2. 数据归一化层	把多厂商、非标准、噪声大的文本和指标变成结构化事件、实体、参数和趋势	LLM 主要价值在这里：处理非标准数据源、自然语言 query、CLI 输出和日志文本
3. 网络知识库层	把 routing information、forwarding tables、device configurations、logs 等合并成一个 coherent knowledge base	让 agent 不再盲问设备，而是围绕统一事实库推理
4. 确定性推理层	path inference、firewall rule application、routing/control-plane reasoning、failure reasoning、policy verification	LLM 不直接“猜”路径或协议结果，而是调用专用工具
5. Agent 编排层	ticket 触发后，agent 规划调查步骤，选择工具，聚合证据，形成 RCA、post-mortem 或客户更新	LLM 是 planner/summarizer/tool-caller，不是唯一大脑
6. 安全与成本控制层	context curation、vendor-specific command discovery、log pattern summary、metric trend summary、deterministic guardrails、protected raw telemetry panel	防 hallucination、防危险命令、防 token 成本爆炸，保留原始证据