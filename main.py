import random
import math
from statistics import mean, variance

T_MOD = 10000

MEAN_ARRIVAL_1 = 12
MEAN_ARRIVAL_2 = 8
GREEN_TIME_1 = 60
GREEN_TIME_2 = 60
ENTRY_INTERVAL = 2
SECTION_TRAVEL_TIME = 10

DETOUR_TRAVEL_TIME = 300
MEAN_RURAL = 20
TURN_TIME = 5

EPSILON = 0.2
ALPHA = 0.95
T_ALPHA = 1.96


def simulate_main_route():
    current_time = 0
    queue1 = []
    queue2 = []

    next_arrival1 = random.expovariate(1 / MEAN_ARRIVAL_1)
    next_arrival2 = random.expovariate(1 / MEAN_ARRIVAL_2)

    total_wait = 0
    total_travel = 0
    total_cars = 0
    no_wait_cars = 0

    lost_cars1 = 0
    lost_cars2 = 0

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
                if wait_time == 0:
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
                if wait_time == 0:
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
        "lost_cars1": lost_cars1,
        "lost_cars2": lost_cars2,
    }


def simulate_detour():
    current_time = 0
    queue_detour = []
    total_wait = 0
    total_travel = 0
    total_cars = 0
    lost_cars = 0

    queue_sum = 0
    queue_measurements = 0

    next_arrival = random.expovariate(1 / MEAN_ARRIVAL_1)

    while current_time < T_MOD:
        current_time = next_arrival
        arrival_time = current_time

        current_time += DETOUR_TRAVEL_TIME

        queue_detour.append(current_time)

        while queue_detour and current_time < T_MOD:
            queue_sum += len(queue_detour)
            queue_measurements += 1

            gap = random.expovariate(1 / MEAN_RURAL)
            if gap >= TURN_TIME:
                arrive_at_turn = queue_detour.pop(0)
                wait_time = current_time - arrive_at_turn
                total_wait += wait_time
                current_time += TURN_TIME
                travel_time = current_time - arrival_time
                total_travel += travel_time
                total_cars += 1
                break
            else:
                current_time += gap

        next_arrival = arrival_time + random.expovariate(1 / MEAN_ARRIVAL_1)

    if total_cars > 0:
        avg_wait = total_wait / total_cars
        avg_travel = total_travel / total_cars
    else:
        avg_wait = avg_travel = 0.0

    avg_queue = queue_sum / queue_measurements if queue_measurements else 0
    throughput = total_cars / T_MOD

    return {
        "avg_wait": avg_wait,
        "avg_travel": avg_travel,
        "avg_queue": avg_queue,
        "throughput": throughput,
        "cars_served": total_cars,
        "lost_cars": lost_cars,
    }


def calculate_required_runs(values, epsilon, t_alpha):
    n = len(values)
    if n < 2:
        return n * 2

    mean_val = mean(values)
    if mean_val == 0:
        return n * 2

    var_val = variance(values)
    if var_val == 0:
        return n

    required = math.ceil((t_alpha**2 * var_val) / ((epsilon * mean_val) ** 2))
    return max(required, n)


def run_with_precision(
    simulate_func,
    epsilon=EPSILON,
    alpha=ALPHA,
    t_alpha=T_ALPHA,
    min_runs=50,
    max_runs=5000,
    target_metric="avg_travel",
):
    print(f"Обеспечение точности {epsilon * 100:.0f}% для {simulate_func.__name__}")

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
            "lost_cars": [],
        }

        for i in range(N):
            result = simulate_func()
            for key in metrics:
                if key == "lost_cars":
                    if simulate_func.__name__ == "simulate_main_route":
                        val = result.get("lost_cars1", 0) + result.get("lost_cars2", 0)
                    else:
                        val = result.get("lost_cars", 0)
                else:
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
        print(f"    Дисперсия {target_metric} = {variance(target_values):.4f}")
        print(f"    Требуется прогонов N* = {N_star}")

        if N_star > N and N_star <= max_runs:
            N = N_star
            iteration += 1
        else:
            if N_star > max_runs:
                print(f"    Достигнут лимит прогонов ({max_runs})")
            print(f"    Точность достигнута")
            break

    final_means = all_results[-1]["means"]
    final_vars = all_results[-1]["vars"]

    return {
        "means": final_means,
        "vars": final_vars,
        "final_N": N,
        "iterations": iteration,
        "history": all_results,
    }


