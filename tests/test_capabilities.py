"""
Tests for AgentHands capabilities
"""

import pytest
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from src.capabilities import CAPABILITIES, get_capability, get_price


class TestCapabilities:
    """Test capability definitions."""
    
    def test_all_capabilities_have_required_fields(self):
        """All capabilities must have required fields."""
        required_fields = ['id', 'name', 'description', 'input_schema', 'price_usdc', 'tier']
        
        for cap_id, cap in CAPABILITIES.items():
            assert cap.id == cap_id, f"Capability ID mismatch: {cap_id}"
            for field in required_fields:
                assert getattr(cap, field) is not None, f"Missing {field} in {cap_id}"
    
    def test_get_capability(self):
        """Test capability retrieval."""
        cap = get_capability("browser.screenshot")
        assert cap.id == "browser.screenshot"
        assert cap.price_usdc == 0.01
    
    def test_get_unknown_capability(self):
        """Unknown capability should raise error."""
        with pytest.raises(ValueError):
            get_capability("nonexistent.capability")
    
    def test_price_calculation(self):
        """Test price with priority multipliers."""
        base_price = get_price("browser.screenshot", "standard")
        priority_price = get_price("browser.screenshot", "priority")
        immediate_price = get_price("browser.screenshot", "immediate")
        
        assert base_price == 0.01
        assert priority_price == 0.015  # 1.5x
        assert immediate_price == 0.02  # 2x
    
    def test_browser_capabilities_exist(self):
        """Browser capabilities should be defined."""
        assert "browser.screenshot" in CAPABILITIES
        assert "browser.scrape" in CAPABILITIES
        assert "browser.interact" in CAPABILITIES
    
    def test_code_capability_exists(self):
        """Code execution capability should be defined."""
        cap = get_capability("code.execute")
        assert "python" in str(cap.input_schema)
        assert "node" in str(cap.input_schema)
        assert "bash" in str(cap.input_schema)
    
    def test_blockchain_capability_exists(self):
        """Blockchain capability should be defined."""
        cap = get_capability("blockchain.balance")
        assert "polygon" in str(cap.input_schema)
        assert cap.price_usdc == 0.01


class TestPricing:
    """Test pricing model."""
    
    def test_tier_pricing(self):
        """Higher tiers should generally cost more."""
        tier1_prices = [c.price_usdc for c in CAPABILITIES.values() if c.tier == 1]
        tier2_prices = [c.price_usdc for c in CAPABILITIES.values() if c.tier == 2]
        
        if tier1_prices and tier2_prices:
            assert min(tier2_prices) >= min(tier1_prices)
    
    def test_minimum_viable_prices(self):
        """All prices should be at least $0.01."""
        for cap in CAPABILITIES.values():
            assert cap.price_usdc >= 0.01, f"{cap.id} has price below minimum"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
