# Werk Platform Performance Report

## 1. Executive Summary
The Werk platform was benchmarked under a mocked production-like environment using an in-memory SQLite database and mocked Redis. The results indicate that the core backend architecture is highly performant, with sub-10ms latencies for WebSocket broadcasts and orchestrator stage transitions.

## 2. Methodology
- **Environment:** Mocked Backend using `start_perf_backend.py` (FastAPI + aiosqlite + fakeredis).
- **Tooling:** Locust (Load Testing), custom Python benchmark scripts (WebSockets & Orchestrator).
- **Concurrency:** 1-50 concurrent users depending on the test suite.

## 3. Key Metrics

### 3.1 REST API Performance
| Endpoint | Method | P50 Latency | P95 Latency | RPS |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/auth/login` | POST | 260 ms | 260 ms | ~4 |
| `/api/v1/projects/` | POST | 170 ms | 170 ms | ~6 |
| `/api/v1/projects/` | GET | 5 ms | 5 ms | ~200 |
| `/api/v1/tasks/` | POST | 10 ms | 10 ms | ~100 |

*Note: Login latency is higher due to password hashing simulation.*

### 3.2 WebSocket Broadcast Latency
Measured the time from a server-side event (Project Creation) to $N$ connected clients receiving the update.
- **Connected Clients:** 50
- **Min Latency:** 7.90 ms
- **Max Latency:** 10.84 ms
- **Avg Latency:** 9.76 ms
- **Success Rate:** 100%

### 3.3 Orchestrator Transition Latency
Measured the overhead of the LangGraph-based orchestrator moving between the 7 defined stages (Init, UX, Architecture, Development, Testing, Review, Deploy).
- **Total Workflow Time:** ~56.89 ms
- **Average Per-Stage Latency:** 8.13 ms
- **Efficiency:** The LangGraph state management and transition logic adds negligible overhead to the functional execution.

## 4. Observations & Recommendations
1. **Security Hashing:** The `login` endpoint is the bottleneck in the auth flow. If scaling to thousands of concurrent logins, consider offloading hashing or using a faster algorithm for non-production environments.
2. **WebSocket Scalability:** Sub-10ms broadcast to 50 clients is excellent. Next steps should involve testing with 1000+ clients to find the point of degradation.
3. **Orchestrator Speed:** The transition speed is very fast, suggesting that the primary bottleneck in production will be the LLM response times or external agent execution rather than the orchestrator overhead.

## 5. Artifacts
- Locust Results: `tests/performance_report_stats.csv`
- WebSocket Benchmark: `tests/benchmark_ws.py`
- Orchestrator Benchmark: `tests/benchmark_orchestrator.py`
