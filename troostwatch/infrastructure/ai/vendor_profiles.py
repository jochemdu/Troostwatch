"""Vendor-specific code extraction profiles.

This module defines extraction rules for specific manufacturers. Each vendor
has unique label formats, code patterns, and normalization rules.

Supported vendors:
- HP (Hewlett-Packard): Product numbers, serial numbers, spare part numbers
- Lenovo: MTM (Machine Type Model), serial numbers, FRU part numbers
- Ubiquiti: MAC addresses, model codes, serial numbers
- Dell: Service tags, express service codes, part numbers
- Apple: Serial numbers, model identifiers
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Literal

from .image_analyzer import ExtractedCode


@dataclass
class VendorProfile:
    """Configuration for vendor-specific code extraction."""

    name: str
    aliases: list[str] = field(default_factory=list)
    patterns: list["CodePattern"] = field(default_factory=list)
    normalizers: list[Callable[[str], str]] = field(default_factory=list)
    validators: list[Callable[[str, str], bool]] = field(default_factory=list)


@dataclass
class CodePattern:
    """A pattern for extracting a specific type of code."""

    code_type: Literal[
        "product_code",
        "model_number",
        "ean",
        "serial_number",
        "part_number",
        "mac_address",
        "service_tag",
        "other",
    ]
    pattern: re.Pattern
    confidence: Literal["high", "medium", "low"] = "medium"
    context: str | None = None
    validator: Callable[[str], bool] | None = None


# =============================================================================
# HP (Hewlett-Packard) Profile
# =============================================================================

# HP Product Number: Letters followed by # and alphanumeric
# Examples: L3M56A#ABB, C9V75A#B19, J8H61A#629
HP_PRODUCT_NUMBER = CodePattern(
    code_type="product_code",
    pattern=re.compile(
        r"\b([A-Z][A-Z0-9]{4,5}[A#][A-Z0-9]{2,4})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="HP product number",
)

# HP Spare Part Number: 6-8 digits followed by -001 or similar
# Examples: 123456-001, L12345-001
HP_SPARE_PART = CodePattern(
    code_type="part_number",
    pattern=re.compile(
        r"\b([A-Z]?\d{5,8}-\d{3})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="HP spare part number",
)

# HP Serial Number: 10 characters alphanumeric
# Examples: CND1234ABC, 5CD1234ABC
HP_SERIAL = CodePattern(
    code_type="serial_number",
    pattern=re.compile(
        r"(?:s/?n|serial)[:\s]*([A-Z0-9]{10})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="HP serial number",
)

# HP CT Number (for consumables)
# Examples: CT12345678
HP_CT_NUMBER = CodePattern(
    code_type="product_code",
    pattern=re.compile(r"\b(CT\d{8})\b", re.IGNORECASE),
    confidence="high",
    context="HP CT number",
)

HP_PROFILE = VendorProfile(
    name="HP",
    aliases=["hewlett-packard", "hewlett packard", "hp inc"],
    patterns=[HP_PRODUCT_NUMBER, HP_SPARE_PART, HP_SERIAL, HP_CT_NUMBER],
    normalizers=[str.upper],
)


# =============================================================================
# Lenovo Profile
# =============================================================================

# Lenovo MTM (Machine Type Model): 10 characters
# Examples: 20HS001QMH, 20L50011MH
LENOVO_MTM = CodePattern(
    code_type="model_number",
    pattern=re.compile(
        r"(?:mtm|machine\s*type)[:\s]*([A-Z0-9]{10})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Lenovo MTM",
)

# Lenovo Product Number (alternative format)
# Examples: 20HQ0014MH
LENOVO_PRODUCT = CodePattern(
    code_type="product_code",
    pattern=re.compile(
        r"\b(20[A-Z0-9]{2}\d{4}[A-Z]{2})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Lenovo product number",
)

# Lenovo Serial Number: 8+ alphanumeric, often starts with R9, PF, etc.
LENOVO_SERIAL = CodePattern(
    code_type="serial_number",
    pattern=re.compile(
        r"(?:s/?n|serial)[:\s]*([A-Z]{2}[A-Z0-9]{6,10})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Lenovo serial number",
)

# Lenovo FRU (Field Replaceable Unit) Part Number
# Examples: 01AY094, 00HN841
LENOVO_FRU = CodePattern(
    code_type="part_number",
    pattern=re.compile(
        r"(?:fru|p/?n)[:\s]*(\d{2}[A-Z]{2}\d{3})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Lenovo FRU part number",
)

LENOVO_PROFILE = VendorProfile(
    name="Lenovo",
    aliases=["lenovo group", "thinkpad", "thinkcentre", "ideapad"],
    patterns=[LENOVO_MTM, LENOVO_PRODUCT, LENOVO_SERIAL, LENOVO_FRU],
    normalizers=[str.upper],
)


# =============================================================================
# Ubiquiti Profile
# =============================================================================

# Ubiquiti Model Codes
# Examples: UAP-AC-PRO, USW-24-POE, UDM-PRO
UBIQUITI_MODEL = CodePattern(
    code_type="model_number",
    pattern=re.compile(
        r"\b(U[A-Z]{2,3}(?:-[A-Z0-9]{1,5}){1,4})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Ubiquiti model code",
)

# Ubiquiti MAC Address (common on network devices)
# Examples: 78:8A:20:12:34:56
UBIQUITI_MAC = CodePattern(
    code_type="mac_address",
    pattern=re.compile(
        r"\b([0-9A-F]{2}(?::[0-9A-F]{2}){5})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="MAC address",
)

# Ubiquiti Serial Number
UBIQUITI_SERIAL = CodePattern(
    code_type="serial_number",
    pattern=re.compile(
        r"(?:s/?n|serial)[:\s]*([A-Z0-9]{12,16})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Ubiquiti serial number",
)

UBIQUITI_PROFILE = VendorProfile(
    name="Ubiquiti",
    aliases=["ubiquiti networks", "ubnt", "unifi"],
    patterns=[UBIQUITI_MODEL, UBIQUITI_MAC, UBIQUITI_SERIAL],
    normalizers=[str.upper],
)


# =============================================================================
# Dell Profile
# =============================================================================

# Dell Service Tag: 7 alphanumeric characters
# Examples: ABC1234, 1AB2CD3
DELL_SERVICE_TAG = CodePattern(
    code_type="service_tag",
    pattern=re.compile(
        r"(?:service\s*tag|s/?t)[:\s]*([A-Z0-9]{7})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Dell Service Tag",
)

# Dell Express Service Code: 11 digits
DELL_EXPRESS_CODE = CodePattern(
    code_type="service_tag",
    pattern=re.compile(
        r"(?:express\s*(?:service\s*)?code)[:\s]*(\d{11})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Dell Express Service Code",
)

# Dell Part Number
# Examples: 0X123Y, 00X12Y
DELL_PART = CodePattern(
    code_type="part_number",
    pattern=re.compile(
        r"(?:p/?n|part)[:\s]*(0[A-Z0-9]{5,7})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Dell part number",
)

DELL_PROFILE = VendorProfile(
    name="Dell",
    aliases=["dell inc", "dell technologies", "dell emc"],
    patterns=[DELL_SERVICE_TAG, DELL_EXPRESS_CODE, DELL_PART],
    normalizers=[str.upper],
)


# =============================================================================
# Apple Profile
# =============================================================================

# Apple Serial Number: 12 characters
# Examples: C02X12345ABC
APPLE_SERIAL = CodePattern(
    code_type="serial_number",
    pattern=re.compile(
        r"(?:serial|s/?n)[:\s]*([A-Z0-9]{12})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Apple serial number",
)

# Apple Model Identifier
# Examples: A1466, A2337
APPLE_MODEL = CodePattern(
    code_type="model_number",
    pattern=re.compile(
        r"(?:model)[:\s]*(A\d{4})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Apple model identifier",
)

# Apple Part Number
# Examples: MGND3LL/A, MK2E3N/A
APPLE_PART = CodePattern(
    code_type="part_number",
    pattern=re.compile(
        r"(?:part|p/?n)?[:\s]*([A-Z]{2,4}\d{1,3}[A-Z]{1,2}/[A-Z])\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Apple part number",
)

APPLE_PROFILE = VendorProfile(
    name="Apple",
    aliases=["apple inc", "apple computer"],
    patterns=[APPLE_SERIAL, APPLE_MODEL, APPLE_PART],
    normalizers=[str.upper],
)


# =============================================================================
# Samsung Profile
# =============================================================================

# Samsung Model Number
# Examples: SM-G991B, SM-A525F, GT-I9500
SAMSUNG_MODEL = CodePattern(
    code_type="model_number",
    pattern=re.compile(
        r"\b((?:SM|GT)-[A-Z]\d{3,4}[A-Z]?)\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Samsung model number",
)

# Samsung Serial/IMEI pattern
SAMSUNG_SERIAL = CodePattern(
    code_type="serial_number",
    pattern=re.compile(
        r"(?:s/?n|serial|imei)[:\s]*([A-Z0-9]{11,15})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Samsung serial/IMEI",
)

SAMSUNG_PROFILE = VendorProfile(
    name="Samsung",
    aliases=["samsung electronics"],
    patterns=[SAMSUNG_MODEL, SAMSUNG_SERIAL],
    normalizers=[str.upper],
)


# =============================================================================
# Cisco Profile
# =============================================================================

# Cisco Product ID (PID)
# Examples: C9200L-24P-4G, WS-C2960X-24PS-L
CISCO_PID = CodePattern(
    code_type="product_code",
    pattern=re.compile(
        r"\b((?:C\d{4}|WS-C\d{4})[A-Z0-9-]{4,20})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Cisco Product ID",
)

# Cisco Serial Number: 11 alphanumeric, often starts with FCH, FDO, etc.
CISCO_SERIAL = CodePattern(
    code_type="serial_number",
    pattern=re.compile(
        r"(?:s/?n|serial)[:\s]*([A-Z]{3}[A-Z0-9]{8})\b",
        re.IGNORECASE,
    ),
    confidence="high",
    context="Cisco serial number",
)

CISCO_PROFILE = VendorProfile(
    name="Cisco",
    aliases=["cisco systems", "cisco meraki", "meraki"],
    patterns=[CISCO_PID, CISCO_SERIAL],
    normalizers=[str.upper],
)


# =============================================================================
# Profile Registry
# =============================================================================

VENDOR_PROFILES: dict[str, VendorProfile] = {
    "hp": HP_PROFILE,
    "lenovo": LENOVO_PROFILE,
    "ubiquiti": UBIQUITI_PROFILE,
    "dell": DELL_PROFILE,
    "apple": APPLE_PROFILE,
    "samsung": SAMSUNG_PROFILE,
    "cisco": CISCO_PROFILE,
}


def detect_vendor(text: str) -> VendorProfile | None:
    """Detect the vendor from text content.

    Searches for vendor names and aliases in the text to identify
    the manufacturer.

    Args:
        text: Text content (e.g., from OCR) to search for vendor names.

    Returns:
        The matching VendorProfile or None if no vendor detected.
    """
    text_lower = text.lower()

    for profile in VENDOR_PROFILES.values():
        # Check main name
        if profile.name.lower() in text_lower:
            return profile
        # Check aliases
        for alias in profile.aliases:
            if alias.lower() in text_lower:
                return profile

    return None


def extract_vendor_codes(
    text: str,
    vendor: VendorProfile | None = None,
) -> list[ExtractedCode]:
    """Extract codes using vendor-specific patterns.

    If no vendor is provided, attempts to auto-detect from the text.

    Args:
        text: Text content to extract codes from.
        vendor: Optional vendor profile to use. Auto-detected if None.

    Returns:
        List of extracted codes with vendor-specific confidence.
    """
    if vendor is None:
        vendor = detect_vendor(text)

    if vendor is None:
        return []

    codes: list[ExtractedCode] = []
    seen: set[str] = set()

    for code_pattern in vendor.patterns:
        for match in code_pattern.pattern.finditer(text):
            value = match.group(1)

            # Apply normalizers
            for normalizer in vendor.normalizers:
                value = normalizer(value)

            # Skip duplicates
            if value in seen:
                continue

            # Validate if validator exists
            if code_pattern.validator and not code_pattern.validator(value):
                continue

            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type=code_pattern.code_type,
                    value=value,
                    confidence=code_pattern.confidence,
                    context=f"{vendor.name}: {code_pattern.context}",
                )
            )

    return codes


def get_all_vendor_names() -> list[str]:
    """Return a list of all supported vendor names."""
    return [profile.name for profile in VENDOR_PROFILES.values()]
