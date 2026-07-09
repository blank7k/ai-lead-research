import argparse
import sys
import io
from batch.batch_processor import BatchProcessor


# Reconfigure stdout/stderr to support Unicode characters in Windows terminal
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description="Lead Intelligence Platform - Benchmark & Batch Processing Module CLI"
    )
    parser.add_argument(
        "--input", 
        default="data/brands.csv", 
        help="Path to the input CSV file containing brand names."
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=3, 
        help="Concurrently running ThreadPoolExecutor worker count."
    )
    parser.add_argument(
        "--delay", 
        type=float, 
        default=2.0, 
        help="Throttling delay sleep (seconds) between batch iterations."
    )
    parser.add_argument(
        "--timeout", 
        type=float, 
        default=120.0, 
        help="Timeout threshold (seconds) for individual brand graph executions."
    )
    parser.add_argument(
        "--output", 
        default="data/results.csv", 
        help="Path to write the consolidated CSV results."
    )
    parser.add_argument(
        "--checkpoint", 
        default="data/checkpoint.json", 
        help="Filepath of the progress checkpoint json tracker."
    )
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Clear progress checkpoint cache before starting execution run."
    )

    args = parser.parse_args()

    # Instantiate and configure BatchProcessor
    processor = BatchProcessor(
        workers=args.workers,
        delay_between_batches=args.delay,
        timeout=args.timeout,
        checkpoint_filepath=args.checkpoint,
        results_filepath=args.output
    )

    # Reset/wipe checkpoint cache if requested
    if args.reset:
        processor.checkpoint_manager.clear()

    # Execute batch processor
    processor.run_batch(args.input)


if __name__ == "__main__":
    main()
