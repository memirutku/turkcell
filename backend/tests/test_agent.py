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

    def test_all_five_tool_names(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        names = {t.name for t in tools}
        expected = {"activate_package", "change_tariff", "lookup_customer_bill", "get_available_packages", "get_available_tariffs"}
        assert names == expected

    @pytest.mark.asyncio
    async def test_lookup_bill_tool_returns_data(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        lookup_tool = next(t for t in tools if t.name == "lookup_customer_bill")
        result_str = await lookup_tool.ainvoke({"customer_id": "cust-001"})
        result = json.loads(result_str)
        assert "customer_name" in result
        assert "bills" in result

    @pytest.mark.asyncio
    async def test_get_packages_tool_returns_data(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        pkg_tool = next(t for t in tools if t.name == "get_available_packages")
        result_str = await pkg_tool.ainvoke({})
        result = json.loads(result_str)
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_tariffs_tool_returns_data(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        tariff_tool = next(t for t in tools if t.name == "get_available_tariffs")
        result_str = await tariff_tool.ainvoke({})
        result = json.loads(result_str)
        assert isinstance(result, list)
        assert len(result) > 0


class TestAgentWorkflow:
    """Placeholder for LangGraph agent workflow tests (Plan 02)."""

    pass


class TestAgentConfirmation:
    """Placeholder for agent confirmation interrupt/resume tests (Plan 02)."""

    pass
