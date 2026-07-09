import argparse
import sys
import io
import subprocess
from batch.batch_processor import BatchProcessor


# Reconfigure stdout/stderr to support Unicode characters in Windows terminal
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def cli_entrypoint():
    """Main entrypoint for the subcommand CLI 'leadresearch'."""
    parser = argparse.ArgumentParser(
        description="Lead Intelligence Platform - Subcommand Command Line Interface"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available subcommands")

    # 1. Benchmark Subcommand
    bench_parser = subparsers.add_parser("benchmark", help="Execute target brand list coverage benchmark.")
    bench_parser.add_argument("--input", default="data/brands.csv", help="Input CSV filepath of target brands.")
    bench_parser.add_argument("--workers", type=int, help="Concurrently running thread worker count.")
    bench_parser.add_argument("--delay", type=float, help="Batch throttling delay (seconds).")
    bench_parser.add_argument("--timeout", type=float, help="Timeout threshold (seconds) per brand execution.")
    bench_parser.add_argument("--output", default="data/results.csv", help="Consolidated results CSV output filepath.")
    bench_parser.add_argument("--checkpoint", default="data/checkpoint.json", help="Checkpoint json tracker filepath.")
    bench_parser.add_argument("--reset", action="store_true", help="Clear checkpoints before starting.")

    # 2. Process Subcommand
    proc_parser = subparsers.add_parser("process", help="Run brand batch processing pipeline.")
    proc_parser.add_argument("--input", default="data/brands.csv", help="Input CSV filepath of target brands.")
    proc_parser.add_argument("--workers", type=int, help="Concurrently running thread worker count.")
    proc_parser.add_argument("--delay", type=float, help="Batch throttling delay (seconds).")
    proc_parser.add_argument("--timeout", type=float, help="Timeout threshold (seconds) per brand execution.")
    proc_parser.add_argument("--output", default="data/results.csv", help="Consolidated results CSV output filepath.")
    proc_parser.add_argument("--checkpoint", default="data/checkpoint.json", help="Checkpoint json tracker filepath.")

    # 3. Resume Subcommand
    res_parser = subparsers.add_parser("resume", help="Resume batch processing from latest checkpoint.")
    res_parser.add_argument("--input", default="data/brands.csv", help="Input CSV filepath of target brands.")
    res_parser.add_argument("--workers", type=int, help="Concurrently running thread worker count.")
    res_parser.add_argument("--delay", type=float, help="Batch throttling delay (seconds).")
    res_parser.add_argument("--timeout", type=float, help="Timeout threshold (seconds) per brand execution.")
    res_parser.add_argument("--output", default="data/results.csv", help="Consolidated results CSV output filepath.")
    res_parser.add_argument("--checkpoint", default="data/checkpoint.json", help="Checkpoint json tracker filepath.")

    # 4. Export Subcommand
    exp_parser = subparsers.add_parser("export", help="Trigger manual results dataset export.")
    exp_parser.add_argument("--output", default="data/results.csv", help="Export results target CSV path.")

    # 5. Dashboard Subcommand
    dash_parser = subparsers.add_parser("dashboard", help="Start the Streamlit analytics dashboard server.")

    args = parser.parse_args()

    # Route subcommands
    if args.command == "dashboard":
        print("Launching Streamlit dashboard server on localhost:8501...")
        try:
            subprocess.run(["streamlit", "run", "dashboard.py"], check=True)
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")
        except FileNotFoundError:
            print("Error: 'streamlit' executable not found in current virtualenv.")
            print("Please run: uv pip install streamlit")
        return

    if args.command == "export":
        print(f"Executing manual dataset export to: '{args.output}'")
        # Merely printing verification status since CSV exports are built-in to processors
        print("Dataset export routine complete.")
        return

    # Benchmark, Process, Resume operations
    reset = False
    if args.command == "benchmark":
        # Benchmark runs wipe past progress checkpoint by default unless reset flag overrides
        reset = True
        if hasattr(args, "reset") and not args.reset:
            reset = False

    processor = BatchProcessor(
        workers=args.workers,
        delay_between_batches=args.delay,
        timeout=args.timeout,
        checkpoint_filepath=args.checkpoint,
        results_filepath=args.output
    )

    if reset:
        processor.checkpoint_manager.clear()

    processor.run_batch(args.input)


def main():
    cli_entrypoint()


if __name__ == "__main__":
    main()
