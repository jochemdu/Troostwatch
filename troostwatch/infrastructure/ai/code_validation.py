"""Code validation utilities for extracted product codes.

This module provides validation for various product code formats:
- EAN-13/EAN-8: European Article Number (GS1 standard)
- UPC-A/UPC-E: Universal Product Code (US standard)
- ISBN-10/ISBN-13: International Standard Book Number
- GTIN-14: Global Trade Item Number (for cases/pallets)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CodeType(str, Enum):
    """Enumeration of supported code types."""

    EAN_13 = "ean_13"
    EAN_8 = "ean_8"
    UPC_A = "upc_a"
    UPC_E = "upc_e"
    ISBN_10 = "isbn_10"
    ISBN_13 = "isbn_13"
    GTIN_14 = "gtin_14"
    SERIAL_NUMBER = "serial_number"
    MODEL_NUMBER = "model_number"
    PRODUCT_CODE = "product_code"
    MAC_ADDRESS = "mac"
    UUID = "uuid"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    code_type: CodeType
    normalized_code: str
    original_code: str
    error_message: str | None = None


# --- GS1 Check Digit Calculation ---


def calculate_gs1_check_digit(digits: str) -> int:
    """Calculate the GS1 check digit for EAN/UPC/GTIN codes.

    The GS1 check digit algorithm:
    1. From right to left (excluding check digit position), multiply
       alternating digits by 3 and 1.
    2. Sum all products.
    3. Check digit = (10 - (sum mod 10)) mod 10.

    This works for EAN-13, EAN-8, UPC-A, and GTIN-14.

    Args:
        digits: The numeric string WITHOUT the check digit.
                For EAN-13: 12 digits. For EAN-8: 7 digits.

    Returns:
        The check digit (0-9).

    Raises:
        ValueError: If input is not all digits.
    """
    if not digits.isdigit():
        raise ValueError(f"Input must be all digits: {digits}")

    # Process from right to left, alternating multipliers 3, 1, 3, 1...
    total = 0
    for i, char in enumerate(reversed(digits)):
        digit = int(char)
        if i % 2 == 0:
            total += digit * 3
        else:
            total += digit * 1

    check_digit = (10 - (total % 10)) % 10
    return check_digit


def validate_ean_13(code: str) -> ValidationResult:
    """Validate an EAN-13 barcode.

    EAN-13 format:
    - 13 digits total
    - First 2-3 digits: Country/GS1 prefix
    - Next 4-5 digits: Manufacturer code
    - Next 4-5 digits: Product code
    - Last digit: Check digit

    Args:
        code: The EAN-13 code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    # Normalize: remove spaces, dashes
    normalized = normalize_code(code)

    # Pad with leading zeros if needed (some OCR drops leading zeros)
    if normalized.isdigit() and len(normalized) < 13:
        normalized = normalized.zfill(13)

    if len(normalized) != 13:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.EAN_13,
            normalized_code=normalized,
            original_code=code,
            error_message=f"EAN-13 must be 13 digits, got {len(normalized)}",
        )

    if not normalized.isdigit():
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.EAN_13,
            normalized_code=normalized,
            original_code=code,
            error_message="EAN-13 must contain only digits",
        )

    # Calculate expected check digit
    payload = normalized[:12]
    expected_check = calculate_gs1_check_digit(payload)
    actual_check = int(normalized[12])

    if expected_check != actual_check:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.EAN_13,
            normalized_code=normalized,
            original_code=code,
            error_message=f"Invalid check digit: expected {expected_check}, got {actual_check}",
        )

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.EAN_13,
        normalized_code=normalized,
        original_code=code,
    )


