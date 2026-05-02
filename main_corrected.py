import random
import math
from statistics import mean, variance
from typing import Dict, List, Callable
import matplotlib.pyplot as plt

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

EPSILON = 0.1
ALPHA = 0.95

ALPHA_TO_T = {
    0.80: 1.28,
    0.85: 1.44,
    0.90: 1.645,
    0.95: 1.96,
    0.99: 2.576,
}


def get_t_alpha(alpha: float) -> float:
    if alpha in ALPHA_TO_T:
        return ALPHA_TO_T[alpha]

    sorted_alphas = sorted(ALPHA_TO_T.keys())
    for i in range(len(sorted_alphas) - 1):
        a1, a2 = sorted_alphas[i], sorted_alphas[i + 1]
        if a1 < alpha < a2:
            t1, t2 = ALPHA_TO_T[a1], ALPHA_TO_T[a2]
            return t1 + (t2 - t1) * (alpha - a1) / (a2 - a1)

    raise ValueError(
        f"Доверительная вероятность alpha={alpha} вне поддерживаемого диапазона"
    )


T_ALPHA = get_t_alpha(ALPHA)


def simulate_main_route() -> Dict:
    current_time = 0
    queue1 = []
    queue2 = []

    next_arrival1 = random.expovariate(1 / MEAN_ARRIVAL_1)
    next_arrival2 = random.expovariate(1 / MEAN_ARRIVAL_2)

    total_wait = 0
    total_travel = 0
    total_cars = 0
    no_wait_cars = 0

    queue_sum = 0
    queue_measurements = 0

    while current_time < T_MOD:
        green_end = current_time + GREEN_TIME_1
        next_entry_time = current_time

        while current_time < green_end and current_time < T_MOD:
            while next_arrival1 <= current_time:
                queue1.append(next_arrival1)
                next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

            while next_arrival2 <= current_time:
                queue2.append(next_arrival2)
                next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

            queue_sum += len(queue1) + len(queue2)
            queue_measurements += 1

            if queue1 and current_time >= next_entry_time:
                arrival_time = queue1.pop(0)
                wait_time = current_time - arrival_time
                travel_time = wait_time + SECTION_TRAVEL_TIME

                total_wait += wait_time
                total_travel += travel_time
                total_cars += 1
                if wait_time < 0.001:
                    no_wait_cars += 1

                next_entry_time = current_time + ENTRY_INTERVAL

            current_time += 1

        current_time += SECTION_TRAVEL_TIME

        green_end = current_time + GREEN_TIME_2
        next_entry_time = current_time

        while current_time < green_end and current_time < T_MOD:
            while next_arrival1 <= current_time:
                queue1.append(next_arrival1)
                next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

            while next_arrival2 <= current_time:
                queue2.append(next_arrival2)
                next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

            queue_sum += len(queue1) + len(queue2)
            queue_measurements += 1

            if queue2 and current_time >= next_entry_time:
                arrival_time = queue2.pop(0)
                wait_time = current_time - arrival_time
                travel_time = wait_time + SECTION_TRAVEL_TIME

                total_wait += wait_time
                total_travel += travel_time
                total_cars += 1
                if wait_time < 0.001:
                    no_wait_cars += 1

                next_entry_time = current_time + ENTRY_INTERVAL

            current_time += 1

        current_time += SECTION_TRAVEL_TIME

    if total_cars > 0:
        avg_wait = total_wait / total_cars
        avg_travel = total_travel / total_cars
        free_probability = no_wait_cars / total_cars
    else:
        avg_wait = avg_travel = free_probability = 0.0

    avg_queue = queue_sum / queue_measurements if queue_measurements else 0
    throughput = total_cars / T_MOD

    return {
        "avg_wait": avg_wait,
        "avg_travel": avg_travel,
        "avg_queue": avg_queue,
        "free_probability": free_probability,
        "throughput": throughput,
        "cars_served": total_cars,
    }


