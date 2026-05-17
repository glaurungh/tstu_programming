"""
Лабораторная работа №4: Сравнение алгоритмов

Профилирование времени и памяти для алгоритмов сортировки на входах разного размера с последующей визуализацией.

Алгоритмы:
1. Пузырьковая сортировка (O(n²))
2. Сортировка слиянием (O(n log n))
3. Встроенная Timsort (list.sort) (O(n log n))

"""

import argparse
import gc
import random
import statistics
import time
import tracemalloc
from functools import wraps
from typing import Callable, Any

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Настройки бенчмарка
# ---------------------------------------------------------------------------

SIZES: list[int] = [100, 300, 500, 1000, 2000, 5000, 10000, 20000]
M: int = 3                # количество запусков на каждую пару (алгоритм, N)
BUBBLE_MAX_N: int = 2000  # пузырьковая сортировка пропускается при N > порога

# ---------------------------------------------------------------------------
# Настройки графика
# ---------------------------------------------------------------------------

PLOT_FIG_SIZE: tuple[int, int] = (9, 8)
PLOT_DPI: int = 130
PLOT_LINE_WIDTH: float = 1.8
PLOT_MARKER_SIZE: int = 7
PLOT_LEGEND_FONT_SIZE: int = 9
PLOT_TITLE_FONT_SIZE: int = 12
PLOT_LABEL_FONT_SIZE: int = 10
PLOT_GRID_ALPHA: float = 0.8
PLOT_GRID_LINE_STYLE: str = "--"
PLOT_GRID_LINE_WIDTH: float = 0.5

PLOT_OUTPUT_FILE: str = "benchmark_results.png"

PLOT_TITLE_TIME: str  = "Сортировка: время выполнения / количество элементов"
PLOT_TITLE_MEM: str   = "Сортировка: пиковая память / количество элементов"
PLOT_XLABEL: str      = "Количество элементов (N)"
PLOT_YLABEL_TIME: str = "Время (секунды) [лог. шкала]"
PLOT_YLABEL_MEM: str  = "Пиковая память (байты) [лог. шкала]"

# цвета фона
PLOT_BG_FIGURE: str  = "#f7f6f2"
PLOT_BG_AXES: str    = "#f9f8f5"
PLOT_COLOR_TEXT: str = "#28251d"
PLOT_COLOR_GRID: str = "#dcd9d5"

# цвет и маркер для каждого алгоритма
ALGORITHM_STYLE: dict[str, tuple[str, str]] = {
    "Пузырьковая сортировка O(n^2)": ("#e05c4b", "o"),
    "Сортировка слиянием O(n log n)": ("#4b8fe0", "s"),
    "Timsort O(n log n)":             ("#4bc27c", "^"),
}

def profile_resources(func: Callable) -> Callable:
    """ Декоратор профилировщика """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float, int]:
        tracemalloc.start()
        start_time = time.perf_counter()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        execution_time = end_time - start_time
        return result, execution_time, peak_memory

    return wrapper


ALGORITHMS: dict[str, Callable] = {}

def register(name: str) -> Callable:
    """ Регистрация алгоритма """
    def decorator(func: Callable) -> Callable:
        ALGORITHMS[name] = func
        return func
    return decorator


@register("Пузырьковая сортировка O(n^2)")
@profile_resources
def bubble_sort(data: list) -> list:
    arr = data[:]
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr


@register("Сортировка слиянием O(n log n)")
@profile_resources
def merge_sort_entry(data: list) -> list:
    def _merge(left: list, right: list) -> list:
        result, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i]); i += 1
            else:
                result.append(right[j]); j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result

    def _sort(arr: list) -> list:
        if len(arr) <= 1:
            return arr
        mid = len(arr) // 2
        return _merge(_sort(arr[:mid]), _sort(arr[mid:]))

    return _sort(data[:])


@register("Timsort O(n log n)")
@profile_resources
def timsort(data: list) -> list:
    arr = data[:]
    arr.sort()
    return arr



