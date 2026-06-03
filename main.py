import random
import math
import uuid
from statistics import mean, variance
from typing import Dict, List, Callable, Tuple, Optional
import matplotlib.pyplot as plt

from events import EventLogger, EventType
from database import SessionLocal, Simulation, init_db
from ab_testing import ABTest, Variant
from analytics import SimulationAnalytics

T_MOD = 14400

MEAN_ARRIVAL_1 = 12
MEAN_ARRIVAL_2 = 8
GREEN_TIME_1 = 30
GREEN_TIME_2 = 45
ENTRY_INTERVAL = 2
SECTION_TRAVEL_TIME = 12

DETOUR_TRAVEL_TIME = 252
MEAN_RURAL = 20
TURN_TIME = 5

PROB_DETOUR = 0.2
PROB_MAIN = 0.8

EPS_REL = 0.005
ALPHA = 0.95

ALPHA_TO_T = {
    0.80: 1.28,
    0.85: 1.44,
    0.90: 1.645,
    0.95: 1.96,
    0.99: 2.576,
}

event_logger: Optional[EventLogger] = None


def get_t_alpha(alpha: float) -> float:
    if alpha in ALPHA_TO_T:
        return ALPHA_TO_T[alpha]
    sorted_alphas = sorted(ALPHA_TO_T.keys())
    for i in range(len(sorted_alphas) - 1):
        a1, a2 = sorted_alphas[i], sorted_alphas[i + 1]
        if a1 < alpha < a2:
            t1, t2 = ALPHA_TO_T[a1], ALPHA_TO_T[a2]
            return t1 + (t2 - t1) * (alpha - a1) / (a2 - a1)
    raise ValueError(f"alpha={alpha} вне диапазона")


def set_parameters(params: Dict[str, float]) -> None:
    global T_MOD, MEAN_ARRIVAL_1, MEAN_ARRIVAL_2, GREEN_TIME_1, GREEN_TIME_2
    global PROB_DETOUR, PROB_MAIN, ENTRY_INTERVAL, DETOUR_TRAVEL_TIME
    
    if 'T_MOD' in params:
        T_MOD = params['T_MOD']
    if 'MEAN_ARRIVAL_1' in params:
        MEAN_ARRIVAL_1 = params['MEAN_ARRIVAL_1']
    if 'MEAN_ARRIVAL_2' in params:
        MEAN_ARRIVAL_2 = params['MEAN_ARRIVAL_2']
    if 'GREEN_TIME_1' in params:
        GREEN_TIME_1 = params['GREEN_TIME_1']
    if 'GREEN_TIME_2' in params:
        GREEN_TIME_2 = params['GREEN_TIME_2']
    if 'PROB_DETOUR' in params:
        PROB_DETOUR = params['PROB_DETOUR']
    if 'PROB_MAIN' in params:
        PROB_MAIN = params['PROB_MAIN']
    if 'ENTRY_INTERVAL' in params:
        ENTRY_INTERVAL = params['ENTRY_INTERVAL']
    if 'DETOUR_TRAVEL_TIME' in params:
        DETOUR_TRAVEL_TIME = params['DETOUR_TRAVEL_TIME']


