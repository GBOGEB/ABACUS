from . import metrics, truth_matrix, validate, runtime


def main():
    runtime.start()
    print("[OK] Runtime Started")

    metrics.load()
    print("[OK] Metrics Loaded")

    truth_matrix.load()
    print("[OK] Truth Matrix Loaded")

    validate.ready()
    print("[OK] Validation Ready")


if __name__ == "__main__":
    main()
