"""
Project cleanup script.

Removes unnecessary files and organizes the project for deployment.
"""

import os
import shutil
from pathlib import Path

# Files and directories to remove
REMOVE_PATTERNS = [
    # Old backtest outputs
    "backtest_output.txt",
    "backtest_result.txt",
    "probs_output.txt",
    "test_out.txt",
    "test_output.txt",
    "train_output.txt",

    # Python cache
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/.pytest_cache",

    # IDE files
    "**/.vscode",
    "**/.idea",

    # OS files
    "**/.DS_Store",
    "**/Thumbs.db",

    # Temporary files
    "**/*.tmp",
    "**/*.temp",
    "**/*.log.old",

    # Old models (keep only latest)
    # Will be handled separately
]

# Directories to create if missing
ENSURE_DIRS = [
    "models",
    "backtest_results",
    "logs",
    "data",
    "config",
]


def cleanup_project(dry_run: bool = False):
    """
    Clean up the project.

    Args:
        dry_run: If True, only print what would be removed
    """
    project_root = Path(__file__).parent.parent

    print("=" * 80)
    print("PROJECT CLEANUP")
    print("=" * 80)
    print(f"\nProject root: {project_root}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")

    removed_count = 0
    removed_size = 0

    # Remove files matching patterns
    print("Removing files matching patterns...")
    for pattern in REMOVE_PATTERNS:
        if pattern.startswith("**"):
            # Recursive pattern
            for file_path in project_root.glob(pattern):
                if file_path.exists():
                    if file_path.is_dir():
                        size = sum(f.stat().st_size for f in file_path.rglob('*') if f.is_file())
                    else:
                        size = file_path.stat().st_size

                    removed_size += size
                    removed_count += 1

                    print(f"  [-] {file_path.relative_to(project_root)} ({size/1024:.1f} KB)")

                    if not dry_run:
                        if file_path.is_dir():
                            shutil.rmtree(file_path)
                        else:
                            file_path.unlink()
        else:
            # Direct file
            file_path = project_root / pattern
            if file_path.exists():
                size = file_path.stat().st_size
                removed_size += size
                removed_count += 1

                print(f"  [-] {pattern} ({size/1024:.1f} KB)")

                if not dry_run:
                    file_path.unlink()

    # Clean old models (keep only latest 3)
    print("\nCleaning old model files...")
    models_dir = project_root / "models"
    if models_dir.exists():
        # Find all timestamped models
        model_files = sorted(
            [f for f in models_dir.glob("lightgbm_*_*.pkl") if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Keep latest 3, remove others
        for old_model in model_files[3:]:
            size = old_model.stat().st_size
            removed_size += size
            removed_count += 1

            print(f"  [-] {old_model.name} ({size/1024:.1f} KB)")

            if not dry_run:
                old_model.unlink()
                # Also remove metadata (multiple possible patterns)
                meta_patterns = [
                    str(old_model).replace('.pkl', '_meta.pkl'),
                    str(old_model) + '_meta.pkl',
                ]
                for meta_pattern in meta_patterns:
                    meta_path = Path(meta_pattern)
                    if meta_path.exists():
                        meta_path.unlink()

    # Ensure required directories exist
    print("\nEnsuring required directories exist...")
    for dirname in ENSURE_DIRS:
        dir_path = project_root / dirname
        if not dir_path.exists():
            print(f"  [+] Creating {dirname}/")
            if not dry_run:
                dir_path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  [OK] {dirname}/ exists")

    # Summary
    print(f"\n{'='*80}")
    print("CLEANUP SUMMARY")
    print(f"{'='*80}")
    print(f"Files/dirs removed: {removed_count}")
    print(f"Space freed: {removed_size/1024/1024:.2f} MB")

    if dry_run:
        print("\n⚠️  DRY RUN - No files were actually removed")
        print("Run without --dry-run to execute cleanup")
    else:
        print("\n✅ Cleanup complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean up project files")
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be removed')
    args = parser.parse_args()

    cleanup_project(dry_run=args.dry_run)