def simulate_combined(simulation_id: Optional[str] = None, log_events: bool = False) -> Dict:
    if simulation_id is None:
        simulation_id = str(uuid.uuid4())
    
    global event_logger
    if log_events:
        event_logger = EventLogger(simulation_id, capture_events=True)
    else:
        event_logger = None
    
    if event_logger:
        event_logger.log_event(EventType.SIMULATION_START, 0)
    
    current_time = 0
    queue1_light = []
    queue2_light = []
    detour_entry_queue = []
    detour_in_transit = []
    detour_exit_queue = []
    rural_queue = []

    next_arrival1 = random.expovariate(1 / MEAN_ARRIVAL_1)
    next_arrival2 = random.expovariate(1 / MEAN_ARRIVAL_2)
    next_rural = random.expovariate(1 / MEAN_RURAL)

    cars_on_R1_after_light = []
    cars_on_R2_after_light = []

    total_wait_light, total_travel_light, total_cars_light = 0, 0, 0
    no_wait_light = 0
    total_wait_detour, total_travel_detour, total_cars_detour = 0, 0, 0
    no_wait_detour = 0
    total_wait_rural, total_travel_rural, total_cars_rural = 0, 0, 0
    no_wait_cars = 0

    queue_sum, queue_measurements = 0, 0

    while current_time < T_MOD:
        for i, (exit_time, info) in enumerate(detour_in_transit[:]):
            if current_time >= exit_time:
                detour_exit_queue.append(info)
                detour_in_transit.pop(i)
                break

        for i, (exit_time, car_type) in enumerate(cars_on_R1_after_light[:]):
            if current_time >= exit_time:
                cars_on_R1_after_light.pop(i)
                break

        for i, (exit_time, car_type) in enumerate(cars_on_R2_after_light[:]):
            if current_time >= exit_time:
                cars_on_R2_after_light.pop(i)
                break

        while next_arrival1 <= current_time:
            queue1_light.append(next_arrival1)
            if event_logger:
                event_logger.log_car_arrival(current_time, 'queue1', len(queue1_light))
            next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

        while next_arrival2 <= current_time:
            queue2_light.append(next_arrival2)
            if event_logger:
                event_logger.log_car_arrival(current_time, 'queue2', len(queue2_light))
            next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

        while next_rural <= current_time:
            rural_queue.append(current_time)
            if event_logger:
                event_logger.log_car_arrival(current_time, 'rural', len(rural_queue))
            next_rural += random.expovariate(1 / MEAN_RURAL)

        no_R1 = len(cars_on_R1_after_light) == 0
        no_R2 = len(cars_on_R2_after_light) == 0

        if detour_exit_queue and no_R1 and no_R2:
            arrival_info = detour_exit_queue.pop(0)
            detour_arrival = arrival_info["arrival"]
            wait = current_time - detour_arrival
            travel = wait + TURN_TIME
            total_wait_detour += wait
            total_travel_detour += travel
            if wait < 0.001:
                no_wait_detour += 1

        if rural_queue and no_R2:
            arrival = rural_queue.pop(0)
            wait = current_time - arrival
            travel = wait + TURN_TIME
            total_wait_rural += wait
            total_travel_rural += travel
            total_cars_rural += 1

        if queue1_light:
            arrival = queue1_light[0]
            if current_time >= max(arrival, current_time):
                if random.random() < PROB_DETOUR:
                    if no_R2 and no_R1:
                        queue1_light.pop(0)
                        wait = current_time - arrival
                        travel = wait + DETOUR_TRAVEL_TIME + TURN_TIME
                        total_wait_detour += wait
                        total_travel_detour += travel
                        total_cars_detour += 1
                        if wait < 0.001:
                            no_wait_detour += 1
                        if event_logger:
                            event_logger.log_car_travel(current_time, 1, 'queue1', 'detour', wait, travel)
                        detour_in_transit.append(
                            (
                                current_time + DETOUR_TRAVEL_TIME,
                                {"arrival": current_time},
                            )
                        )

        green_end = current_time + GREEN_TIME_1
        next_entry_time = current_time

        if event_logger:
            event_logger.log_light_state(current_time, 1, 'green')

        while current_time < green_end and current_time < T_MOD:
            for i, (exit_time, info) in enumerate(detour_in_transit[:]):
                if current_time >= exit_time:
                    detour_exit_queue.append(info)
                    detour_in_transit.pop(i)
                    break

            for i, (exit_time, car_type) in enumerate(cars_on_R1_after_light[:]):
                if current_time >= exit_time:
                    cars_on_R1_after_light.pop(i)
                    break

            for i, (exit_time, car_type) in enumerate(cars_on_R2_after_light[:]):
                if current_time >= exit_time:
                    cars_on_R2_after_light.pop(i)
                    break

            while next_arrival1 <= current_time:
                queue1_light.append(next_arrival1)
                if event_logger:
                    event_logger.log_car_arrival(current_time, 'queue1', len(queue1_light))
                next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

            while next_arrival2 <= current_time:
                queue2_light.append(next_arrival2)
                if event_logger:
                    event_logger.log_car_arrival(current_time, 'queue2', len(queue2_light))
                next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

            while next_rural <= current_time:
                rural_queue.append(current_time)
                if event_logger:
                    event_logger.log_car_arrival(current_time, 'rural', len(rural_queue))
                next_rural += random.expovariate(1 / MEAN_RURAL)

            no_R1 = len(cars_on_R1_after_light) == 0
            no_R2 = len(cars_on_R2_after_light) == 0

            if event_logger:
                event_logger.update_queue_size(current_time, 'queue1', len(queue1_light))
                event_logger.update_queue_size(current_time, 'queue2', len(queue2_light))

            if detour_exit_queue and no_R1 and no_R2:
                arrival_info = detour_exit_queue.pop(0)
                detour_arrival = arrival_info["arrival"]
                wait = current_time - detour_arrival
                travel = wait + TURN_TIME
                total_wait_detour += wait
                total_travel_detour += travel
                if wait < 0.001:
                    no_wait_detour += 1

            if rural_queue and no_R2:
                arrival = rural_queue.pop(0)
                wait = current_time - arrival
                travel = wait + TURN_TIME
                total_wait_rural += wait
                total_travel_rural += travel
                total_cars_rural += 1

            if queue1_light and current_time >= next_entry_time:
                arrival = queue1_light[0]
                if current_time >= arrival:
                    if random.random() < PROB_DETOUR:
                        if no_R2 and no_R1:
                            queue1_light.pop(0)
                            wait = current_time - arrival
                            travel = wait + DETOUR_TRAVEL_TIME + TURN_TIME
                            total_wait_detour += wait
                            total_travel_detour += travel
                            total_cars_detour += 1
                            if wait < 0.001:
                                no_wait_detour += 1
                            if event_logger:
                                event_logger.log_car_travel(current_time, 1, 'queue1', 'detour', wait, travel)
                            detour_in_transit.append(
                                (
                                    current_time + DETOUR_TRAVEL_TIME,
                                    {"arrival": current_time},
                                )
                            )
                            next_entry_time = current_time + ENTRY_INTERVAL
                    else:
                        queue1_light.pop(0)
                        wait = current_time - arrival
                        travel = wait + SECTION_TRAVEL_TIME
                        total_wait_light += wait
                        total_travel_light += travel
                        total_cars_light += 1
                        if wait < 0.001:
                            no_wait_light += 1
                        if event_logger:
                            event_logger.log_car_travel(current_time, 1, 'queue1', 'main', wait, travel)
                        cars_on_R1_after_light.append(
                            (current_time + SECTION_TRAVEL_TIME, "W1")
                        )
                        next_entry_time = current_time + ENTRY_INTERVAL

            queue_sum += (
                len(queue1_light)
                + len(queue2_light)
                + len(detour_exit_queue)
                + len(rural_queue)
            )
            queue_measurements += 1
            current_time += 1

        if event_logger:
            event_logger.log_light_state(current_time, 1, 'red')

        current_time += SECTION_TRAVEL_TIME

        green_end = current_time + GREEN_TIME_2
        next_entry_time = current_time

        if event_logger:
            event_logger.log_light_state(current_time, 2, 'green')

        while current_time < green_end and current_time < T_MOD:
            for i, (exit_time, info) in enumerate(detour_in_transit[:]):
                if current_time >= exit_time:
                    detour_exit_queue.append(info)
                    detour_in_transit.pop(i)
                    break

            for i, (exit_time, car_type) in enumerate(cars_on_R1_after_light[:]):
                if current_time >= exit_time:
                    cars_on_R1_after_light.pop(i)
                    break

            for i, (exit_time, car_type) in enumerate(cars_on_R2_after_light[:]):
                if current_time >= exit_time:
                    cars_on_R2_after_light.pop(i)
                    break

            while next_arrival1 <= current_time:
                queue1_light.append(next_arrival1)
                if event_logger:
                    event_logger.log_car_arrival(current_time, 'queue1', len(queue1_light))
                next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

            while next_arrival2 <= current_time:
                queue2_light.append(next_arrival2)
                if event_logger:
                    event_logger.log_car_arrival(current_time, 'queue2', len(queue2_light))
                next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

            while next_rural <= current_time:
                rural_queue.append(current_time)
                if event_logger:
                    event_logger.log_car_arrival(current_time, 'rural', len(rural_queue))
                next_rural += random.expovariate(1 / MEAN_RURAL)

            no_R1 = len(cars_on_R1_after_light) == 0
            no_R2 = len(cars_on_R2_after_light) == 0

            if event_logger:
                event_logger.update_queue_size(current_time, 'queue2', len(queue2_light))

            if detour_exit_queue and no_R1 and no_R2:
                arrival_info = detour_exit_queue.pop(0)
                detour_arrival = arrival_info["arrival"]
                wait = current_time - detour_arrival
                travel = wait + TURN_TIME
                total_wait_detour += wait
                total_travel_detour += travel
                if wait < 0.001:
                    no_wait_detour += 1

            if rural_queue and no_R2:
                arrival = rural_queue.pop(0)
                wait = current_time - arrival
                travel = wait + TURN_TIME
                total_wait_rural += wait
                total_travel_rural += travel
                total_cars_rural += 1

            if queue2_light and current_time >= next_entry_time:
                arrival = queue2_light.pop(0)
                wait = current_time - arrival
                travel = wait + SECTION_TRAVEL_TIME
                total_wait_light += wait
                total_travel_light += travel
                total_cars_light += 1
                if wait < 0.001:
                    no_wait_light += 1
                if event_logger:
                    event_logger.log_car_travel(current_time, 2, 'queue2', 'main', wait, travel)
                cars_on_R2_after_light.append(
                    (current_time + SECTION_TRAVEL_TIME, "W2")
                )
                next_entry_time = current_time + ENTRY_INTERVAL

            queue_sum += (
                len(queue1_light)
                + len(queue2_light)
                + len(detour_exit_queue)
                + len(rural_queue)
            )
            queue_measurements += 1
            current_time += 1

        if event_logger:
            event_logger.log_light_state(current_time, 2, 'red')

        current_time += SECTION_TRAVEL_TIME

    if event_logger:
        event_logger.log_event(EventType.SIMULATION_END, current_time)

    total_cars = total_cars_light + total_cars_detour + total_cars_rural
    total_wait = total_wait_light + total_wait_detour + total_wait_rural
    total_travel = total_travel_light + total_travel_detour + total_travel_rural
    no_wait_cars = no_wait_light + no_wait_detour

    avg_wait = total_wait / total_cars if total_cars else 0
    avg_travel = total_travel / total_cars if total_cars else 0
    free_prob = no_wait_cars / total_cars if total_cars else 0
    avg_queue = queue_sum / queue_measurements if queue_measurements else 0
    throughput = total_cars / T_MOD

    return {
        "simulation_id": simulation_id,
        "avg_wait": avg_wait,
        "avg_travel": avg_travel,
        "avg_queue": avg_queue,
        "free_probability": free_prob,
        "throughput": throughput,
        "cars_served": total_cars,
        "cars_light": total_cars_light,
        "cars_detour": total_cars_detour,
        "cars_rural": total_cars_rural,
        "avg_wait_light": total_wait_light / total_cars_light if total_cars_light else 0,
        "avg_travel_light": total_travel_light / total_cars_light if total_cars_light else 0,
        "avg_wait_detour": total_wait_detour / total_cars_detour if total_cars_detour else 0,
        "avg_travel_detour": total_travel_detour / total_cars_detour if total_cars_detour else 0,
        "avg_wait_rural": total_wait_rural / total_cars_rural if total_cars_rural else 0,
        "avg_travel_rural": total_travel_rural / total_cars_rural if total_cars_rural else 0,
    }


