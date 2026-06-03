from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from database import Simulation, SimulationEvent, MetricSnapshot, ABTest, PerformanceReport


class SimulationAnalytics:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_peak_congestion_times(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = self.db.query(
            SimulationEvent.timestamp,
            SimulationEvent.simulation_id,
            func.json_extract(SimulationEvent.details, '$.queue_length').label('queue_length'),
            SimulationEvent.details['queue'].astext.label('queue_name'),
        ).filter(
            SimulationEvent.event_type == 'queue_length_change'
        ).order_by(
            func.json_extract(SimulationEvent.details, '$.new_size').desc()
        ).limit(limit)
        
        results = []
        for row in query:
            results.append({
                'timestamp': row.timestamp,
                'simulation_id': row.simulation_id,
                'queue_name': row.queue_name,
            })
        return results
    
    def get_traffic_jam_statistics(self) -> Dict[str, Any]:
        jam_events = self.db.query(SimulationEvent).filter(
            SimulationEvent.event_type == 'traffic_jam_created'
        ).all()
        
        jam_resolution_events = self.db.query(SimulationEvent).filter(
            SimulationEvent.event_type == 'traffic_jam_resolved'
        ).all()
        
        total_jams = len(jam_events)
        resolved_jams = len(jam_resolution_events)
        
        jam_durations = []
        for created in jam_events:
            resolutions = [
                r for r in jam_resolution_events
                if r.details.get('queue') == created.details.get('queue')
                and r.timestamp > created.timestamp
            ]
            if resolutions:
                duration = resolutions[0].timestamp - created.timestamp
                jam_durations.append(duration)
        
        avg_jam_duration = sum(jam_durations) / len(jam_durations) if jam_durations else 0
        
        return {
            'total_jams': total_jams,
            'resolved_jams': resolved_jams,
            'unresolved_jams': total_jams - resolved_jams,
            'avg_jam_duration': avg_jam_duration,
            'longest_jam': max(jam_durations) if jam_durations else 0,
            'shortest_jam': min(jam_durations) if jam_durations else 0,
        }
    
    def get_queue_statistics_by_hour(self) -> Dict[int, Dict[str, float]]:
        metrics = self.db.query(MetricSnapshot).all()
        
        by_hour: Dict[int, List[int]] = {}
        for metric in metrics:
            hour = int(metric.timestamp // 3600)
            if hour not in by_hour:
                by_hour[hour] = []
            if metric.queue_length_total:
                by_hour[hour].append(metric.queue_length_total)
        
        result = {}
        for hour, lengths in by_hour.items():
            if lengths:
                result[hour] = {
                    'avg_queue': sum(lengths) / len(lengths),
                    'max_queue': max(lengths),
                    'min_queue': min(lengths),
                    'measurements': len(lengths),
                }
        
        return result
    
    def get_route_efficiency(self) -> Dict[str, Dict[str, float]]:
        all_sims = self.db.query(Simulation).all()
        
        route_stats = {
            'light': {'wait_times': [], 'travel_times': []},
            'detour': {'wait_times': [], 'travel_times': []},
            'rural': {'wait_times': [], 'travel_times': []},
        }
        
        for sim in all_sims:
            if sim.metrics_by_route:
                for route, metrics in sim.metrics_by_route.items():
                    if route in route_stats:
                        if 'avg_wait' in metrics:
                            route_stats[route]['wait_times'].append(metrics['avg_wait'])
                        if 'avg_travel' in metrics:
                            route_stats[route]['travel_times'].append(metrics['avg_travel'])
        
        result = {}
        for route, data in route_stats.items():
            waits = data['wait_times']
            travels = data['travel_times']
            result[route] = {
                'avg_wait': sum(waits) / len(waits) if waits else 0,
                'avg_travel': sum(travels) / len(travels) if travels else 0,
                'samples': len(waits),
            }
        
        return result
    
    def compare_configurations(self, param1: str, param2: str) -> Dict[str, Any]:
        sims = self.db.query(Simulation).all()
        
        config_groups: Dict[tuple, List[Simulation]] = {}
        for sim in sims:
            p1_val = getattr(sim, param1, None)
            p2_val = getattr(sim, param2, None)
            key = (p1_val, p2_val)
            if key not in config_groups:
                config_groups[key] = []
            config_groups[key].append(sim)
        
        results = []
        for (p1_val, p2_val), group_sims in config_groups.items():
            if group_sims:
                avg_wait = sum(s.avg_wait for s in group_sims if s.avg_wait) / len(group_sims)
                avg_travel = sum(s.avg_travel for s in group_sims if s.avg_travel) / len(group_sims)
                avg_throughput = sum(s.throughput for s in group_sims if s.throughput) / len(group_sims)
                
                results.append({
                    'param1': param1,
                    'param1_value': p1_val,
                    'param2': param2,
                    'param2_value': p2_val,
                    'sample_count': len(group_sims),
                    'avg_wait_time': avg_wait,
                    'avg_travel_time': avg_travel,
                    'avg_throughput': avg_throughput,
                })
        
        return {
            'param1': param1,
            'param2': param2,
            'comparisons': sorted(results, key=lambda x: x['avg_wait_time']),
        }
    
    def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
        if not test:
            return {'error': 'Test not found'}
        
        variant_a_sims = self.db.query(Simulation).filter(
            Simulation.ab_test_id == test_id,
            Simulation.simulation_name.contains('A')
        ).all()
        
        variant_b_sims = self.db.query(Simulation).filter(
            Simulation.ab_test_id == test_id,
            Simulation.simulation_name.contains('B')
        ).all()
        
        def get_stats(sims):
            waits = [s.avg_wait for s in sims if s.avg_wait]
            travels = [s.avg_travel for s in sims if s.avg_travel]
            throughputs = [s.throughput for s in sims if s.throughput]
            return {
                'count': len(sims),
                'avg_wait': sum(waits) / len(waits) if waits else 0,
                'avg_travel': sum(travels) / len(travels) if travels else 0,
                'avg_throughput': sum(throughputs) / len(throughputs) if throughputs else 0,
            }
        
        return {
            'test_id': test_id,
            'test_name': test.test_name,
            'created_at': test.created_at.isoformat(),
            'variant_a_params': test.variant_a_params,
            'variant_b_params': test.variant_b_params,
            'variant_a_stats': get_stats(variant_a_sims),
            'variant_b_stats': get_stats(variant_b_sims),
        }
    
    def get_top_simulations(self, metric: str = 'throughput', limit: int = 10) -> List[Dict[str, Any]]:
        metric_col = getattr(Simulation, metric)
        sims = self.db.query(Simulation).filter(
            metric_col.isnot(None)
        ).order_by(desc(metric_col)).limit(limit).all()
        
        results = []
        for sim in sims:
            results.append({
                'id': sim.id,
                'name': sim.simulation_name,
                'created_at': sim.created_at.isoformat(),
                'metric': metric,
                'value': getattr(sim, metric),
                'avg_wait': sim.avg_wait,
                'avg_travel': sim.avg_travel,
            })
        
        return results
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        sims = self.db.query(Simulation).all()
        
        if not sims:
            return {'error': 'No simulations found'}
        
        waits = [s.avg_wait for s in sims if s.avg_wait]
        travels = [s.avg_travel for s in sims if s.avg_travel]
        queues = [s.avg_queue for s in sims if s.avg_queue]
        throughputs = [s.throughput for s in sims if s.throughput]
        
        return {
            'total_simulations': len(sims),
            'avg_wait_time': sum(waits) / len(waits) if waits else 0,
            'best_wait_time': min(waits) if waits else 0,
            'worst_wait_time': max(waits) if waits else 0,
            'avg_travel_time': sum(travels) / len(travels) if travels else 0,
            'avg_queue_length': sum(queues) / len(queues) if queues else 0,
            'avg_throughput': sum(throughputs) / len(throughputs) if throughputs else 0,
        }
    
    def get_parameter_sensitivity(self, param_name: str) -> List[Dict[str, Any]]:
        param_col = getattr(Simulation, param_name)
        sims = self.db.query(Simulation).filter(
            param_col.isnot(None)
        ).order_by(param_col).all()
        
        by_value: Dict[float, List[Simulation]] = {}
        for sim in sims:
            val = getattr(sim, param_name)
            if val not in by_value:
                by_value[val] = []
            by_value[val].append(sim)
        
        results = []
        for param_val in sorted(by_value.keys()):
            group = by_value[param_val]
            waits = [s.avg_wait for s in group if s.avg_wait]
            travels = [s.avg_travel for s in group if s.avg_travel]
            
            results.append({
                'param_value': param_val,
                'sample_count': len(group),
                'avg_wait_time': sum(waits) / len(waits) if waits else 0,
                'avg_travel_time': sum(travels) / len(travels) if travels else 0,
            })
        
        return results
