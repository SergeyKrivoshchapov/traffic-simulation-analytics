from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class EventType(Enum):
    CAR_ARRIVAL = "car_arrival"
    CAR_ENTERS_QUEUE = "car_enters_queue"
    CAR_STARTS_TRAVEL = "car_starts_travel"
    CAR_COMPLETES_TRAVEL = "car_completes_travel"
    QUEUE_LENGTH_CHANGE = "queue_length_change"
    TRAFFIC_JAM_CREATED = "traffic_jam_created"
    TRAFFIC_JAM_RESOLVED = "traffic_jam_resolved"
    LIGHT_STATE_CHANGE = "light_state_change"
    SIMULATION_START = "simulation_start"
    SIMULATION_END = "simulation_end"


@dataclass
class Event:
    event_type: EventType
    timestamp: float
    details: Dict[str, Any]
    simulation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "details": self.details,
            "simulation_id": self.simulation_id,
        }


class EventLogger:
    
    def __init__(self, simulation_id: str, capture_events: bool = True):
        self.simulation_id = simulation_id
        self.events: List[Event] = []
        self.capture_events = capture_events
        self.queue_history: Dict[str, List[Dict[float, int]]] = {
            "queue1": [],
            "queue2": [],
            "detour": [],
            "rural": [],
        }
        self.traffic_jam_threshold = 5
        self.current_queue_sizes = {
            "queue1": 0,
            "queue2": 0,
            "detour": 0,
            "rural": 0,
        }
    
    def log_event(
        self,
        event_type: EventType,
        timestamp: float,
        **details
    ) -> None:
        if not self.capture_events:
            return
        
        event = Event(
            event_type=event_type,
            timestamp=timestamp,
            details=details,
            simulation_id=self.simulation_id,
        )
        self.events.append(event)
    
    def log_car_arrival(self, timestamp: float, queue_name: str, car_id: int) -> None:
        self.log_event(
            EventType.CAR_ARRIVAL,
            timestamp,
            queue=queue_name,
            car_id=car_id,
        )
    
    def log_car_travel(
        self,
        timestamp: float,
        car_id: int,
        queue_from: str,
        route: str,
        wait_time: float,
        travel_time: float,
    ) -> None:
        self.log_event(
            EventType.CAR_STARTS_TRAVEL,
            timestamp,
            car_id=car_id,
            from_queue=queue_from,
            route=route,
            wait_time=wait_time,
            travel_time=travel_time,
        )
    
    def log_car_completion(
        self,
        timestamp: float,
        car_id: int,
        route: str,
        total_wait: float,
        total_travel: float,
    ) -> None:
        self.log_event(
            EventType.CAR_COMPLETES_TRAVEL,
            timestamp,
            car_id=car_id,
            route=route,
            total_wait=total_wait,
            total_travel=total_travel,
        )
    
    def update_queue_size(self, timestamp: float, queue_name: str, new_size: int) -> None:
        old_size = self.current_queue_sizes.get(queue_name, 0)
        
        if new_size != old_size:
            self.current_queue_sizes[queue_name] = new_size
            self.queue_history[queue_name].append({timestamp: new_size})
            
            self.log_event(
                EventType.QUEUE_LENGTH_CHANGE,
                timestamp,
                queue=queue_name,
                old_size=old_size,
                new_size=new_size,
            )
            
            if new_size > self.traffic_jam_threshold and old_size <= self.traffic_jam_threshold:
                self.log_event(
                    EventType.TRAFFIC_JAM_CREATED,
                    timestamp,
                    queue=queue_name,
                    queue_length=new_size,
                )
            elif new_size <= self.traffic_jam_threshold and old_size > self.traffic_jam_threshold:
                self.log_event(
                    EventType.TRAFFIC_JAM_RESOLVED,
                    timestamp,
                    queue=queue_name,
                    queue_length=new_size,
                )
    
    def log_light_state(self, timestamp: float, light_id: int, state: str) -> None:
        self.log_event(
            EventType.LIGHT_STATE_CHANGE,
            timestamp,
            light_id=light_id,
            state=state,
        )
    
    def get_events(self) -> List[Dict[str, Any]]:
        return [event.to_dict() for event in self.events]
    
    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        return [e for e in self.events if e.event_type == event_type]
    
    def get_events_in_range(self, start: float, end: float) -> List[Event]:
        return [e for e in self.events if start <= e.timestamp <= end]
    
    def get_queue_summary(self) -> Dict[str, Dict[str, float]]:
        summary = {}
        for queue_name, history in self.queue_history.items():
            if history:
                sizes = [list(h.values())[0] for h in history]
                summary[queue_name] = {
                    "max_length": max(sizes),
                    "avg_length": sum(sizes) / len(sizes),
                    "peak_times": len([s for s in sizes if s > self.traffic_jam_threshold]),
                }
        return summary
    
    def get_traffic_jam_events(self) -> List[Event]:
        return (
            self.get_events_by_type(EventType.TRAFFIC_JAM_CREATED) +
            self.get_events_by_type(EventType.TRAFFIC_JAM_RESOLVED)
        )
    
    def export_json(self, filepath: str) -> None:
        with open(filepath, 'w') as f:
            json.dump(self.get_events(), f, indent=2)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        return {
            "total_events": len(self.events),
            "event_types": {
                et.value: len(self.get_events_by_type(et))
                for et in EventType
            },
            "queue_summary": self.get_queue_summary(),
            "traffic_jams_count": len(self.get_traffic_jam_events()),
        }