def simulate_detour() -> Dict:
    total_travel = 0
    total_wait = 0
    total_cars = 0
    no_wait_cars = 0

    detour_queue = []

    next_arrival1 = random.expovariate(1 / MEAN_ARRIVAL_1)
    next_arrival2 = random.expovariate(1 / MEAN_ARRIVAL_2)

    valve_available_time = 0

    queue_sum = 0
    queue_measurements = 0

    current_time = 0

    while current_time < T_MOD:
        next_event_time = min(
            next_arrival1, next_arrival2, max(valve_available_time, current_time)
        )

        if next_event_time > T_MOD:
            break

        current_time = next_event_time

        queue_sum += len(detour_queue)
        queue_measurements += 1

        if current_time == next_arrival1:
            detour_queue.append({"arrival_time": current_time, "direction": 1})
            next_arrival1 = current_time + random.expovariate(1 / MEAN_ARRIVAL_1)

        elif current_time == next_arrival2:
            detour_queue.append({"arrival_time": current_time, "direction": 2})
            next_arrival2 = current_time + random.expovariate(1 / MEAN_ARRIVAL_2)

        elif current_time >= valve_available_time:
            valve_available_time = current_time

            if detour_queue:
                car = detour_queue.pop(0)
                wait_time = current_time - car["arrival_time"]
                travel_time = wait_time + DETOUR_TRAVEL_TIME + TURN_TIME

                total_wait += wait_time
                total_travel += travel_time
                total_cars += 1

                if wait_time < 0.001:
                    no_wait_cars += 1

                valve_available_time = current_time + random.expovariate(1 / MEAN_RURAL)
            else:
                valve_available_time = current_time

    if total_cars > 0:
        avg_wait = total_wait / total_cars
        avg_travel = total_travel / total_cars
        free_probability = no_wait_cars / total_cars
    else:
        avg_wait = avg_travel = free_probability = 0.0

    avg_queue = queue_sum / queue_measurements if queue_measurements else 0
    throughput = total_cars / T_MOD

    return {
        "avg_wait": avg_wait,
        "avg_travel": avg_travel,
        "avg_queue": avg_queue,
        "free_probability": free_probability,
        "throughput": throughput,
        "cars_served": total_cars,
    }


def simulate_detour() -> Dict:
    total_travel = 0
    total_wait = 0
    total_cars = 0
    no_wait_cars = 0

    detour_queue1 = []
    detour_queue2 = []

    next_arrival1 = random.expovariate(1 / MEAN_ARRIVAL_1)
    next_arrival2 = random.expovariate(1 / MEAN_ARRIVAL_2)

    valve1_available_time = 0
    valve2_available_time = 0

    queue_sum = 0
    queue_measurements = 0

    for current_time in range(T_MOD):
        while next_arrival1 <= current_time:
            detour_queue1.append({"arrival_time": current_time, "direction": 1})
            next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

        while next_arrival2 <= current_time:
            detour_queue2.append({"arrival_time": current_time, "direction": 2})
            next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

        queue_sum += len(detour_queue1) + len(detour_queue2)
        queue_measurements += 1

        if current_time >= valve1_available_time and detour_queue1:
            car = detour_queue1.pop(0)
            wait_time = current_time - car["arrival_time"]
            travel_time = wait_time + DETOUR_TRAVEL_TIME + TURN_TIME

            total_wait += wait_time
            total_travel += travel_time
            total_cars += 1

            if wait_time < 0.001:
                no_wait_cars += 1

            service_time = random.expovariate(1 / MEAN_RURAL)
            valve1_available_time = current_time + service_time

        if current_time >= valve2_available_time and detour_queue2:
            car = detour_queue2.pop(0)
            wait_time = current_time - car["arrival_time"]
            travel_time = wait_time + DETOUR_TRAVEL_TIME + TURN_TIME

            total_wait += wait_time
            total_travel += travel_time
            total_cars += 1

            if wait_time < 0.001:
                no_wait_cars += 1

            service_time = random.expovariate(1 / MEAN_RURAL)
            valve2_available_time = current_time + service_time

    if total_cars > 0:
        avg_wait = total_wait / total_cars
        avg_travel = total_travel / total_cars
        free_probability = no_wait_cars / total_cars
    else:
        avg_wait = avg_travel = free_probability = 0.0

    avg_queue = queue_sum / queue_measurements if queue_measurements else 0
    throughput = total_cars / T_MOD

    return {
        "avg_wait": avg_wait,
        "avg_travel": avg_travel,
        "avg_queue": avg_queue,
        "free_probability": free_probability,
        "throughput": throughput,
        "cars_served": total_cars,
    }


