import asyncio
import time
import statistics
from orchestrator.core import WerkOrchestrator, Stage
from orchestrator.bus.event_bus import EventBus
from orchestrator.registry.agent_registry import AgentRegistry
from orchestrator.memory.context_store import ContextStore
from orchestrator.dispatcher.dispatcher import TaskDispatcher
import unittest.mock as mock

class MockEventBus(EventBus):
    async def connect(self): pass
    async def publish(self, channel, event): pass
    async def subscribe(self, channel): pass
    async def get_message(self, timeout=1.0): return None
    async def close(self): pass

async def benchmark_run(orch, project_id, project_name):
    start_time = time.time()
    
    async def mocked_review(state):
        # print(f"DEBUG: Node REVIEW called for {state['project_id']}, approved={state.get('review_approved')}")
        return {"review_approved": True, "review_feedback": "Auto-approved by benchmark"}

    # Patch the node function in the graph
    # In LangGraph 0.2+, nodes are often stored in the graph's nodes attribute
    # But WerkOrchestrator uses StateGraph which compiles to a Pregel object.
    
    original_review = orch._run_stage_review
    orch._run_stage_review = mocked_review
    
    try:
        # Set a reasonable recursion limit for testing
        config = {"recursion_limit": 20, "configurable": {"thread_id": project_id}}
        final_state = await orch._graph.ainvoke(
            {
                "project_id": project_id,
                "project_name": project_name,
                "current_stage": Stage.INIT.value,
                "previous_stage": "",
                "artifacts": [],
                "blockers": [],
                "review_approved": False,
            },
            config
        )
    finally:
        orch._run_stage_review = original_review
        
    end_time = time.time()
    return (end_time - start_time) * 1000, final_state

async def main():
    bus = MockEventBus()
    registry = AgentRegistry()
    dispatcher = TaskDispatcher()
    context = ContextStore()
    
    orch = WerkOrchestrator(bus, registry, dispatcher, context)
    
    num_runs = 10
    latencies = []
    
    print(f"Running {num_runs} orchestrator workflow benchmarks...")
    
    for i in range(num_runs):
        project_id = f"bench-{i}"
        project_name = f"Bench Project {i}"
        latency, state = await benchmark_run(orch, project_id, project_name)
        latencies.append(latency)
        print(f"Run {i+1}: {latency:.2f} ms")
        
    print(f"\n--- Orchestrator Transition Benchmark ---")
    print(f"Total Stages per Run: 7")
    print(f"Min Latency: {min(latencies):.2f} ms")
    print(f"Max Latency: {max(latencies):.2f} ms")
    print(f"Avg Latency: {statistics.mean(latencies):.2f} ms")
    print(f"Avg Per-Stage Latency: {statistics.mean(latencies)/7:.2f} ms")

if __name__ == "__main__":
    asyncio.run(main())
