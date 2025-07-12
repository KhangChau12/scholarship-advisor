"""
Currency Converter Tool using ExchangeRate-API
"""
import asyncio
import aiohttp
from typing import Dict, Optional, List
from loguru import logger
import time
import json

from ..config.settings import settings

class CurrencyConverterTool:
    """Currency converter for scholarship financial calculations"""
    
    def __init__(self):
        self.api_key = settings.EXCHANGE_RATE_API_KEY
        self.base_url = f"https://v6.exchangerate-api.com/v6/{self.api_key}"
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour for exchange rates
        
    def _get_cache_key(self, from_currency: str, to_currency: str) -> str:
        """Generate cache key for currency pair"""
        return f"{from_currency}_{to_currency}"
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - timestamp < self.cache_ttl
    
    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """
        Get exchange rate between two currencies
        
        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'VND')
            
        Returns:
            Exchange rate or None if error
        """
        # Normalize currency codes
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Check cache
        cache_key = self._get_cache_key(from_currency, to_currency)
        if cache_key in self.cache:
            rate, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.info(f"Using cached exchange rate: {from_currency} → {to_currency}")
                return rate
        
        try:
            url = f"{self.base_url}/pair/{from_currency}/{to_currency}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("result") == "success":
                            rate = data.get("conversion_rate")
                            
                            # Cache the rate
                            self.cache[cache_key] = (rate, time.time())
                            
                            logger.info(f"Exchange rate {from_currency} → {to_currency}: {rate}")
                            return rate
                        else:
                            logger.error(f"Currency API error: {data.get('error-type', 'Unknown')}")
                            return None
                    else:
                        logger.error(f"Currency API HTTP error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting exchange rate: {str(e)}")
            return None
    
    async def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> Optional[Dict[str, any]]:
        """
        Convert amount from one currency to another
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Conversion result with details
        """
        rate = await self.get_exchange_rate(from_currency, to_currency)
        
        if rate is None:
            return None
        
        converted_amount = amount * rate
        
        return {
            "original_amount": amount,
            "original_currency": from_currency.upper(),
            "converted_amount": round(converted_amount, 2),
            "converted_currency": to_currency.upper(),
            "exchange_rate": rate,
            "timestamp": time.time()
        }
    
    async def get_multiple_rates(
        self,
        base_currency: str,
        target_currencies: List[str]
    ) -> Dict[str, float]:
        """
        Get exchange rates for multiple currencies
        
        Args:
            base_currency: Base currency code
            target_currencies: List of target currency codes
            
        Returns:
            Dictionary of currency codes to exchange rates
        """
        rates = {}
        
        try:
            url = f"{self.base_url}/latest/{base_currency.upper()}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("result") == "success":
                            conversion_rates = data.get("conversion_rates", {})
                            
                            for currency in target_currencies:
                                currency_upper = currency.upper()
                                if currency_upper in conversion_rates:
                                    rates[currency_upper] = conversion_rates[currency_upper]
                                    
                                    # Cache individual rates
                                    cache_key = self._get_cache_key(base_currency.upper(), currency_upper)
                                    self.cache[cache_key] = (conversion_rates[currency_upper], time.time())
                            
                            logger.info(f"Retrieved {len(rates)} exchange rates for {base_currency}")
                            return rates
                            
        except Exception as e:
            logger.error(f"Error getting multiple exchange rates: {str(e)}")
        
        return rates
    
    def get_common_currencies(self) -> Dict[str, str]:
        """Get list of common currencies for student expenses"""
        return {
            "USD": "US Dollar",
            "EUR": "Euro", 
            "GBP": "British Pound",
            "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar",
            "JPY": "Japanese Yen",
            "KRW": "Korean Won",
            "SGD": "Singapore Dollar",
            "VND": "Vietnamese Dong",
            "CNY": "Chinese Yuan"
        }
    
    async def calculate_study_costs(
        self,
        costs: Dict[str, Dict[str, float]],
        target_currency: str = "VND"
    ) -> Dict[str, any]:
        """
        Calculate total study costs in target currency
        
        Args:
            costs: Dictionary of cost categories with amounts and currencies
            target_currency: Currency to convert everything to
            
        Returns:
            Comprehensive cost breakdown
        """
        total_cost = 0
        converted_costs = {}
        conversion_details = {}
        
        for category, cost_info in costs.items():
            amount = cost_info.get("amount", 0)
            currency = cost_info.get("currency", "USD")
            
            conversion = await self.convert_amount(amount, currency, target_currency)
            
            if conversion:
                converted_costs[category] = conversion["converted_amount"]
                total_cost += conversion["converted_amount"]
                conversion_details[category] = conversion
            else:
                logger.warning(f"Could not convert {category} cost from {currency}")
                converted_costs[category] = 0
        
        return {
            "total_cost": round(total_cost, 2),
            "target_currency": target_currency.upper(),
            "cost_breakdown": converted_costs,
            "conversion_details": conversion_details,
            "calculated_at": time.time()
        }

# Global currency converter instance
currency_converter = CurrencyConverterTool()