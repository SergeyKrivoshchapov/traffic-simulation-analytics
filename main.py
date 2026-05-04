import random
import math
from statistics import mean, variance
from typing import Dict, List, Callable, Tuple
import matplotlib.pyplot as plt

# -------------------- Параметры модели --------------------
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


def simulate_combined() -> Dict:
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
            next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

        while next_arrival2 <= current_time:
            queue2_light.append(next_arrival2)
            next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

        while next_rural <= current_time:
            rural_queue.append(current_time)
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
                        detour_in_transit.append(
                            (
                                current_time + DETOUR_TRAVEL_TIME,
                                {"arrival": current_time},
                            )
                        )

        green_end = current_time + GREEN_TIME_1
        next_entry_time = current_time

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
                next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

            while next_arrival2 <= current_time:
                queue2_light.append(next_arrival2)
                next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

            while next_rural <= current_time:
                rural_queue.append(current_time)
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

        current_time += SECTION_TRAVEL_TIME

        green_end = current_time + GREEN_TIME_2
        next_entry_time = current_time

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
                next_arrival1 += random.expovariate(1 / MEAN_ARRIVAL_1)

            while next_arrival2 <= current_time:
                queue2_light.append(next_arrival2)
                next_arrival2 += random.expovariate(1 / MEAN_ARRIVAL_2)

            while next_rural <= current_time:
                rural_queue.append(current_time)
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

            if queue2_light and current_time >= next_entry_time:
                arrival = queue2_light.pop(0)
                wait = current_time - arrival
                travel = wait + SECTION_TRAVEL_TIME
                total_wait_light += wait
                total_travel_light += travel
                total_cars_light += 1
                if wait < 0.001:
                    no_wait_light += 1
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

        current_time += SECTION_TRAVEL_TIME

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
        "avg_wait": avg_wait,
        "avg_travel": avg_travel,
        "avg_queue": avg_queue,
        "free_probability": free_prob,
        "throughput": throughput,
        "cars_served": total_cars,
        "cars_light": total_cars_light,
        "cars_detour": total_cars_detour,
        "cars_rural": total_cars_rural,
        "avg_wait_light": total_wait_light / total_cars_light
        if total_cars_light
        else 0,
        "avg_travel_light": total_travel_light / total_cars_light
        if total_cars_light
        else 0,
        "avg_wait_detour": total_wait_detour / total_cars_detour
        if total_cars_detour
        else 0,
        "avg_travel_detour": total_travel_detour / total_cars_detour
        if total_cars_detour
        else 0,
        "avg_wait_rural": total_wait_rural / total_cars_rural
        if total_cars_rural
        else 0,
        "avg_travel_rural": total_travel_rural / total_cars_rural
        if total_cars_rural
        else 0,
    }


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


def required_runs_for_Tmod(
    simulate_func: Callable,
    metric_key: str,
    T_values: List[float],
    epsilon_rel: float,
    alpha: float,
) -> List[Dict]:
    original_T = globals()["T_MOD"]
    t_alpha = get_t_alpha(alpha)
    results = []
    for T in T_values:
        globals()["T_MOD"] = T
        values = [simulate_func()[metric_key] for _ in range(50)]
        N = 50
        while True:
            var_val = variance(values) if len(values) > 1 else 0.0
            mean_v = mean(values) if values else 0
            if mean_v == 0 or var_val == 0:
                N_star = N
            else:
                epsilon_abs = epsilon_rel * mean_v
                N_star = math.ceil((t_alpha**2 * var_val) / (epsilon_abs**2))
            if N_star <= N or N_star > 5000:
                break
            values.extend(simulate_func()[metric_key] for _ in range(N_star - N))
            N = N_star
        results.append(
            {"T_mod": T, "T_mod_hrs": T / 3600, "N_star": N, "mean": mean(values)}
        )
    globals()["T_MOD"] = original_T
    return results


def print_Tmod_table(results: List[Dict], metric_label: str):
    print(f"\nПоказатель: {metric_label}")
    print(f"{'Эксперимент':<12} {'Tмод, час':<12} {'Число реализаций N*':<20}")
    print("-" * 45)
    for i, r in enumerate(results, 1):
        print(f"{i:<12} {r['T_mod_hrs']:<12.0f} {r['N_star']:<20}")