def save_simulation_to_db(results: Dict, simulation_name: str = "simulation") -> None:
    try:
        db = SessionLocal()
        
        sim = Simulation(
            id=results.get("simulation_id", str(uuid.uuid4())),
            simulation_name=simulation_name,
            t_mod=T_MOD,
            mean_arrival_1=MEAN_ARRIVAL_1,
            mean_arrival_2=MEAN_ARRIVAL_2,
            green_time_1=GREEN_TIME_1,
            green_time_2=GREEN_TIME_2,
            prob_detour=PROB_DETOUR,
            entry_interval=ENTRY_INTERVAL,
            avg_wait=results.get("avg_wait"),
            avg_travel=results.get("avg_travel"),
            avg_queue=results.get("avg_queue"),
            free_probability=results.get("free_probability"),
            throughput=results.get("throughput"),
            cars_served=results.get("cars_served"),
            metrics_by_route={
                "light": {
                    "avg_wait": results.get("avg_wait_light"),
                    "avg_travel": results.get("avg_travel_light"),
                    "cars": results.get("cars_light"),
                },
                "detour": {
                    "avg_wait": results.get("avg_wait_detour"),
                    "avg_travel": results.get("avg_travel_detour"),
                    "cars": results.get("cars_detour"),
                },
                "rural": {
                    "avg_wait": results.get("avg_wait_rural"),
                    "avg_travel": results.get("avg_travel_rural"),
                    "cars": results.get("cars_rural"),
                },
            }
        )
        
        db.add(sim)
        db.commit()
        db.close()
        print(f"✓ Simulation saved to database: {results.get('simulation_id')}")
    except Exception as e:
        print(f"✗ Error saving to database: {e}")


