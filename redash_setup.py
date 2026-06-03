import os
import requests
import json
from typing import Dict, List, Optional

class RedashSetup:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Key {api_key}',
            'Content-Type': 'application/json'
        }
        self.db_id = None
        self.query_ids = {}

    def create_datasource(self, db_url: str) -> int:
        endpoint = f'{self.base_url}/api/data_sources'
        parsed_url = self._parse_db_url(db_url)
        payload = {
            'name': 'Traffic Simulation DB',
            'type': 'pg',
            'options': {
                'host': parsed_url['host'],
                'port': parsed_url['port'],
                'user': parsed_url['user'],
                'password': parsed_url['password'],
                'dbname': parsed_url['dbname']
            }
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 200:
            self.db_id = response.json()['id']
            print(f"Created datasource: {self.db_id}")
            return self.db_id
        else:
            print(f"Error creating datasource: {response.text}")
            return None

    def create_query(self, name: str, sql: str) -> Optional[int]:
        endpoint = f'{self.base_url}/api/queries'
        payload = {
            'name': name,
            'data_source_id': self.db_id,
            'query': sql
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 200:
            query_id = response.json()['id']
            self.query_ids[name] = query_id
            print(f"Created query: {name} ({query_id})")
            return query_id
        else:
            print(f"Error creating query {name}: {response.text}")
            return None

    def create_dashboard(self, title: str, query_ids: List[int]) -> Optional[int]:
        endpoint = f'{self.base_url}/api/dashboards'
        payload = {
            'name': title,
            'widgets': []
        }
        for qid in query_ids:
            payload['widgets'].append({
                'type': 'query',
                'query_id': qid,
                'visualization': 'TABLE',
                'width': 1
            })
        response = requests.post(endpoint, json=payload, headers=self.headers)
        if response.status_code == 200:
            dashboard_id = response.json()['id']
            print(f"Created dashboard: {title} ({dashboard_id})")
            return dashboard_id
        else:
            print(f"Error creating dashboard: {response.text}")
            return None

    def _parse_db_url(self, db_url: str) -> Dict:
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', '')
        if '@' in db_url:
            auth, host_db = db_url.split('@')
            if ':' in auth:
                user, password = auth.split(':')
            else:
                user, password = auth, ''
        else:
            user, password = 'postgres', ''
            host_db = db_url
        if '/' in host_db:
            host_port, dbname = host_db.split('/')
        else:
            host_port = host_db
            dbname = 'traffic_simulation'
        if ':' in host_port:
            host, port = host_port.split(':')
            port = int(port)
        else:
            host = host_port
            port = 5432
        return {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'dbname': dbname
        }

def setup_dashboard(redash_url: str, redash_key: str, db_url: str):
    setup = RedashSetup(redash_url, redash_key)
    setup.create_datasource(db_url)
    
    queries = {
        'Simulation Summary': "SELECT COUNT(*) as total, ROUND(AVG(avg_wait)::numeric,2) as avg_wait FROM simulations",
        'Queue by Hour': "SELECT (timestamp/3600)::integer as hour, ROUND(AVG(queue_length_total)::numeric,1) as avg_queue FROM metric_snapshots GROUP BY hour ORDER BY hour",
        'Traffic Jams': "SELECT details->>'queue' as queue, COUNT(*) as jams FROM simulation_events WHERE event_type='traffic_jam_created' GROUP BY queue",
        'Route Efficiency': "SELECT 'light' as route, ROUND(AVG((metrics_by_route->'light'->>'avg_wait')::numeric),2) as avg_wait FROM simulations WHERE metrics_by_route->'light' IS NOT NULL",
        'Top Simulations': "SELECT simulation_name, ROUND(avg_wait::numeric,2) as wait_time FROM simulations ORDER BY avg_wait ASC LIMIT 10"
    }
    
    query_ids = []
    for name, sql in queries.items():
        query_id = setup.create_query(name, sql)
        if query_id:
            query_ids.append(query_id)
    
    if query_ids:
        setup.create_dashboard('Traffic Simulation Analytics', query_ids)
        print("Dashboard setup complete!")

if __name__ == '__main__':
    redash_url = os.getenv('REDASH_API_URL', 'http://localhost:5000')
    redash_key = os.getenv('REDASH_API_KEY', '')
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres@localhost/traffic_simulation')
    if not redash_key:
        print("Error: REDASH_API_KEY not set")
        exit(1)
    setup_dashboard(redash_url, redash_key, db_url)