def run_benchmarks() -> dict[str, dict[str, list]]:
    results: dict[str, dict[str, list]] = {
        name: {"times": [], "memories": []} for name in ALGORITHMS
    }

    for n in SIZES:
        base_data = random.sample(range(n * 10), n)
        print(f"N = {n}")

        for name, func in ALGORITHMS.items():
            if "Пузырьковая сортировка" in name and n > BUBBLE_MAX_N:
                results[name]["times"].append(None)
                results[name]["memories"].append(None)
                print(f"  {name}: пропущено (N > {BUBBLE_MAX_N})")
                continue

            run_times: list[float] = []
            run_mems: list[int] = []

            for _ in range(M):
                gc.collect()
                _, t, mem = func(base_data[:])
                run_times.append(t)
                run_mems.append(mem)

            median_time = statistics.median(run_times)
            median_mem  = statistics.median(run_mems)
            results[name]["times"].append(median_time)
            results[name]["memories"].append(median_mem)
            print(f"  {name}: time={median_time:.6f}s  mem={median_mem} bytes")

    return results

def _configure_ax(
    ax: plt.Axes,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    ax.set_facecolor(PLOT_BG_AXES)
    ax.grid(
        True,
        which="major",
        linestyle=PLOT_GRID_LINE_STYLE,
        linewidth=PLOT_GRID_LINE_WIDTH,
        color=PLOT_COLOR_GRID,
        alpha=PLOT_GRID_ALPHA,
    )
    ax.set_yscale("log")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(title, fontsize=PLOT_TITLE_FONT_SIZE,
                 fontweight="bold", pad=10, color=PLOT_COLOR_TEXT)
    ax.set_xlabel(xlabel, fontsize=PLOT_LABEL_FONT_SIZE, color=PLOT_COLOR_TEXT)
    ax.set_ylabel(ylabel, fontsize=PLOT_LABEL_FONT_SIZE, color=PLOT_COLOR_TEXT)


def plot_results(
    results: dict,
    sizes: list[int],
    save_to: str | None = None,
) -> None:
    fig, (ax_time, ax_mem) = plt.subplots(
        2, 1, figsize=PLOT_FIG_SIZE, dpi=PLOT_DPI
    )
    fig.patch.set_facecolor(PLOT_BG_FIGURE)

    _configure_ax(ax_time, PLOT_TITLE_TIME, PLOT_XLABEL, PLOT_YLABEL_TIME)
    _configure_ax(ax_mem,  PLOT_TITLE_MEM,  PLOT_XLABEL, PLOT_YLABEL_MEM)

    for name, data in results.items():
        color, marker = ALGORITHM_STYLE[name]
        valid = [
            (s, t, m)
            for s, t, m in zip(sizes, data["times"], data["memories"])
            if t is not None
        ]
        xs = [v[0] for v in valid]
        ts = [v[1] for v in valid]
        ms = [v[2] for v in valid]

        ax_time.plot(
            xs, ts, label=name, color=color,
            marker=marker, linewidth=PLOT_LINE_WIDTH, markersize=PLOT_MARKER_SIZE,
        )
        ax_mem.plot(
            xs, ms, label=name, color=color,
            marker=marker, linewidth=PLOT_LINE_WIDTH, markersize=PLOT_MARKER_SIZE,
        )

    ax_time.legend(fontsize=PLOT_LEGEND_FONT_SIZE, framealpha=0.9)
    ax_mem.legend(fontsize=PLOT_LEGEND_FONT_SIZE, framealpha=0.9)

    plt.tight_layout(pad=2.5)

    if save_to:
        plt.savefig(save_to, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"График сохранен: {save_to}")

    plt.show()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Сравнение алгоритмов сортировки"
    )
    parser.add_argument(
        "--save",
        nargs="?",
        const=PLOT_OUTPUT_FILE,
        help=(
            f"Сохранить график в PNG-файл. "
            f"Без аргумента сохраняет в '{PLOT_OUTPUT_FILE}'."
        ),
    )
    args = parser.parse_args()

    benchmark_results = run_benchmarks()
    plot_results(benchmark_results, SIZES, save_to=args.save)