def stability_check_10runs(
    simulate_func: Callable,
    metrics: List[Tuple[str, str]],
    epsilon_rel: float,
    num_runs: int = 10,
) -> None:
    eps_percent = epsilon_rel * 100
    print(f"\n{'=' * 70}")
    print(f"МЕТОД ПО 10 ПРОГОНАМ (проверка устойчивости, ε = {eps_percent:.0f}%)")

    results = [simulate_func() for _ in range(num_runs)]

    col_widths = [8]
    headers = ["Прогон"]
    for _, label in metrics:
        headers.append(label)
        col_widths.append(max(len(label), 10))
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(f"\n{header_line}\n{'-' * len(header_line)}")
    for i, res in enumerate(results, 1):
        row = [str(i).ljust(col_widths[0])]
        for j, (key, _) in enumerate(metrics):
            row.append(f"{res[key]:.2f}".ljust(col_widths[j + 1]))
        print(" | ".join(row))

    print(
        f"\n{'Показатель':<35} {'мин':<10} {'макс':<10} {'сред':<10} {'разброс (%)':<12} {'устойчивость'}"
    )
    print("-" * 95)
    for key, label in metrics:
        vals = [r[key] for r in results]
        min_v, max_v, mean_v = min(vals), max(vals), mean(vals)
        spread = (max_v - min_v) / mean_v * 100 if mean_v > 0 else 0.0
        stable = "ДА" if spread <= eps_percent else "НЕТ"
        print(
            f"{label:<35} {min_v:<10.2f} {max_v:<10.2f} {mean_v:<10.2f} {spread:<12.1f} {stable}"
        )


