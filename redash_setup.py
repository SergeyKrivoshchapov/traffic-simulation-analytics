import os
import requests

REDASH_URL = os.getenv("REDASH_API_URL", "http://localhost:5000")
REDASH_KEY = os.getenv("REDASH_API_KEY")

if not REDASH_KEY:
    print("REDASH_API_KEY not set")
    exit(1)

HEADERS = {"Authorization": f"Key {REDASH_KEY}", "Content-Type": "application/json"}

resp = requests.get(f"{REDASH_URL}/api/data_sources", headers=HEADERS)
datasources = resp.json()
ds_id = None
for ds in datasources:
    if ds.get("name") == "Traffic Simulation DB":
        ds_id = ds["id"]
        break

if not ds_id:
    payload = {
        "name": "Traffic Simulation DB",
        "type": "pg",
        "options": {
            "host": "host.docker.internal",
            "port": 5432,
            "user": "postgres",
            "password": "postgres",
            "dbname": "traffic_simulation",
        },
    }
    resp = requests.post(
        f"{REDASH_URL}/api/data_sources", json=payload, headers=HEADERS
    )
    if resp.status_code == 200:
        ds_id = resp.json()["id"]
    else:
        print(f"Failed to create datasource: {resp.text}")
        exit(1)

queries = {
    "Simulation Summary": """
        SELECT 
            COUNT(*) as total,
            ROUND(AVG(avg_wait)::numeric, 2) as avg_wait_sec,
            ROUND(AVG(avg_travel)::numeric, 2) as avg_travel_sec,
            SUM(cars_served) as total_cars
        FROM simulations
    """,
    "Route Comparison": """
        SELECT 
            'light' as route,
            ROUND(AVG((metrics_by_route->'light'->>'avg_wait')::numeric), 2) as avg_wait
        FROM simulations WHERE metrics_by_route->'light' IS NOT NULL
        UNION ALL
        SELECT 
            'detour',
            ROUND(AVG((metrics_by_route->'detour'->>'avg_wait')::numeric), 2)
        FROM simulations WHERE metrics_by_route->'detour' IS NOT NULL
        UNION ALL
        SELECT 
            'rural',
            ROUND(AVG((metrics_by_route->'rural'->>'avg_wait')::numeric), 2)
        FROM simulations WHERE metrics_by_route->'rural' IS NOT NULL
    """,
    "A/B Test Results": """
        SELECT test_name, status, results_summary
        FROM ab_tests
        WHERE status = 'completed'
        ORDER BY created_at DESC
    """,
}

for name, sql in queries.items():
    payload = {"name": name, "data_source_id": ds_id, "query": sql.strip()}
    resp = requests.post(f"{REDASH_URL}/api/queries", json=payload, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Query '{name}' failed: {resp.text}")