def calculate_required_runs(values: List[float], epsilon: float, t_alpha: float) -> int:
    n = len(values)
    if n < 2:
        return n * 2

    mean_val = mean(values)
    if mean_val == 0:
        return n * 2

    var_val = variance(values)
    if var_val == 0:
        return n

    required = math.ceil((t_alpha**2 * var_val) / (epsilon**2))
    return max(required, n)


def run_with_precision(
    simulate_func: Callable,
    epsilon: float = EPSILON,
    alpha: float = ALPHA,
    min_runs: int = 50,
    max_runs: int = 5000,
    target_metric: str = "avg_travel",
) -> Dict:
    t_alpha = get_t_alpha(alpha)

    print(
        f"Обеспечение точности {epsilon * 100:.0f}% (α = {alpha}, t_α = {t_alpha:.4f}) для {simulate_func.__name__}"
    )

    N = min_runs
    iteration = 1
    all_results = []

    while True:
        print(f"  Этап {iteration}: N = {N} прогонов")

        metrics = {
            "avg_wait": [],
            "avg_travel": [],
            "avg_queue": [],
            "free_probability": [],
            "throughput": [],
            "cars_served": [],
        }

        for i in range(N):
            result = simulate_func()
            for key in metrics:
                val = result.get(key, 0)
                metrics[key].append(val)

        all_results.append(
            {
                "N": N,
                "means": {k: mean(v) for k, v in metrics.items()},
                "vars": {
                    k: variance(v) if len(v) > 1 else 0 for k, v in metrics.items()
                },
            }
        )

        target_values = metrics[target_metric]
        N_star = calculate_required_runs(target_values, epsilon, t_alpha)

        print(f"    Среднее {target_metric} = {mean(target_values):.4f}")
        print(
            f"    Стандартное отклонение {target_metric} = {math.sqrt(variance(target_values)):.4f}"
        )
        print(f"    Требуется прогонов N* = {N_star}")

        if N_star > N and N_star <= max_runs:
            N = N_star
            iteration += 1
        else:
            if N_star > max_runs:
                print(f"    Требуется N* = {N_star}, но лимит = {max_runs}")
            print(f"    Точность достигнута за {iteration} итерацию(й)")
            break

    final_means = all_results[-1]["means"]
    final_vars = all_results[-1]["vars"]

    return {
        "means": final_means,
        "vars": final_vars,
        "final_N": N,
        "iterations": iteration,
        "history": all_results,
        "alpha": alpha,
        "t_alpha": t_alpha,
        "epsilon": epsilon,
    }


def run_stability_check(simulate_func: Callable, num_runs: int = 10) -> List[Dict]:
    print(f"\n Проверка устойчивости ({num_runs} прогонов)")

    results = []
    for i in range(num_runs):
        result = simulate_func()
        results.append(result)

    metrics_names = ["avg_wait", "avg_travel", "avg_queue", "throughput"]
    metrics_labels = [
        "Среднее время ожидания",
        "Среднее время проезда",
        "Средняя длина очереди",
        "Пропускная способность",
    ]

    print(f"\n{'Метрика':<30} | мин | макс | сред | разброс(%)")
    print("-" * 75)

    for i, metric in enumerate(metrics_names):
        values = [r[metric] for r in results]
        min_val = min(values)
        max_val = max(values)
        mean_val = mean(values)
        spread = (max_val - min_val) / mean_val * 100 if mean_val > 0 else 0

        print(
            f"{metrics_labels[i]:<30} | {min_val:5.2f} | {max_val:5.2f} | {mean_val:5.2f} | {spread:6.1f}%"
        )

    return results


def sensitivity_analysis(
    simulate_func: Callable,
    param_name: str,
    param_values: List[float],
    original_params: Dict = None,
) -> List[Dict]:
    print(f"\nАнализ чувствительности к параметру '{param_name}'")
    print(f"   Значения: {param_values}")

    results = []
    original_value = globals().get(param_name)

    try:
        for value in param_values:
            globals()[param_name] = value
            result = simulate_func()
            results.append(
                {
                    "param_value": value,
                    "avg_wait": result["avg_wait"],
                    "avg_travel": result["avg_travel"],
                    "avg_queue": result["avg_queue"],
                    "throughput": result["throughput"],
                }
            )

        print(f"\n{param_name:>10} | ожид(c) | проезд(c) | очер | пропуск(авт/с)")
        for r in results:
            print(
                f"  {r['param_value']:9.1f} | {r['avg_wait']:7.2f} | {r['avg_travel']:9.2f} | {r['avg_queue']:5.1f} | {r['throughput']:9.6f}"
            )
    finally:
        if original_value is not None:
            globals()[param_name] = original_value

    return results