def validate_ean_8(code: str) -> ValidationResult:
    """Validate an EAN-8 barcode.

    EAN-8 format:
    - 8 digits total
    - First 2-3 digits: Country/GS1 prefix
    - Next 4-5 digits: Product code
    - Last digit: Check digit

    Args:
        code: The EAN-8 code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    normalized = normalize_code(code)

    # Pad with leading zeros if needed
    if normalized.isdigit() and len(normalized) < 8:
        normalized = normalized.zfill(8)

    if len(normalized) != 8:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.EAN_8,
            normalized_code=normalized,
            original_code=code,
            error_message=f"EAN-8 must be 8 digits, got {len(normalized)}",
        )

    if not normalized.isdigit():
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.EAN_8,
            normalized_code=normalized,
            original_code=code,
            error_message="EAN-8 must contain only digits",
        )

    payload = normalized[:7]
    expected_check = calculate_gs1_check_digit(payload)
    actual_check = int(normalized[7])

    if expected_check != actual_check:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.EAN_8,
            normalized_code=normalized,
            original_code=code,
            error_message=f"Invalid check digit: expected {expected_check}, got {actual_check}",
        )

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.EAN_8,
        normalized_code=normalized,
        original_code=code,
    )


def validate_upc_a(code: str) -> ValidationResult:
    """Validate a UPC-A barcode.

    UPC-A format:
    - 12 digits total
    - First digit: Number system
    - Next 5 digits: Manufacturer code
    - Next 5 digits: Product code
    - Last digit: Check digit

    Args:
        code: The UPC-A code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    normalized = normalize_code(code)

    if normalized.isdigit() and len(normalized) < 12:
        normalized = normalized.zfill(12)

    if len(normalized) != 12:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.UPC_A,
            normalized_code=normalized,
            original_code=code,
            error_message=f"UPC-A must be 12 digits, got {len(normalized)}",
        )

    if not normalized.isdigit():
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.UPC_A,
            normalized_code=normalized,
            original_code=code,
            error_message="UPC-A must contain only digits",
        )

    payload = normalized[:11]
    expected_check = calculate_gs1_check_digit(payload)
    actual_check = int(normalized[11])

    if expected_check != actual_check:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.UPC_A,
            normalized_code=normalized,
            original_code=code,
            error_message=f"Invalid check digit: expected {expected_check}, got {actual_check}",
        )

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.UPC_A,
        normalized_code=normalized,
        original_code=code,
    )


def validate_gtin_14(code: str) -> ValidationResult:
    """Validate a GTIN-14 barcode.

    GTIN-14 format:
    - 14 digits total
    - First digit: Packaging indicator
    - Next 12 digits: GTIN-12 or padded GTIN-8/EAN-13
    - Last digit: Check digit

    Args:
        code: The GTIN-14 code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    normalized = normalize_code(code)

    if normalized.isdigit() and len(normalized) < 14:
        normalized = normalized.zfill(14)

    if len(normalized) != 14:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.GTIN_14,
            normalized_code=normalized,
            original_code=code,
            error_message=f"GTIN-14 must be 14 digits, got {len(normalized)}",
        )

    if not normalized.isdigit():
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.GTIN_14,
            normalized_code=normalized,
            original_code=code,
            error_message="GTIN-14 must contain only digits",
        )

    payload = normalized[:13]
    expected_check = calculate_gs1_check_digit(payload)
    actual_check = int(normalized[13])

    if expected_check != actual_check:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.GTIN_14,
            normalized_code=normalized,
            original_code=code,
            error_message=f"Invalid check digit: expected {expected_check}, got {actual_check}",
        )

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.GTIN_14,
        normalized_code=normalized,
        original_code=code,
    )


# --- ISBN Validation ---


def calculate_isbn_10_check_digit(digits: str) -> str:
    """Calculate ISBN-10 check digit.

    ISBN-10 uses modulo 11 with weights 10, 9, 8, 7, 6, 5, 4, 3, 2:
    - Sum = 10×d1 + 9×d2 + 8×d3 + ... + 2×d9
    - Check digit = (11 - (sum mod 11)) mod 11
    - If result is 10, use 'X'

    Args:
        digits: First 9 digits of ISBN-10.

    Returns:
        Check character ('0'-'9' or 'X').
    """
    if len(digits) != 9 or not digits.isdigit():
        raise ValueError(f"ISBN-10 payload must be 9 digits: {digits}")

    # Weights from 10 down to 2 for positions 0-8
    total = sum((10 - i) * int(d) for i, d in enumerate(digits))
    remainder = total % 11
    check = (11 - remainder) % 11

    return "X" if check == 10 else str(check)


def validate_isbn_10(code: str) -> ValidationResult:
    """Validate an ISBN-10 code.

    ISBN-10 format:
    - 10 characters (9 digits + 1 check character)
    - Check character can be 0-9 or X

    Args:
        code: The ISBN-10 code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    normalized = normalize_code(code).upper()

    if len(normalized) != 10:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.ISBN_10,
            normalized_code=normalized,
            original_code=code,
            error_message=f"ISBN-10 must be 10 characters, got {len(normalized)}",
        )

    # First 9 must be digits, last can be digit or X
    if not normalized[:9].isdigit():
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.ISBN_10,
            normalized_code=normalized,
            original_code=code,
            error_message="ISBN-10 first 9 characters must be digits",
        )

    if normalized[9] not in "0123456789X":
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.ISBN_10,
            normalized_code=normalized,
            original_code=code,
            error_message="ISBN-10 check character must be 0-9 or X",
        )

    expected_check = calculate_isbn_10_check_digit(normalized[:9])

    if expected_check != normalized[9]:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.ISBN_10,
            normalized_code=normalized,
            original_code=code,
            error_message=f"Invalid check digit: expected {expected_check}, got {normalized[9]}",
        )

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.ISBN_10,
        normalized_code=normalized,
        original_code=code,
    )


