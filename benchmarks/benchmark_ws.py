import asyncio
import websockets
import httpx
import time
import json
import statistics
import uuid

BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/events"
NUM_CLIENTS = 50
TEST_DURATION = 10

async def ws_client(client_id, results):
    try:
        async with websockets.connect(WS_URL) as websocket:
            results[client_id] = []
            while True:
                message = await websocket.recv()
                recv_time = time.time()
                data = json.loads(message)
                if data.get("type") == "project.created":
                    results[client_id].append({
                        "event": "project.created",
                        "project_id": data["payload"]["project_id"],
                        "received_at": recv_time
                    })
                elif data.get("type") == "ping":
                    # Ignore pings
                    pass
    except Exception as e:
        print(f"Client {client_id} error: {e}")

async def trigger_event(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        project_name = f"WS Benchmark {uuid.uuid4().hex[:8]}"
        start_time = time.time()
        response = await client.post(
            f"{BACKEND_URL}/api/v1/projects/",
            json={"name": project_name, "description": "WS Benchmark"},
            headers=headers
        )
        if response.status_code == 201:
            project_id = response.json()["id"]
            return start_time, project_id
        else:
            print(f"Failed to create project: {response.status_code} {response.text}")
            return None, None

async def main():
    # 1. Login to get token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = response.json()["access_token"]

    results = {}
    clients = [asyncio.create_task(ws_client(i, results)) for i in range(NUM_CLIENTS)]
    
    # Wait for connections to stabilize
    print(f"Connecting {NUM_CLIENTS} WebSocket clients...")
    await asyncio.sleep(2)
    
    print("Triggering broadcast event...")
    start_time, project_id = await trigger_event(token)
    
    if not start_time:
        return

    # Wait for clients to receive the event
    await asyncio.sleep(5)
    
    # Analyze results
    latencies = []
    received_count = 0
    for client_id, events in results.items():
        for event in events:
            if event["project_id"] == project_id:
                latency = (event["received_at"] - start_time) * 1000 # ms
                latencies.append(latency)
                received_count += 1
                break
    
    print(f"\n--- WebSocket Broadcast Benchmark ---")
    print(f"Clients connected: {NUM_CLIENTS}")
    print(f"Clients received event: {received_count}")
    
    if latencies:
        print(f"Min Latency: {min(latencies):.2f} ms")
        print(f"Max Latency: {max(latencies):.2f} ms")
        print(f"Avg Latency: {statistics.mean(latencies):.2f} ms")
        if len(latencies) > 1:
            print(f"Std Dev: {statistics.stdev(latencies):.2f} ms")
    else:
        print("No latencies recorded.")

    # Cleanup
    for c in clients:
        c.cancel()

if __name__ == "__main__":
    asyncio.run(main())
