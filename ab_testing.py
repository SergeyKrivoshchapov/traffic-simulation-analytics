from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Tuple
from statistics import mean, stdev
import uuid
from datetime import datetime
import json


@dataclass
class Variant:
    name: str
    params: Dict[str, float]
    
    def __repr__(self) -> str:
        return f"Variant(name={self.name}, params={self.params})"


@dataclass
class VariantResult:
    variant: Variant
    results: List[Dict[str, float]]
    run_count: int = 0
    
    def get_stats(self, metric: str) -> Dict[str, float]:
        values = [r[metric] for r in self.results if metric in r]
        if not values:
            return {"count": 0, "mean": 0, "stdev": 0}
        
        return {
            "count": len(values),
            "mean": mean(values),
            "stdev": stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
        }


class ABTest:
    
    def __init__(
        self,
        test_name: str,
        variant_a: Variant,
        variant_b: Variant,
        description: str = "",
    ):
        self.id = str(uuid.uuid4())
        self.test_name = test_name
        self.variant_a = variant_a
        self.variant_b = variant_b
        self.description = description
        self.created_at = datetime.utcnow()
        self.results_a: VariantResult = VariantResult(variant_a, [])
        self.results_b: VariantResult = VariantResult(variant_b, [])
        self.run_count_per_variant = 0
        
    def run(
        self,
        simulate_func: Callable,
        num_runs: int = 10,
        param_applier: Callable = None,
    ) -> None:
        self.run_count_per_variant = num_runs
        
        print(f"\n[A/B Test: {self.test_name}]")
        print(f"Running {num_runs} simulations for Variant A: {self.variant_a.name}")
        for i in range(num_runs):
            if param_applier:
                param_applier(self.variant_a.params)
            result = simulate_func()
            self.results_a.results.append(result)
            self.results_a.run_count = i + 1
            if (i + 1) % max(1, num_runs // 3) == 0:
                print(f"  ✓ {i + 1}/{num_runs} runs completed")
        
        print(f"Running {num_runs} simulations for Variant B: {self.variant_b.name}")
        for i in range(num_runs):
            if param_applier:
                param_applier(self.variant_b.params)
            result = simulate_func()
            self.results_b.results.append(result)
            self.results_b.run_count = i + 1
            if (i + 1) % max(1, num_runs // 3) == 0:
                print(f"  ✓ {i + 1}/{num_runs} runs completed")
        
        print("✓ A/B test completed")
    
    def compare_metric(self, metric: str) -> Dict[str, Any]:
        stats_a = self.results_a.get_stats(metric)
        stats_b = self.results_b.get_stats(metric)
        
        if stats_a["count"] == 0 or stats_b["count"] == 0:
            return {"error": "Insufficient data for comparison"}
        
        mean_diff = stats_b["mean"] - stats_a["mean"]
        pct_change = (mean_diff / stats_a["mean"] * 100) if stats_a["mean"] != 0 else 0
        
        se_a = stats_a["stdev"] / (stats_a["count"] ** 0.5) if stats_a["stdev"] > 0 else 0
        se_b = stats_b["stdev"] / (stats_b["count"] ** 0.5) if stats_b["stdev"] > 0 else 0
        se_diff = (se_a**2 + se_b**2) ** 0.5
        
        z_score = mean_diff / se_diff if se_diff > 0 else 0
        confidence = "High" if abs(z_score) > 2 else "Medium" if abs(z_score) > 1 else "Low"
        
        return {
            "metric": metric,
            "variant_a": stats_a,
            "variant_b": stats_b,
            "difference": mean_diff,
            "percent_change": pct_change,
            "z_score": z_score,
            "confidence": confidence,
            "winner": (
                self.variant_b.name if pct_change > 0 else self.variant_a.name
            ),
        }
    
    def print_summary(self, metrics: List[str]) -> None:
        print(f"\n{'=' * 80}")
        print(f"A/B Test Results: {self.test_name}")
        print(f"{'=' * 80}")
        print(f"Variant A: {self.variant_a.name}")
        print(f"  Parameters: {self.variant_a.params}")
        print(f"  Runs: {self.run_count_per_variant}")
        print()
        print(f"Variant B: {self.variant_b.name}")
        print(f"  Parameters: {self.variant_b.params}")
        print(f"  Runs: {self.run_count_per_variant}")
        print()
        print(f"{'-' * 80}")
        print(f"{'Metric':<25} {'Variant A':<15} {'Variant B':<15} {'Change':<15} {'Winner':<12} {'Confidence'}")
        print(f"{'-' * 80}")
        
        for metric in metrics:
            comp = self.compare_metric(metric)
            if "error" not in comp:
                a_val = f"{comp['variant_a']['mean']:.2f}"
                b_val = f"{comp['variant_b']['mean']:.2f}"
                change = f"{comp['percent_change']:+.1f}%"
                winner = comp['winner']
                conf = comp['confidence']
                print(f"{metric:<25} {a_val:<15} {b_val:<15} {change:<15} {winner:<12} {conf}")
        
        print(f"{'=' * 80}\n")
    
    def get_summary_dict(self, metrics: List[str]) -> Dict[str, Any]:
        comparisons = {}
        for metric in metrics:
            comp = self.compare_metric(metric)
            if "error" not in comp:
                comparisons[metric] = comp
        
        return {
            "test_id": self.id,
            "test_name": self.test_name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "variant_a": {
                "name": self.variant_a.name,
                "params": self.variant_a.params,
                "run_count": self.results_a.run_count,
            },
            "variant_b": {
                "name": self.variant_b.name,
                "params": self.variant_b.params,
                "run_count": self.results_b.run_count,
            },
            "comparisons": comparisons,
        }
    
    def export_json(self, filepath: str, metrics: List[str]) -> None:
        with open(filepath, 'w') as f:
            json.dump(self.get_summary_dict(metrics), f, indent=2)
    
    @staticmethod
    def create_preset_tests() -> List["ABTest"]:
        tests = []
        
        tests.append(ABTest(
            test_name="Light Timing Optimization",
            variant_a=Variant(
                name="Conservative (30/45 sec)",
                params={
                    "GREEN_TIME_1": 30,
                    "GREEN_TIME_2": 45,
                }
            ),
            variant_b=Variant(
                name="Aggressive (40/55 sec)",
                params={
                    "GREEN_TIME_1": 40,
                    "GREEN_TIME_2": 55,
                }
            ),
            description="Comparing conservative vs aggressive traffic light timing"
        ))
        
        tests.append(ABTest(
            test_name="Detour Probability",
            variant_a=Variant(
                name="Low Detours (20%)",
                params={
                    "PROB_DETOUR": 0.2,
                    "PROB_MAIN": 0.8,
                }
            ),
            variant_b=Variant(
                name="High Detours (40%)",
                params={
                    "PROB_DETOUR": 0.4,
                    "PROB_MAIN": 0.6,
                }
            ),
            description="Comparing different detour adoption rates"
        ))
        
        tests.append(ABTest(
            test_name="Arrival Rate Handling",
            variant_a=Variant(
                name="Normal Load",
                params={
                    "MEAN_ARRIVAL_1": 12,
                    "MEAN_ARRIVAL_2": 8,
                }
            ),
            variant_b=Variant(
                name="High Load",
                params={
                    "MEAN_ARRIVAL_1": 8,
                    "MEAN_ARRIVAL_2": 5,
                }
            ),
            description="Comparing system behavior under different traffic loads"
        ))
        
        return tests
