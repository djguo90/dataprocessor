#!/usr/bin/env python3
"""
Script to copy all mp4 files from first-level subdirectories in code/media/videos
to a new collected folder.
"""

import shutil
import sys
from pathlib import Path


def copy_mp4_files():
    # Define paths

    videos_dir = r"/mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_视频结果_part003_p1v5_p2v5_matched_469"

    # Convert string path to Path object if needed
    if isinstance(videos_dir, str):
        videos_dir = Path(videos_dir)

    # Create output directory path in parent directory
    output_dir = videos_dir.parent / "小数单模-立体几何_训练集_视频结果_part003_p1v5_p2v5_matched_469_collected"

    # Check if source directory exists
    if not videos_dir.exists():
        print(f"Error: Source directory does not exist: {videos_dir}")
        return

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Counter for statistics
    total_copied = 0
    total_skipped = 0
    file_counter = {}  # To handle duplicate names

    # Get all first-level subdirectories
    subdirs = [d for d in videos_dir.iterdir() if d.is_dir()]

    print(f"Found {len(subdirs)} subdirectories in {videos_dir}")
    print("-" * 60)

    # Process each subdirectory
    for subdir in subdirs:
        # Look for mp4 files in the subdirectory and its children (like 480p15)
        mp4_files = list(subdir.rglob("*.mp4"))

        if mp4_files:
            print(f"\nProcessing {subdir.name}:")

            for mp4_file in mp4_files:
                # Skip files in partial_movie_files directories
                if "partial_movie_files" in str(mp4_file):
                    print(f"  ⊘ Skipping (partial): {mp4_file.name}")
                    total_skipped += 1
                    continue

                try:
                    # Use the UUID directory name as the base filename
                    uuid_name = subdir.name

                    # Handle duplicate UUID names (if somehow there are duplicates)
                    if uuid_name in file_counter:
                        file_counter[uuid_name] += 1
                        new_name = f"{uuid_name}_{file_counter[uuid_name]}.mp4"
                    else:
                        file_counter[uuid_name] = 0
                        new_name = f"{uuid_name}.mp4"

                    # Define destination path
                    dest_path = output_dir / new_name

                    # Copy the file
                    shutil.copy2(mp4_file, dest_path)
                    print(f"  ✓ Copied: {mp4_file.name} -> {new_name}")
                    total_copied += 1

                except Exception as e:
                    print(f"  ✗ Error copying {mp4_file.name}: {e}")
                    total_skipped += 1

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Total files copied: {total_copied}")
    print(f"Total files skipped: {total_skipped}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        copy_mp4_files()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
