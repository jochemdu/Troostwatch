"""Simple preprocessing stubs used during tests and local scripts.

This module provides lightweight placeholder implementations for the
label-extraction pipeline used by some scripts. These are intentionally
minimal and should be replaced by actual implementations when the
pipeline is wired up.
"""


def preprocess_for_ocr(image_bytes, config=None):
    # Dummy: just return the input
    return image_bytes


class PreprocessingConfig:
    @staticmethod
    def for_labels():
        return PreprocessingConfig()

    steps_applied = ["dummy"]


class TesseractOCR:
    def __init__(self, language="eng"):
        pass

    def extract_text(self, image_bytes):
        class Result:
            text = ""
            confidence = 1.0

        return Result()


def parse_label(text):
    # Dummy: just return None
    return None


class ParsedLabel:
    pass