def sensitivity_analysis(
    simulate_func: Callable,
    param_name: str,
    param_values: List[float],
    original_params: Dict = None,
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


def plot_wait(g1, g2, a1, a2):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, data, name in [
        (axes[0, 0], g1, "GREEN_TIME_1"),
        (axes[0, 1], g2, "GREEN_TIME_2"),
        (axes[1, 0], a1, "MEAN_ARRIVAL_1"),
        (axes[1, 1], a2, "MEAN_ARRIVAL_2"),
    ]:
        x = [r["param_value"] for r in data]
        y = [r["avg_wait"] for r in data]
        ax.plot(x, y, "b-o")
        ax.set_xlabel(name)
        ax.set_ylabel("Среднее время ожидания")
        ax.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    print(f"T_MOD = {T_MOD} с, α = {ALPHA}")
    print(f"Относительная погрешность ε = {EPS_REL * 100:.0f}%")
    print(
        f"Вероятность объезда для W1 = {PROB_DETOUR * 100:.0f}%, светофора = {PROB_MAIN * 100:.0f}%"
    )
    print("W2 всегда через светофор, W3 — проселочный поток по объезду")

    print("\n" + "=" * 70)
    print("КОМБИНИРОВАННАЯ МОДЕЛЬ (светофор + объезд + проселочный поток)")
    print("=" * 70)

    print("\n--- 1. Метод по 10 прогонам ---")
    stability_check_10runs(
        simulate_combined,
        [
            ("avg_travel", "Среднее время проезда"),
            ("avg_wait", "Среднее время ожидания"),
            ("avg_queue", "Средняя длина очереди"),
            ("throughput", "Пропускная способность"),
        ],
        epsilon_rel=EPS_REL,
    )

    print("\n--- 2. Итерационный метод (N*) ---")
    res_combined = run_precision_iterative(
        simulate_combined,
        "avg_travel",
        "Среднее время проезда",
        epsilon_rel=EPS_REL,
        alpha=ALPHA,
    )

    print("\n--- 3. Зависимость N* от Tмод ---")
    T_values = [3600, 7200, 14400, 28800]
    print_Tmod_table(
        required_runs_for_Tmod(
            simulate_combined, "avg_travel", T_values, EPS_REL, ALPHA
        ),
        "Среднее время проезда",
    )

    print("\n" + "=" * 70)
    print("АНАЛИЗ ЧУВСТВИТЕЛЬНОСТИ")
    print("=" * 70)

    green1_vals = [
        15,
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        70,
        80,
        90,
        100,
        110,
        120,
        140,
        160,
        180,
        200,
        250,
        300,
        350,
        400,
        500,
        600,
    ]
    green2_vals = [
        15,
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        70,
        80,
        90,
        100,
        110,
        120,
        140,
        160,
        180,
        200,
        250,
        300,
        350,
        400,
        500,
        600,
    ]
    arr1_vals = [
        10,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        26,
        28,
        30,
        35,
        40,
        45,
        50,
        60,
        80,
        100,
        120,
        150,
        180,
        200,
        250,
        300,
    ]
    arr2_vals = [
        10,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        26,
        28,
        30,
        35,
        40,
        45,
        50,
        60,
        80,
        100,
        120,
        150,
        180,
        200,
        250,
        300,
    ]

    res_g1 = sensitivity_analysis(simulate_combined, "GREEN_TIME_1", green1_vals)
    res_g2 = sensitivity_analysis(simulate_combined, "GREEN_TIME_2", green2_vals)
    res_a1 = sensitivity_analysis(simulate_combined, "MEAN_ARRIVAL_1", arr1_vals)
    res_a2 = sensitivity_analysis(simulate_combined, "MEAN_ARRIVAL_2", arr2_vals)

    plot_wait(res_g1, res_g2, res_a1, res_a2)

    print("\n" + "=" * 70)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 70)
    print(
        f"Среднее время проезда = {res_combined['mean']:.2f} с (N={res_combined['final_N']})"
    )

    result = simulate_combined()
    print(f"Всего обслужено: {result['cars_served']:.0f}")
    print(
        f"  Через светофор (W1+W2): {result['cars_light']:.0f} (среднее время проезда {result['avg_travel_light']:.2f} с)"
    )
    print(
        f"  Через объезд (W1):       {result['cars_detour']:.0f} (среднее время проезда {result['avg_travel_detour']:.2f} с)"
    )
    print(
        f"  Проселочный (W3):        {result['cars_rural']:.0f} (среднее время проезда {result['avg_travel_rural']:.2f} с)"
    )