def calculate_required_runs(
    values: List[float], epsilon_rel: float, t_alpha: float
) -> int:
    n = len(values)
    if n < 2:
        return n * 2
    mean_val = mean(values)
    if mean_val == 0:
        return n * 2
    epsilon_abs = epsilon_rel * mean_val
    var_val = variance(values)
    if var_val == 0:
        return n
    required = math.ceil((t_alpha**2 * var_val) / (epsilon_abs**2))
    return max(required, n)


def run_precision_iterative(
    simulate_func: Callable,
    target_metric: str,
    metric_label: str,
    epsilon_rel: float,
    alpha: float = ALPHA,
    min_runs: int = 50,
    max_runs: int = 5000,
) -> Dict:
    t_alpha = get_t_alpha(alpha)
    eps_percent = epsilon_rel * 100
    print(f"\n{'=' * 70}")
    print(f"ИТЕРАЦИОННЫЙ МЕТОД для показателя «{metric_label}»")
    print(
        f"Относительная погрешность ε = {eps_percent:.0f}%, α = {alpha}, t_α = {t_alpha:.4f}"
    )
    print(f"Начальное число прогонов: N0 = {min_runs}")
    print(f"{'Итерация':<10} {'N':<8} {'Среднее':<12} {'σ':<12} {'N*':<8} {'Действие'}")
    print("-" * 65)

    N = min_runs
    iteration = 1
    while True:
        values = [simulate_func()[target_metric] for _ in range(N)]
        mean_val = mean(values)
        sigma = math.sqrt(variance(values)) if len(values) > 1 else 0.0
        N_star = calculate_required_runs(values, epsilon_rel, t_alpha)

        action = ""
        if N_star <= N:
            action = "Точность достигнута (N* ≤ N)"
        elif N_star > max_runs:
            action = f"N* > лимит ({max_runs}), остановка"
        else:
            action = f"Увеличиваем N до {N_star}"

        print(
            f"{iteration:<10} {N:<8} {mean_val:<12.4f} {sigma:<12.4f} {N_star:<8} {action}"
        )

        if N_star <= N or N_star > max_runs:
            final_N, final_values = N, values
            break
        else:
            N = N_star
            iteration += 1

    print(f"Итоговое число прогонов: {final_N}")
    return {
        "target_metric": target_metric,
        "metric_label": metric_label,
        "final_N": final_N,
        "mean": mean(final_values),
        "sigma": math.sqrt(variance(final_values)) if len(final_values) > 1 else 0.0,
        "epsilon_rel": epsilon_rel,
        "alpha": alpha,
        "t_alpha": t_alpha,
    }


