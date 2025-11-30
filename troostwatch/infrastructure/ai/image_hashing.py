"""Perceptual image hashing for deduplication.

This module provides image hashing utilities using multiple algorithms
to detect duplicate or near-duplicate images:

- **pHash (perceptual hash)**: Robust to resizing, compression, minor edits
- **dHash (difference hash)**: Fast, good for exact duplicates
- **aHash (average hash)**: Simple, fast baseline

Usage:
    from troostwatch.infrastructure.ai.image_hashing import (
        compute_phash,
        compute_dhash,
        hamming_distance,
        are_similar,
    )

    # Compute hash for an image
    hash1 = compute_phash("/path/to/image1.jpg")
    hash2 = compute_phash("/path/to/image2.jpg")

    # Compare hashes
    distance = hamming_distance(hash1, hash2)
    if are_similar(hash1, hash2, threshold=10):
        print("Images are similar!")
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from troostwatch.infrastructure.observability import get_logger

logger = get_logger(__name__)

# Try to import PIL, gracefully handle if not available
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # type: ignore[misc, assignment]


def _ensure_pil() -> None:
    """Raise ImportError if PIL is not available."""
    if not PIL_AVAILABLE:
        raise ImportError(
            "Pillow is required for image hashing. " "Install with: pip install Pillow"
        )


def compute_phash(
    image_path: str | Path,
    hash_size: int = 8,
) -> str:
    """Compute perceptual hash (pHash) for an image.

    pHash uses DCT (Discrete Cosine Transform) to create a hash that is
    robust to resizing, compression, and minor color changes.

    Args:
        image_path: Path to the image file.
        hash_size: Size of the hash (8 = 64-bit hash). Higher = more precise.

    Returns:
        Hex string representation of the hash.

    Raises:
        ImportError: If PIL is not available.
        FileNotFoundError: If image file doesn't exist.
        ValueError: If image cannot be processed.
    """
    _ensure_pil()

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    try:
        # Open and convert to grayscale
        with Image.open(path) as img:
            # Resize to hash_size * 4 for DCT (will reduce to hash_size after)
            img = img.convert("L").resize(
                (hash_size * 4, hash_size * 4),
                Image.Resampling.LANCZOS,
            )

            # Get pixel data
            pixels = list(img.getdata())

            # Simple DCT-like approach: compute block averages
            # Full DCT requires numpy/scipy, this is a simplified version
            block_size = 4
            blocks = []
            width = hash_size * 4

            for row in range(hash_size):
                for col in range(hash_size):
                    # Average pixels in this block
                    total = 0
                    for dy in range(block_size):
                        for dx in range(block_size):
                            idx = (row * block_size + dy) * width + (
                                col * block_size + dx
                            )
                            total += pixels[idx]
                    blocks.append(total / (block_size * block_size))

            # Compute median
            median = sorted(blocks)[len(blocks) // 2]

            # Build hash: 1 if above median, 0 if below
            bits = ["1" if b > median else "0" for b in blocks]
            hash_int = int("".join(bits), 2)

            return format(hash_int, f"0{hash_size * hash_size // 4}x")

    except Exception as e:
        logger.error(
            "Failed to compute pHash", extra={"path": str(path), "error": str(e)}
        )
        raise ValueError(f"Cannot compute pHash for {path}: {e}") from e


def compute_dhash(
    image_path: str | Path,
    hash_size: int = 8,
) -> str:
    """Compute difference hash (dHash) for an image.

    dHash compares adjacent pixels to create a hash. It's fast and works
    well for detecting exact or near-exact duplicates.

    Args:
        image_path: Path to the image file.
        hash_size: Width of the hash (height is hash_size, total bits = hash_size²).

    Returns:
        Hex string representation of the hash.
    """
    _ensure_pil()

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    try:
        with Image.open(path) as img:
            # Resize to (hash_size + 1) x hash_size for horizontal gradient
            img = img.convert("L").resize(
                (hash_size + 1, hash_size),
                Image.Resampling.LANCZOS,
            )

            pixels = list(img.getdata())
            width = hash_size + 1

            # Compare adjacent pixels
            bits = []
            for row in range(hash_size):
                for col in range(hash_size):
                    idx = row * width + col
                    bits.append("1" if pixels[idx] < pixels[idx + 1] else "0")

            hash_int = int("".join(bits), 2)
            return format(hash_int, f"0{hash_size * hash_size // 4}x")

    except Exception as e:
        logger.error(
            "Failed to compute dHash", extra={"path": str(path), "error": str(e)}
        )
        raise ValueError(f"Cannot compute dHash for {path}: {e}") from e


def compute_ahash(
    image_path: str | Path,
    hash_size: int = 8,
) -> str:
    """Compute average hash (aHash) for an image.

    aHash is the simplest perceptual hash: resize to small size,
    convert to grayscale, and compare each pixel to the mean.

    Args:
        image_path: Path to the image file.
        hash_size: Size of the hash grid.

    Returns:
        Hex string representation of the hash.
    """
    _ensure_pil()

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    try:
        with Image.open(path) as img:
            img = img.convert("L").resize(
                (hash_size, hash_size),
                Image.Resampling.LANCZOS,
            )

            pixels = list(img.getdata())
            mean = sum(pixels) / len(pixels)

            bits = ["1" if p > mean else "0" for p in pixels]
            hash_int = int("".join(bits), 2)
            return format(hash_int, f"0{hash_size * hash_size // 4}x")

    except Exception as e:
        logger.error(
            "Failed to compute aHash", extra={"path": str(path), "error": str(e)}
        )
        raise ValueError(f"Cannot compute aHash for {path}: {e}") from e


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hex hash strings.

    Hamming distance is the number of bits that differ between two hashes.
    Lower distance = more similar images.

    Args:
        hash1: First hash (hex string).
        hash2: Second hash (hex string).

    Returns:
        Number of differing bits.

    Raises:
        ValueError: If hashes have different lengths.
    """
    if len(hash1) != len(hash2):
        raise ValueError(f"Hash lengths must match: {len(hash1)} vs {len(hash2)}")

    # Convert hex to binary and count differences
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor = int1 ^ int2

    # Count set bits (1s) in XOR result
    return bin(xor).count("1")