def run_stability_check(simulate_func, num_runs=10):
    print(f"Проверка устойчивости ({num_runs} прогонов)")

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

    for i, metric in enumerate(metrics_names):
        values = [r[metric] for r in results]
        min_val = min(values)
        max_val = max(values)
        mean_val = mean(values)
        spread = (max_val - min_val) / mean_val * 100 if mean_val > 0 else 0

        print(
            f"  {metrics_labels[i]:30s}: мин={min_val:.3f}, макс={max_val:.3f}, сред={mean_val:.3f}, разброс={spread:.1f}%"
        )

    return results


def sensitivity_analysis(simulate_func, param_name, param_values):
    print(f"Анализ чувствительности к параметру '{param_name}'")

    results = []
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

    print(f"\n  {param_name:>10} | ожид | проезд | очер | пропуск")
    for r in results:
        print(
            f"  {r['param_value']:10.1f} | {r['avg_wait']:5.1f} | {r['avg_travel']:6.1f} | {r['avg_queue']:5.1f} | {r['throughput']:9.4f}"
        )

    return results


if __name__ == "__main__":
    main_precision = run_with_precision(
        simulate_main_route, epsilon=0.2, target_metric="avg_travel"
    )

    print(f"\nИТОГОВЫЕ РЕЗУЛЬТАТЫ (Основной путь)")
    print(f"Число прогонов: {main_precision['final_N']}")
    print(f"Число итераций: {main_precision['iterations']}")
    print(f"Средние значения показателей:")
    print(
        f"  Среднее время ожидания        : {main_precision['means']['avg_wait']:.4f} с"
    )
    print(
        f"  Среднее время проезда         : {main_precision['means']['avg_travel']:.4f} с"
    )
    print(
        f"  Средняя длина очереди         : {main_precision['means']['avg_queue']:.4f} авт"
    )
    print(
        f"  Вероятность проезда без ожид  : {main_precision['means']['free_probability']:.4f}"
    )
    print(
        f"  Пропускная способность        : {main_precision['means']['throughput']:.4f} авт/с"
    )
    print(
        f"  Обслужено автомобилей         : {main_precision['means']['cars_served']:.0f}"
    )
    print(
        f"  Потеряно автомобилей          : {main_precision['means']['lost_cars']:.0f}"
    )

    detour_precision = run_with_precision(
        simulate_detour, epsilon=0.2, target_metric="avg_travel"
    )

    print(f"\nИТОГОВЫЕ РЕЗУЛЬТАТЫ (Объезд)")
    print(f"Число прогонов: {detour_precision['final_N']}")
    print(f"Число итераций: {detour_precision['iterations']}")
    print(f"Средние значения показателей:")
    print(
        f"  Среднее время ожидания        : {detour_precision['means']['avg_wait']:.4f} с"
    )
    print(
        f"  Среднее время проезда         : {detour_precision['means']['avg_travel']:.4f} с"
    )
    print(
        f"  Средняя длина очереди         : {detour_precision['means']['avg_queue']:.4f} авт"
    )
    print(
        f"  Пропускная способность        : {detour_precision['means']['throughput']:.4f} авт/с"
    )
    print(
        f"  Обслужено автомобилей         : {detour_precision['means']['cars_served']:.0f}"
    )
    print(
        f"  Потеряно автомобилей          : {detour_precision['means']['lost_cars']:.0f}"
    )

    print()
    stability_results = run_stability_check(simulate_main_route, num_runs=10)

    print()
    sensitivity_results = sensitivity_analysis(
        simulate_main_route, "GREEN_TIME_1", [30, 45, 60, 75, 90, 105, 120]
    )

    print()
    delta = (
        detour_precision["means"]["avg_travel"] - main_precision["means"]["avg_travel"]
    )
    if delta > 0:
        print(f"Основной путь эффективнее на {delta:.2f} с")
    elif delta < 0:
        print(f"Объезд эффективнее на {abs(delta):.2f} с")
    else:
        print("Оба варианта одинаково эффективны")