def run_ab_test_example() -> None:
    print("\n" + "=" * 70)
    print("A/B ТЕСТИРОВАНИЕ: Оптимизация времени светофора")
    print("=" * 70)
    
    test = ABTest(
        test_name="Light Timing Optimization",
        variant_a=Variant(
            name="Conservative (30s/45s)",
            params={
                'GREEN_TIME_1': 30,
                'GREEN_TIME_2': 45,
            }
        ),
        variant_b=Variant(
            name="Aggressive (40s/55s)",
            params={
                'GREEN_TIME_1': 40,
                'GREEN_TIME_2': 55,
            }
        ),
        description="Comparing conservative vs aggressive traffic light timing strategies"
    )
    
    def apply_params(params):
        global GREEN_TIME_1, GREEN_TIME_2
        GREEN_TIME_1 = params.get('GREEN_TIME_1', GREEN_TIME_1)
        GREEN_TIME_2 = params.get('GREEN_TIME_2', GREEN_TIME_2)
    
    test.run(
        simulate_combined,
        num_runs=3,
        param_applier=apply_params,
    )
    
    test.print_summary([
        'avg_wait',
        'avg_travel',
        'throughput',
        'avg_queue',
    ])
    
    try:
        db = SessionLocal()
        from database import ABTest as ABTestModel
        ab_test_db = ABTestModel(
            id=test.id,
            test_name=test.test_name,
            description=test.description,
            variant_a_params=test.variant_a.params,
            variant_b_params=test.variant_b.params,
            num_runs_per_variant=test.run_count_per_variant,
            results_summary=test.get_summary_dict(['avg_wait', 'avg_travel', 'throughput']),
            status='completed',
        )
        db.add(ab_test_db)
        db.commit()
        db.close()
        print(f"\n✓ A/B test results saved to database: {test.id}")
    except Exception as e:
        print(f"✗ Error saving A/B test to database: {e}")


