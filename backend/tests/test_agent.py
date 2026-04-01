import json
import time

import pytest

from app.services.mock_bss import MockBSSService


class TestMockBSSActions:
    @pytest.fixture
    def mock_bss(self):
        service = MockBSSService()
        service.load_data()
        return service

    @pytest.mark.asyncio
    async def test_activate_package_success(self, mock_bss):
        result = await mock_bss.activate_package("cust-001", "pkg-002")
        assert result["success"] is True
        assert result["transaction_id"].startswith("TXN-")
        assert len(result["transaction_id"]) == 10  # TXN-XXXXXX
        assert result["customer_id"] == "cust-001"
        assert result["package"]["id"] == "pkg-002"
        assert result["package"]["name"] == "Ek 10GB Internet Paketi"
        assert "basariyla" in result["message_tr"]

    @pytest.mark.asyncio
    async def test_activate_package_invalid_customer(self, mock_bss):
        result = await mock_bss.activate_package("nonexistent", "pkg-002")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_activate_package_invalid_package(self, mock_bss):
        result = await mock_bss.activate_package("cust-001", "nonexistent")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_change_tariff_success(self, mock_bss):
        result = await mock_bss.change_tariff("cust-001", "tariff-003")
        assert result["success"] is True
        assert result["transaction_id"].startswith("TXN-")
        assert result["old_tariff"] is not None
        assert result["new_tariff"]["id"] == "tariff-003"
        assert "degistirildi" in result["message_tr"]

    @pytest.mark.asyncio
    async def test_change_tariff_invalid_customer(self, mock_bss):
        result = await mock_bss.change_tariff("nonexistent", "tariff-003")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_change_tariff_invalid_tariff(self, mock_bss):
        result = await mock_bss.change_tariff("cust-001", "nonexistent")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_change_tariff_updates_customer(self, mock_bss):
        original = mock_bss.get_customer("cust-001")
        original_tariff_id = original.tariff_id
        await mock_bss.change_tariff("cust-001", "tariff-003")
        updated = mock_bss.get_customer("cust-001")
        assert updated.tariff_id == "tariff-003"
        assert updated.tariff_id != original_tariff_id

    @pytest.mark.asyncio
    async def test_realistic_response_delay(self, mock_bss):
        start = time.monotonic()
        await mock_bss.activate_package("cust-001", "pkg-002")
        elapsed = time.monotonic() - start
        assert 0.3 <= elapsed <= 2.0, f"Expected delay 0.3-2.0s, got {elapsed:.2f}s"


class TestToolDefinitions:
    """Verify LangChain tool definitions for Gemini function calling."""

    def test_tools_list_not_empty(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        assert len(tools) >= 5

    def test_tool_names(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        names = {t.name for t in tools}
        assert "activate_package" in names
        assert "change_tariff" in names
        assert "lookup_customer_bill" in names

    def test_tool_descriptions_in_turkish(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        turkish_keywords = ["musteri", "paket", "tarife", "fatura", "listele", "aktif", "degistir", "sorgula"]
        for tool in tools:
            has_turkish = any(kw in tool.description.lower() for kw in turkish_keywords)
            assert has_turkish, f"Tool {tool.name} description lacks Turkish keywords: {tool.description}"


class TestAgentWorkflow:
    """Placeholder for LangGraph agent workflow tests (Plan 02)."""

    pass


class TestAgentConfirmation:
    """Placeholder for agent confirmation interrupt/resume tests (Plan 02)."""

    pass
