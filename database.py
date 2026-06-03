from sqlalchemy import (
    create_engine, Column, String, Float, Integer, DateTime,
    JSON, ForeignKey, Index, Table, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/traffic_simulation"
)

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    simulation_name = Column(String, nullable=False)
    
    t_mod = Column(Float, nullable=False)
    mean_arrival_1 = Column(Float, nullable=False)
    mean_arrival_2 = Column(Float, nullable=False)
    green_time_1 = Column(Float, nullable=False)
    green_time_2 = Column(Float, nullable=False)
    prob_detour = Column(Float, nullable=False)
    entry_interval = Column(Float, nullable=False)
    
    avg_wait = Column(Float, nullable=True)
    avg_travel = Column(Float, nullable=True)
    avg_queue = Column(Float, nullable=True)
    free_probability = Column(Float, nullable=True)
    throughput = Column(Float, nullable=True)
    cars_served = Column(Integer, nullable=True)
    
    metrics_by_route = Column(JSON, nullable=True)
    
    ab_test_id = Column(String, ForeignKey("ab_tests.id"), nullable=True, index=True)
    
    events = relationship("SimulationEvent", back_populates="simulation", cascade="all, delete-orphan")
    metrics = relationship("MetricSnapshot", back_populates="simulation", cascade="all, delete-orphan")
    ab_test = relationship("ABTest", back_populates="simulations")
    
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_ab_test_id', 'ab_test_id'),
    )


class SimulationEvent(Base):
    __tablename__ = "simulation_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, ForeignKey("simulations.id"), index=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    details = Column(JSON, nullable=False)
    
    simulation = relationship("Simulation", back_populates="events")
    
    __table_args__ = (
        Index('idx_simulation_timestamp', 'simulation_id', 'timestamp'),
        Index('idx_event_type', 'event_type'),
    )


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, ForeignKey("simulations.id"), index=True)
    timestamp = Column(Float, nullable=False)
    queue_length_total = Column(Integer, nullable=True)
    queue_1_length = Column(Integer, nullable=True)
    queue_2_length = Column(Integer, nullable=True)
    cars_in_transit = Column(Integer, nullable=True)
    active_light = Column(String, nullable=True)
    
    simulation = relationship("Simulation", back_populates="metrics")
    
    __table_args__ = (
        Index('idx_metric_simulation_ts', 'simulation_id', 'timestamp'),
    )


class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    test_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    variant_a_params = Column(JSON, nullable=False)
    variant_b_params = Column(JSON, nullable=False)
    num_runs_per_variant = Column(Integer, default=10)
    
    results_summary = Column(JSON, nullable=True)
    status = Column(String, default="pending")
    
    simulations = relationship("Simulation", back_populates="ab_test", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_ab_test_created', 'created_at'),
        Index('idx_ab_test_status', 'status'),
    )


class SimulationParameter(Base):
    __tablename__ = "simulation_parameters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, ForeignKey("simulations.id"), index=True)
    param_name = Column(String, nullable=False, index=True)
    param_value = Column(Float, nullable=False)
    metric_affected = Column(String, nullable=True)
    sensitivity_score = Column(Float, nullable=True)


class PerformanceReport(Base):
    __tablename__ = "performance_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    report_name = Column(String, nullable=False)
    report_type = Column(String)
    
    avg_wait_time = Column(Float, nullable=True)
    avg_travel_time = Column(Float, nullable=True)
    total_cars = Column(Integer, nullable=True)
    peak_queue_length = Column(Integer, nullable=True)
    throughput = Column(Float, nullable=True)
    
    data = Column(JSON, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized")


def drop_db():
    Base.metadata.drop_all(bind=engine)
    print("✓ Database dropped")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
