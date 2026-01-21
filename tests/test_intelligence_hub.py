"""Unit tests"""
import pytest
from unittest.mock import Mock, patch
from intelligence_hub.models.state import InvestigationState
from intelligence_hub.config.settings import Config
from intelligence_hub.utils.helpers import normalize_company_name, validate_ticker_format

class TestInvestigationState:
    """InvestigationState tests"""

    def test_initialization(self):
        """Test initialization"""
        state = InvestigationState()
        assert state.user_input == ""
        assert state.canonical_name == ""
        assert state.ticker == ""
        assert state.progress == 0
        assert isinstance(state.logs, list)

class TestConfig:
    """Configuration tests"""

    def test_config_defaults(self):
        """Test default values"""
        config = Config()
        assert config.MARKET_DATA_TTL == 24
        assert config.LLM_MODEL == "gpt-4o"
        assert config.RENDER_JS is True
        assert config.COUNTRY_CODE == "ae"

class TestHelpers:
    """Helper function tests"""

    def test_normalize_company_name(self):
        """Test company name normalization"""
        assert normalize_company_name("  first abu dhabi bank  ") == "First Abu Dhabi Bank"
        assert normalize_company_name("EMIRATES NBD") == "Emirates Nbd"

    def test_validate_ticker_format(self):
        """Test ticker validation"""
        assert validate_ticker_format("FAB") is True
        assert validate_ticker_format("ADCB") is True
        assert validate_ticker_format("fab") is False
        assert validate_ticker_format("FAB123") is True
        assert validate_ticker_format("FAB!") is False
        assert validate_ticker_format("VERYVERYLONGTICKER") is False

class TestWorkflow:
    """Workflow tests"""

    @pytest.mark.asyncio
    async def test_workflow_creation(self):
        """Test workflow creation"""
        from intelligence_hub.agents.investigation_workflow import create_investigation_workflow

        workflow = create_investigation_workflow()
        assert workflow is not None

if __name__ == "__main__":
    pytest.main([__file__])