def validate_isbn_13(code: str) -> ValidationResult:
    """Validate an ISBN-13 code.

    ISBN-13 is essentially an EAN-13 starting with 978 or 979.

    Args:
        code: The ISBN-13 code to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    normalized = normalize_code(code)

    if len(normalized) != 13:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.ISBN_13,
            normalized_code=normalized,
            original_code=code,
            error_message=f"ISBN-13 must be 13 digits, got {len(normalized)}",
        )

    if not normalized.startswith(("978", "979")):
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.ISBN_13,
            normalized_code=normalized,
            original_code=code,
            error_message="ISBN-13 must start with 978 or 979",
        )

    # Use EAN-13 validation for the rest
    ean_result = validate_ean_13(normalized)

    return ValidationResult(
        is_valid=ean_result.is_valid,
        code_type=CodeType.ISBN_13,
        normalized_code=normalized,
        original_code=code,
        error_message=ean_result.error_message,
    )


# --- MAC Address Validation ---


def validate_mac_address(code: str) -> ValidationResult:
    """Validate a MAC address.

    Supports formats:
    - AA:BB:CC:DD:EE:FF
    - AA-BB-CC-DD-EE-FF
    - AABBCCDDEEFF
    - AA.BB.CC.DD.EE.FF

    Args:
        code: The MAC address to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    # Remove common separators
    normalized = code.upper().replace(":", "").replace("-", "").replace(".", "")

    if len(normalized) != 12:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.MAC_ADDRESS,
            normalized_code=normalized,
            original_code=code,
            error_message=f"MAC address must be 12 hex digits, got {len(normalized)}",
        )

    if not all(c in "0123456789ABCDEF" for c in normalized):
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.MAC_ADDRESS,
            normalized_code=normalized,
            original_code=code,
            error_message="MAC address must contain only hex digits",
        )

    # Format as AA:BB:CC:DD:EE:FF
    formatted = ":".join(normalized[i: i + 2] for i in range(0, 12, 2))

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.MAC_ADDRESS,
        normalized_code=formatted,
        original_code=code,
    )


# --- UUID Validation ---


def validate_uuid(code: str) -> ValidationResult:
    """Validate a UUID.

    Supports formats:
    - 550e8400-e29b-41d4-a716-446655440000
    - 550e8400e29b41d4a716446655440000

    Args:
        code: The UUID to validate.

    Returns:
        ValidationResult with validation status and details.
    """
    # Remove dashes and convert to lowercase
    normalized = code.lower().replace("-", "")

    if len(normalized) != 32:
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.UUID,
            normalized_code=normalized,
            original_code=code,
            error_message=f"UUID must be 32 hex digits, got {len(normalized)}",
        )

    if not all(c in "0123456789abcdef" for c in normalized):
        return ValidationResult(
            is_valid=False,
            code_type=CodeType.UUID,
            normalized_code=normalized,
            original_code=code,
            error_message="UUID must contain only hex digits",
        )

    # Format as standard UUID with dashes
    formatted = f"{normalized[:8]}-{normalized[8:12]}-{normalized[12:16]}-{normalized[16:20]}-{normalized[20:]}"

    return ValidationResult(
        is_valid=True,
        code_type=CodeType.UUID,
        normalized_code=formatted,
        original_code=code,
    )


# --- Code Normalization ---


def normalize_code(code: str) -> str:
    """Normalize a code string.

    - Strips leading/trailing whitespace
    - Removes common OCR artifacts
    - Collapses multiple spaces

    Args:
        code: The code string to normalize.

    Returns:
        Normalized code string.
    """
    # Strip whitespace
    result = code.strip()

    # Remove common separators (spaces, dashes in the middle)
    result = re.sub(r"[\s\-]+", "", result)

    # Remove common OCR artifacts (parentheses, brackets, etc.)
    result = re.sub(r"[\[\]\(\)\{\}]", "", result)

    return result


# --- Auto-detection and Validation ---


