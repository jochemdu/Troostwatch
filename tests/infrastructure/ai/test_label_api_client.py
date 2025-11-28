"""Tests for the Label OCR API client."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from troostwatch.infrastructure.ai.label_api_client import (
    ExtractedCode,
    HealthStatus,
    LabelAPIClient,
    ParseLabelResult,
)


class TestExtractedCode:
    """Tests for ExtractedCode dataclass."""

    def test_create_extracted_code(self):
        """Test creating an ExtractedCode."""
        code = ExtractedCode(
            code_type="ean",
            value="5901234123457",
            confidence="high",
            context="barcode on package",
        )
        assert code.code_type == "ean"
        assert code.value == "5901234123457"
        assert code.confidence == "high"
        assert code.context == "barcode on package"

    def test_extracted_code_defaults(self):
        """Test ExtractedCode with default context."""
        code = ExtractedCode(
            code_type="serial_number",
            value="ABC123456",
            confidence="medium",
        )
        assert code.context is None


class TestParseLabelResult:
    """Tests for ParseLabelResult dataclass."""

    def test_create_empty_result(self):
        """Test creating an empty ParseLabelResult."""
        result = ParseLabelResult()
        assert result.codes == []
        assert result.raw_text == ""
        assert result.processing_time_ms == 0
        assert result.error is None

    def test_create_result_with_codes(self):
        """Test creating a result with codes."""
        codes = [
            ExtractedCode("ean", "1234567890123", "high"),
            ExtractedCode("serial_number", "SN123456", "medium"),
        ]
        result = ParseLabelResult(
            codes=codes,
            raw_text="EAN: 1234567890123\nS/N: SN123456",
            processing_time_ms=150,
        )
        assert len(result.codes) == 2
        assert result.processing_time_ms == 150

    def test_create_result_with_error(self):
        """Test creating a result with an error."""
        result = ParseLabelResult(error="Service not available")
        assert result.error == "Service not available"


class TestHealthStatus:
    """Tests for HealthStatus dataclass."""

    def test_create_health_status(self):
        """Test creating a HealthStatus."""
        status = HealthStatus(
            status="ok",
            model_loaded=True,
            tesseract_available=True,
        )
        assert status.status == "ok"
        assert status.model_loaded is True
        assert status.tesseract_available is True


class TestLabelAPIClient:
    """Tests for LabelAPIClient."""

    def test_init_default_url(self):
        """Test client initialization with default URL."""
        client = LabelAPIClient()
        assert client.base_url == "http://localhost:8001"
        assert client.timeout == 30.0

    def test_init_custom_url(self):
        """Test client initialization with custom URL."""
        client = LabelAPIClient(
            base_url="http://ml-service:9000",
            timeout=60.0,
        )
        assert client.base_url == "http://ml-service:9000"
        assert client.timeout == 60.0

    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL."""
        client = LabelAPIClient(base_url="http://localhost:8001/")
        assert client.base_url == "http://localhost:8001"

    def test_context_manager(self):
        """Test using client as context manager."""
        async def _test():
            async with LabelAPIClient() as client:
                assert client._client is not None
            assert client._client is None

        asyncio.run(_test())

    def test_health_check_success(self):
        """Test successful health check."""
        async def _test():
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "ok",
                "model_loaded": True,
                "tesseract_available": True,
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)

            client = LabelAPIClient()
            client._client = mock_client

            status = await client.health_check()

            assert status.status == "ok"
            assert status.model_loaded is True
            mock_client.get.assert_called_once_with("http://localhost:8001/health")

        asyncio.run(_test())

    def test_is_available_true(self):
        """Test is_available returns True when service is healthy."""
        async def _test():
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "ok",
                "model_loaded": True,
                "tesseract_available": True,
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)

            client = LabelAPIClient()
            client._client = mock_client

            available = await client.is_available()
            assert available is True

        asyncio.run(_test())

    def test_is_available_false_on_error(self):
        """Test is_available returns False when service is not reachable."""
        import httpx

        async def _test():
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            client = LabelAPIClient()
            client._client = mock_client

            available = await client.is_available()
            assert available is False

        asyncio.run(_test())

    def test_parse_label_url_success(self):
        """Test successful URL-based label parsing."""
        async def _test():
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "codes": [
                    {
                        "code_type": "ean",
                        "value": "5901234123457",
                        "confidence": "high",
                        "context": "barcode",
                    }
                ],
                "raw_text": "Product EAN: 5901234123457",
                "processing_time_ms": 200,
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            client = LabelAPIClient()
            client._client = mock_client

            result = await client.parse_label_url("https://example.com/image.jpg")

            assert result.error is None
            assert len(result.codes) == 1
            assert result.codes[0].code_type == "ean"
            assert result.codes[0].value == "5901234123457"
            assert result.processing_time_ms == 200

        asyncio.run(_test())

    def test_parse_label_url_connection_error(self):
        """Test URL parsing when service is not reachable."""
        import httpx

        async def _test():
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            client = LabelAPIClient()
            client._client = mock_client

            result = await client.parse_label_url("https://example.com/image.jpg")

            assert result.error is not None
            assert "not reachable" in result.error

        asyncio.run(_test())

    def test_parse_label_file_not_found(self):
        """Test file parsing when file does not exist."""
        async def _test():
            client = LabelAPIClient()
            result = await client.parse_label_file("/nonexistent/image.jpg")

            assert result.error is not None
            assert "not found" in result.error.lower()

        asyncio.run(_test())

    def test_parse_response_normalizes_code_types(self):
        """Test that unknown code types are normalized to 'other'."""
        client = LabelAPIClient()
        result = client._parse_response({
            "codes": [
                {"code_type": "unknown_type", "value": "ABC123", "confidence": "high"},
                {"code_type": "ean", "value": "1234567890123", "confidence": "high"},
            ],
            "raw_text": "test",
            "processing_time_ms": 100,
        })

        assert result.codes[0].code_type == "other"
        assert result.codes[1].code_type == "ean"

    def test_parse_response_normalizes_confidence(self):
        """Test that unknown confidence levels are normalized to 'medium'."""
        client = LabelAPIClient()
        result = client._parse_response({
            "codes": [
                {"code_type": "ean", "value": "1234567890123", "confidence": "very_high"},
            ],
            "raw_text": "test",
            "processing_time_ms": 100,
        })

        assert result.codes[0].confidence == "medium"

    def test_parse_response_handles_empty_codes(self):
        """Test parsing response with no codes."""
        client = LabelAPIClient()
        result = client._parse_response({
            "codes": [],
            "raw_text": "No codes found",
            "processing_time_ms": 50,
        })

        assert result.codes == []
        assert result.raw_text == "No codes found"