def are_similar(
    hash1: str,
    hash2: str,
    threshold: int = 10,
) -> bool:
    """Check if two image hashes are similar.

    Args:
        hash1: First image hash.
        hash2: Second image hash.
        threshold: Maximum Hamming distance to consider similar.
            - 0: Identical
            - 1-5: Very similar (minor compression differences)
            - 6-10: Similar (same image, different processing)
            - 11-15: Somewhat similar (similar content)
            - 16+: Different images

    Returns:
        True if images are considered similar.
    """
    try:
        return hamming_distance(hash1, hash2) <= threshold
    except ValueError:
        return False


def compute_hash(
    image_path: str | Path,
    algorithm: Literal["phash", "dhash", "ahash"] = "phash",
    hash_size: int = 8,
) -> str:
    """Compute image hash using specified algorithm.

    Args:
        image_path: Path to image file.
        algorithm: Hash algorithm to use.
        hash_size: Size parameter for the hash.

    Returns:
        Hex hash string.
    """
    if algorithm == "phash":
        return compute_phash(image_path, hash_size)
    elif algorithm == "dhash":
        return compute_dhash(image_path, hash_size)
    elif algorithm == "ahash":
        return compute_ahash(image_path, hash_size)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


def find_duplicates(
    image_paths: list[str | Path],
    algorithm: Literal["phash", "dhash", "ahash"] = "phash",
    threshold: int = 10,
) -> list[tuple[str, str, int]]:
    """Find duplicate images in a list.

    Args:
        image_paths: List of image file paths.
        algorithm: Hash algorithm to use.
        threshold: Maximum Hamming distance to consider duplicates.

    Returns:
        List of tuples (path1, path2, distance) for similar images.
    """
    # Compute hashes for all images
    hashes: dict[str, str] = {}
    for path in image_paths:
        try:
            h = compute_hash(path, algorithm)
            hashes[str(path)] = h
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Skipping {path}: {e}")

    # Compare all pairs
    duplicates = []
    paths = list(hashes.keys())

    for i, path1 in enumerate(paths):
        for path2 in paths[i + 1 :]:
            try:
                dist = hamming_distance(hashes[path1], hashes[path2])
                if dist <= threshold:
                    duplicates.append((path1, path2, dist))
            except ValueError:
                pass

    return sorted(duplicates, key=lambda x: x[2])


__all__ = [
    "compute_phash",
    "compute_dhash",
    "compute_ahash",
    "compute_hash",
    "hamming_distance",
    "are_similar",
    "find_duplicates",
    "PIL_AVAILABLE",
]
