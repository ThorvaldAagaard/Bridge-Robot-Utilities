import platform
import time
import json
import os
import psutil
import numpy as np

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


def print_header(title):
    print(f"\n{'=' * 10} {title} {'=' * 10}")


def cpu_info():
    print_header("SYSTEM INFO")
    print("Platform:", platform.system(), platform.release())
    print("Processor:", platform.processor())
    print("CPU cores (logical/physical):", psutil.cpu_count(logical=True), "/", psutil.cpu_count(logical=False))
    print("RAM total (GB):", round(psutil.virtual_memory().total / 1e9, 2))
    print("Python version:", platform.python_version())
    if TF_AVAILABLE:
        print("TensorFlow version:", tf.__version__)
    print()


def benchmark_numpy():
    print_header("NUMPY BENCHMARK")
    timings = {}

    def matmul_test(n=2000):
        a = np.random.rand(n, n)
        b = np.random.rand(n, n)
        return a @ b

    t0 = time.time()
    matmul_test()
    t1 = time.time()
    timings['matmul'] = t1 - t0
    print(f"Matrix multiply 2000x2000: {timings['matmul']:.2f} s")

    t0 = time.time()
    np.linalg.svd(np.random.rand(1000, 1000))
    t1 = time.time()
    timings['svd'] = t1 - t0
    print(f"SVD 1000x1000: {timings['svd']:.2f} s")

    t0 = time.time()
    np.fft.fft(np.random.rand(10_000_000))
    t1 = time.time()
    timings['fft'] = t1 - t0
    print(f"FFT 10M samples: {timings['fft']:.2f} s")

    timings['numpy_total'] = timings['matmul'] + timings['svd'] + timings['fft']
    return timings['numpy_total']


def benchmark_tensorflow():
    if not TF_AVAILABLE:
        print_header("TENSORFLOW BENCHMARK")
        print("TensorFlow not installed.")
        return None

    print_header("TENSORFLOW BENCHMARK")
    x = tf.random.uniform((1000, 1000))
    t0 = time.time()
    for _ in range(50):
        _ = tf.matmul(x, x)
    tf_time = time.time() - t0
    print(f"50 matrix multiplications (1000x1000): {tf_time:.2f} s")
    return tf_time


def benchmark_io():
    print_header("DISK I/O BENCHMARK")
    data = b"x" * 100_000_000  # 100 MB
    filename = "temp_benchmark_file.bin"

    t0 = time.time()
    with open(filename, "wb") as f:
        f.write(data)
    write_time = time.time() - t0

    t0 = time.time()
    with open(filename, "rb") as f:
        _ = f.read()
    read_time = time.time() - t0

    os.remove(filename)

    print(f"Write 100MB: {write_time:.2f} s")
    print(f"Read 100MB:  {read_time:.2f} s")
    return write_time + read_time


def benchmark_json():
    print_header("JSON PARSING BENCHMARK")
    data = [{"x": np.random.rand(), "y": np.random.rand()} for _ in range(1_000_000)]

    t0 = time.time()
    js = json.dumps(data)
    t1 = time.time()
    json_serialize = t1 - t0

    t0 = time.time()
    _ = json.loads(js)
    t1 = time.time()
    json_deserialize = t1 - t0

    print(f"Serialize 1M small objects: {json_serialize:.2f} s")
    print(f"Deserialize 1M small objects: {json_deserialize:.2f} s")
    return json_serialize + json_deserialize


def compute_score(numpy_time, tf_time, io_time, json_time, reference=None):
    # Reference times: if None, we assume the current machine is 100
    # Lower times are better, so we invert: score = ref_time / current_time
    # Weight: numpy 40%, TF 30%, IO 20%, JSON 10%
    weights = {'numpy': 0.4, 'tf': 0.3, 'io': 0.2, 'json': 0.1}

    if reference is None:
        reference = {'numpy': numpy_time, 'tf': tf_time or 1, 'io': io_time, 'json': json_time}

    scores = {}
    scores['numpy'] = reference['numpy'] / numpy_time
    scores['tf'] = reference['tf'] / (tf_time or reference['tf'])
    scores['io'] = reference['io'] / io_time
    scores['json'] = reference['json'] / json_time

    # Weighted sum scaled to 100
    weighted_score = (scores['numpy'] * weights['numpy'] +
                      scores['tf'] * weights['tf'] +
                      scores['io'] * weights['io'] +
                      scores['json'] * weights['json']) * 100

    return weighted_score


def summary(score):
    print_header("SUMMARY")
    print(f"✅ Performance score: {score:.1f} / 100")
    print("Higher is better. Compare this number across machines to see relative performance.")


if __name__ == "__main__":
    print("System Benchmark, Version 1.0.17")
    cpu_info()
    numpy_time = benchmark_numpy()
    tf_time = benchmark_tensorflow()
    io_time = benchmark_io()
    json_time = benchmark_json()
    perf_score = compute_score(numpy_time, tf_time, io_time, json_time)
    summary(perf_score)