def sensitivity_analysis(
    simulate_func: Callable,
    param_name: str,
    param_values: List[float],
) -> List[Dict]:
    print(f"\nАнализ чувствительности к параметру '{param_name}': {param_values}")
    results = []
    original_value = globals().get(param_name)
    try:
        for value in param_values:
            globals()[param_name] = value
            res = simulate_func()
            results.append({"param_value": value, **res})
        print(f"\n{param_name:>10} | ожид(c) | проезд(c) | очер | пропуск(авт/с)")
        for r in results:
            print(
                f"  {r['param_value']:9.1f} | {r['avg_wait']:7.2f} | {r['avg_travel']:9.2f} | {r['avg_queue']:5.1f} | {r['throughput']:9.6f}"
            )
    finally:
        if original_value is not None:
            globals()[param_name] = original_value
    return results


def run_with_logging_demo() -> None:
    print("\n" + "=" * 70)
    print("ДЕМОНСТРАЦИЯ: Детальное логирование событий")
    print("=" * 70)
    
    sim_id = str(uuid.uuid4())[:8]
    print(f"Запуск симуляции с ID: {sim_id}")
    
    results = simulate_combined(simulation_id=sim_id, log_events=True)
    
    if event_logger:
        stats = event_logger.get_summary_stats()
        print(f"\n✓ Logged {stats['total_events']} events")
        
        print("\nВиды событий:")
        for event_type, count in stats['event_types'].items():
            if count > 0:
                print(f"  - {event_type}: {count}")
        
        print("\nПиковые очереди:")
        for queue, data in stats['queue_summary'].items():
            print(f"  - {queue}: макс={data['max_length']:.0f}, сред={data['avg_length']:.1f}")
        
        print(f"\nПробок обнаружено: {stats['traffic_jams_count']}")
        
        event_logger.export_json(f"simulation_{sim_id}_events.json")
        print(f"\n✓ Events exported to simulation_{sim_id}_events.json")
    
    save_simulation_to_db(results, f"logged_simulation_{sim_id}")


if __name__ == "__main__":
    print(f"T_MOD = {T_MOD} с, α = {ALPHA}")
    print(f"Относительная погрешность ε = {EPS_REL * 100:.0f}%")
    print(
        f"Вероятность объезда для W1 = {PROB_DETOUR * 100:.0f}%, светофора = {PROB_MAIN * 100:.0f}%"
    )
    print("W2 всегда через светофор, W3 — проселочный поток по объезду")

    init_db()

    print("\n" + "=" * 70)
    print("КОМБИНИРОВАННАЯ МОДЕЛЬ (светофор + объезд + проселочный поток)")
    print("=" * 70)

    print("\n--- 1. Метод по 10 прогонам ---")
    stability_check_10runs(
        lambda: simulate_combined(),
        [
            ("avg_travel", "Среднее время проезда"),
            ("avg_wait", "Среднее время ожидания"),
            ("avg_queue", "Средняя длина очереди"),
            ("throughput", "Пропускная способность"),
        ],
        epsilon_rel=EPS_REL,
    )

    res_combined = run_precision_iterative(
        lambda: simulate_combined(),
        "avg_travel",
        "Среднее время проезда",
        epsilon_rel=EPS_REL,
        alpha=ALPHA,
    )

    run_ab_test_example()
    run_with_logging_demo()

    print("\n" + "=" * 70)
    print("Analysis complete")
    print("Results saved to PostgreSQL")
    print("Setup Redash: python redash_setup.py")
    print("=" * 70)