def plot_sensitivity(metric_name, x_values, y_values, x_label, y_label, title):
    plt.figure(figsize=(10, 6))
    plt.plot(x_values, y_values, "b-o", linewidth=2, markersize=8)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.title(title, fontsize=14)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()


def plot_all_wait_times(
    green1_results, green2_results, arrival1_results, arrival2_results
):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    param_configs = [
        (axes[0, 0], green1_results, "GREEN_TIME_1", "GREEN_TIME_1 (с)"),
        (axes[0, 1], green2_results, "GREEN_TIME_2", "GREEN_TIME_2 (с)"),
        (axes[1, 0], arrival1_results, "MEAN_ARRIVAL_1", "MEAN_ARRIVAL_1 (с)"),
        (axes[1, 1], arrival2_results, "MEAN_ARRIVAL_2", "MEAN_ARRIVAL_2 (с)"),
    ]

    for ax, results, param_name, x_label in param_configs:
        x_values = [r["param_value"] for r in results]
        y_values = [r["avg_wait"] for r in results]

        ax.plot(x_values, y_values, "b-o", linewidth=2, markersize=8)
        ax.set_xlabel(x_label, fontsize=11)
        ax.set_ylabel("Среднее время ожидания (с)", fontsize=11)
        ax.set_title(
            f"Зависимость среднего времени ожидания от {param_name}", fontsize=12
        )
        ax.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.show()