def detect_code_type(code: str) -> CodeType:
    """Attempt to detect the type of a product code.

    Args:
        code: The code string to analyze.

    Returns:
        Best guess at the code type.
    """
    normalized = normalize_code(code)

    # Check for purely numeric codes first (EAN, UPC, GTIN)
    if normalized.isdigit():
        length = len(normalized)
        if length == 13:
            if normalized.startswith(("978", "979")):
                return CodeType.ISBN_13
            return CodeType.EAN_13
        elif length == 12:
            return CodeType.UPC_A
        elif length == 8:
            return CodeType.EAN_8
        elif length == 14:
            return CodeType.GTIN_14

    # Check for MAC address pattern (requires separators OR hex letters A-F)
    # This avoids false positives on pure-digit codes
    mac_normalized = code.upper().replace(":", "").replace("-", "").replace(".", "")
    has_separators = ":" in code or "-" in code or "." in code
    has_hex_letters = any(c in "ABCDEF" for c in mac_normalized)
    if (
        len(mac_normalized) == 12
        and all(c in "0123456789ABCDEF" for c in mac_normalized)
        and (has_separators or has_hex_letters)
    ):
        return CodeType.MAC_ADDRESS

    # Check for UUID pattern
    uuid_normalized = code.lower().replace("-", "")
    if len(uuid_normalized) == 32 and all(
        c in "0123456789abcdef" for c in uuid_normalized
    ):
        return CodeType.UUID

    # ISBN-10 check (9 digits + optional X)
    if len(normalized) == 10:
        if normalized[:9].isdigit() and normalized[9] in "0123456789Xx":
            return CodeType.ISBN_10

    return CodeType.UNKNOWN


def validate_code(code: str, code_type: CodeType | None = None) -> ValidationResult:
    """Validate a product code.

    If code_type is not specified, attempts to auto-detect it.

    Args:
        code: The code to validate.
        code_type: Optional explicit code type.

    Returns:
        ValidationResult with validation details.
    """
    if code_type is None:
        code_type = detect_code_type(code)

    validators = {
        CodeType.EAN_13: validate_ean_13,
        CodeType.EAN_8: validate_ean_8,
        CodeType.UPC_A: validate_upc_a,
        CodeType.GTIN_14: validate_gtin_14,
        CodeType.ISBN_10: validate_isbn_10,
        CodeType.ISBN_13: validate_isbn_13,
        CodeType.MAC_ADDRESS: validate_mac_address,
        CodeType.UUID: validate_uuid,
    }

    validator = validators.get(code_type)
    if validator:
        return validator(code)

    # No specific validator - just normalize
    normalized = normalize_code(code)
    return ValidationResult(
        is_valid=True,  # Can't invalidate unknown types
        code_type=code_type,
        normalized_code=normalized,
        original_code=code,
    )


def validate_and_correct_ean(code: str) -> ValidationResult:
    """Validate an EAN code and attempt to correct common OCR errors.

    Tries EAN-13 first, then EAN-8. If validation fails, attempts
    common corrections:
    - Swap similar characters (0/O, 1/I/l, 5/S, 8/B)
    - Correct common transpositions

    Args:
        code: The EAN code to validate and possibly correct.

    Returns:
        ValidationResult with validation details.
    """
    # First try direct validation
    normalized = normalize_code(code)

    # Try as EAN-13
    if len(normalized) >= 12:
        result = validate_ean_13(normalized)
        if result.is_valid:
            return result

    # Try as EAN-8
    if len(normalized) <= 8:
        result = validate_ean_8(normalized)
        if result.is_valid:
            return result

    # Attempt OCR corrections
    corrections = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "b": "8",
        "G": "6",
        "g": "9",
    }

    corrected = normalized
    for wrong, right in corrections.items():
        corrected = corrected.replace(wrong, right)

    if corrected != normalized:
        # Try validation with corrected code
        if len(corrected) == 13:
            result = validate_ean_13(corrected)
            if result.is_valid:
                return result

        if len(corrected) == 8:
            result = validate_ean_8(corrected)
            if result.is_valid:
                return result

    # Return failed validation
    return ValidationResult(
        is_valid=False,
        code_type=CodeType.EAN_13 if len(normalized) >= 12 else CodeType.EAN_8,
        normalized_code=normalized,
        original_code=code,
        error_message="Could not validate or correct EAN code",
    )


__all__ = [
    "CodeType",
    "ValidationResult",
    "calculate_gs1_check_digit",
    "detect_code_type",
    "normalize_code",
    "validate_code",
    "validate_and_correct_ean",
    "validate_ean_13",
    "validate_ean_8",
    "validate_gtin_14",
    "validate_isbn_10",
    "validate_isbn_13",
    "validate_mac_address",
    "validate_upc_a",
    "validate_uuid",
]