def plot_all_wait_times_detour(arrival1_results, arrival2_results, rural_results):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    param_configs = [
        (axes[0], arrival1_results, "MEAN_ARRIVAL_1", "MEAN_ARRIVAL_1 (с)"),
        (axes[1], arrival2_results, "MEAN_ARRIVAL_2", "MEAN_ARRIVAL_2 (с)"),
        (axes[2], rural_results, "MEAN_RURAL", "MEAN_RURAL (с)"),
    ]

    for ax, results, param_name, x_label in param_configs:
        x_values = [r["param_value"] for r in results]
        y_values = [r["avg_wait"] for r in results]

        ax.plot(x_values, y_values, "b-o", linewidth=2, markersize=8)
        ax.set_xlabel(x_label, fontsize=11)
        ax.set_ylabel("Среднее время ожидания (с)", fontsize=11)
        ax.set_title(
            f"Зависимость среднего времени ожидания от {param_name}", fontsize=12
        )
        ax.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    print(f"Время моделирования: {T_MOD} секунд, ALPHA = {ALPHA}, EPSILON = {EPSILON}")

    print("1. ОСНОВНОЙ МАРШРУТ")

    main_precision = run_with_precision(
        simulate_main_route, epsilon=EPSILON, alpha=ALPHA, target_metric="avg_travel"
    )

    print(f"\nИТОГОВЫЕ РЕЗУЛЬТАТЫ (Основной путь)")
    print(f"  Число прогонов: {main_precision['final_N']}")
    print(f"  Число итераций: {main_precision['iterations']}")
    print(f"  Доверительная вероятность: {main_precision['alpha']}")
    print(f"\n  Средние значения показателей:")
    print(
        f"    Среднее время ожидания        : {main_precision['means']['avg_wait']:.4f} с"
    )
    print(
        f"    Среднее время проезда         : {main_precision['means']['avg_travel']:.4f} с"
    )
    print(
        f"    Средняя длина очереди         : {main_precision['means']['avg_queue']:.4f} авт"
    )
    print(
        f"    Вероятность проезда без ожид  : {main_precision['means']['free_probability']:.4f}"
    )
    print(
        f"    Пропускная способность        : {main_precision['means']['throughput']:.6f} авт/с"
    )
    print(
        f"    Обслужено автомобилей         : {main_precision['means']['cars_served']:.0f}"
    )

    print("\n" + "=" * 60)
    print("ПРОВЕРКА УСТОЙЧИВОСТИ ОСНОВНОГО МАРШРУТА")
    print("=" * 60)
    stability_results_main = run_stability_check(simulate_main_route, num_runs=10)

    print("\n" + "=" * 60)
    print("АНАЛИЗ ЧУВСТВИТЕЛЬНОСТИ ДЛЯ ОСНОВНОГО МАРШРУТА")
    print("=" * 60)

    green1_values = [30, 45, 60, 75, 90, 105, 120]
    green2_values = [30, 45, 60, 75, 90, 105, 120]
    arrival1_values = [6, 8, 10, 12, 14, 16, 18]
    arrival2_values = [6, 8, 10, 12, 14, 16, 18]

    sensitivity_results_green1 = sensitivity_analysis(
        simulate_main_route, "GREEN_TIME_1", green1_values
    )

    sensitivity_results_green2 = sensitivity_analysis(
        simulate_main_route, "GREEN_TIME_2", green2_values
    )

    sensitivity_results_arrival1 = sensitivity_analysis(
        simulate_main_route, "MEAN_ARRIVAL_1", arrival1_values
    )

    sensitivity_results_arrival2 = sensitivity_analysis(
        simulate_main_route, "MEAN_ARRIVAL_2", arrival2_values
    )

    plot_all_wait_times(
        sensitivity_results_green1,
        sensitivity_results_green2,
        sensitivity_results_arrival1,
        sensitivity_results_arrival2,
    )

    print("\n" + "=" * 60)
    print("2. ОБЪЕЗД (альтернативный маршрут)")
    print("=" * 60)

    detour_precision = run_with_precision(
        simulate_detour, epsilon=EPSILON, alpha=ALPHA, target_metric="avg_travel"
    )

    print(f"\nИТОГОВЫЕ РЕЗУЛЬТАТЫ (Объезд)")
    print(f"  Число прогонов: {detour_precision['final_N']}")
    print(f"  Число итераций: {detour_precision['iterations']}")
    print(f"  Доверительная вероятность: {detour_precision['alpha']}")
    print(f"\n  Средние значения показателей:")
    print(
        f"    Среднее время ожидания        : {detour_precision['means']['avg_wait']:.4f} с"
    )
    print(
        f"    Среднее время проезда         : {detour_precision['means']['avg_travel']:.4f} с"
    )
    print(
        f"    Средняя длина очереди         : {detour_precision['means']['avg_queue']:.4f} авт"
    )
    print(
        f"    Пропускная способность        : {detour_precision['means']['throughput']:.6f} авт/с"
    )
    print(
        f"    Обслужено автомобилей         : {detour_precision['means']['cars_served']:.0f}"
    )

    print("\n" + "=" * 60)
    print("ПРОВЕРКА УСТОЙЧИВОСТИ ОБЪЕЗДА")
    print("=" * 60)
    stability_results_detour = run_stability_check(simulate_detour, num_runs=10)

    print("\n" + "=" * 60)
    print("АНАЛИЗ ЧУВСТВИТЕЛЬНОСТИ ДЛЯ ОБЪЕЗДА")
    print("=" * 60)

    rural_values = [5, 10, 15, 20, 25, 30, 35]

    detour_sensitivity_arrival1 = sensitivity_analysis(
        simulate_detour, "MEAN_ARRIVAL_1", arrival1_values
    )

    detour_sensitivity_arrival2 = sensitivity_analysis(
        simulate_detour, "MEAN_ARRIVAL_2", arrival2_values
    )

    detour_sensitivity_rural = sensitivity_analysis(
        simulate_detour, "MEAN_RURAL", rural_values
    )

    plot_all_wait_times_detour(
        detour_sensitivity_arrival1,
        detour_sensitivity_arrival2,
        detour_sensitivity_rural,
    )

    print("3. СРАВНЕНИЕ МАРШРУТОВ")

    delta = (
        detour_precision["means"]["avg_travel"] - main_precision["means"]["avg_travel"]
    )
    if delta > 0:
        print(f"\nОсновной путь эффективнее на {delta:.2f} с")
    elif delta < 0:
        print(f"\nОбъезд эффективнее на {abs(delta):.2f} с")
    else:
        print("\nОба варианта одинаково эффективны")
