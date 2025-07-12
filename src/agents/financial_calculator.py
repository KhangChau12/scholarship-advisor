"""
Financial Calculator Agent - Agent tính toán tài chính du học
Nhiệm vụ: Tính toán chi phí du học, ước tính tiết kiệm từ học bổng, phân tích tài chính
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from ..utils.llm_client import llm_manager
from ..config.prompts import FINANCIAL_CALCULATOR_PROMPT
from ..tools.currency_converter import currency_converter
from ..tools.web_search import web_search_tool

class FinancialCalculatorAgent:
    """Agent tính toán tài chính du học chuyên nghiệp"""
    
    def __init__(self):
        self.name = "FinancialCalculatorAgent"
        self.llm = llm_manager
        self.currency_tool = currency_converter
        self.search_tool = web_search_tool
        
    async def calculate_study_costs(
        self,
        student_info: Dict[str, Any],
        scholarships: List[Dict[str, Any]],
        target_currency: str = "VND"
    ) -> Dict[str, Any]:
        """
        Tính toán toàn diện chi phí du học
        
        Args:
            student_info: Thông tin học sinh (quốc gia, ngành học, etc.)
            scholarships: Danh sách học bổng được đề xuất
            target_currency: Tiền tệ hiển thị (mặc định VND)
            
        Returns:
            Phân tích tài chính chi tiết
        """
        logger.info("Starting comprehensive financial calculation")
        
        try:
            # Get study destination info
            country = student_info.get("target_country", "")
            field = student_info.get("field_of_study", "")
            degree_level = student_info.get("degree_level", "")
            
            # Research current costs
            cost_data = await self._research_study_costs(country, field, degree_level)
            
            # Calculate base costs
            base_costs = await self._calculate_base_costs(cost_data, country)
            
            # Analyze scholarship opportunities
            scholarship_analysis = await self._analyze_scholarship_savings(
                scholarships, base_costs
            )
            
            # Convert to target currency
            financial_summary = await self._convert_to_target_currency(
                base_costs, scholarship_analysis, target_currency
            )
            
            # Generate financial recommendations
            recommendations = await self._generate_financial_recommendations(
                financial_summary, student_info
            )
            
            return {
                "success": True,
                "base_costs": base_costs,
                "scholarship_analysis": scholarship_analysis,
                "financial_summary": financial_summary,
                "recommendations": recommendations,
                "calculation_metadata": {
                    "currency": target_currency,
                    "calculation_date": asyncio.get_event_loop().time(),
                    "data_sources": cost_data.get("sources", [])
                }
            }
            
        except Exception as e:
            logger.error(f"Error in financial calculation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "financial_summary": {}
            }
    
    async def _research_study_costs(
        self,
        country: str,
        field: str,
        degree_level: str
    ) -> Dict[str, Any]:
        """Nghiên cứu chi phí du học hiện tại"""
        
        # Search for tuition fees
        tuition_results = await self.search_tool.search_tuition_fees(
            university="top universities",
            country=country,
            program=f"{field} {degree_level}"
        )
        
        # Search for living costs
        living_cost_query = f"{country} cost of living international students 2024"
        living_results = await self.search_tool.search_scholarships(
            query=living_cost_query,
            country=country,
            num_results=5
        )
        
        # Analyze cost data with LLM
        cost_analysis = await self._analyze_cost_data(
            tuition_results, living_results, country, field, degree_level
        )
        
        return {
            "tuition_analysis": cost_analysis,
            "sources": [r.get("link", "") for r in tuition_results + living_results]
        }
    
    async def _analyze_cost_data(
        self,
        tuition_results: List[Dict[str, Any]],
        living_results: List[Dict[str, Any]],
        country: str,
        field: str,
        degree_level: str
    ) -> Dict[str, Any]:
        """Phân tích dữ liệu chi phí với LLM"""
        
        # Prepare search data for analysis
        search_content = "TUITION INFORMATION:\n"
        for result in tuition_results:
            search_content += f"- {result.get('title', '')}: {result.get('snippet', '')}\n"
        
        search_content += "\nLIVING COST INFORMATION:\n"
        for result in living_results:
            search_content += f"- {result.get('title', '')}: {result.get('snippet', '')}\n"
        
        system_prompt = f"""
        {FINANCIAL_CALCULATOR_PROMPT}
        
        Phân tích thông tin chi phí du học và đưa ra ước tính chi tiết.
        Tập trung vào chi phí cho sinh viên quốc tế từ Việt Nam.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Quốc gia: {country}
                Ngành học: {field}
                Bậc học: {degree_level}
                
                Thông tin chi phí tìm được:
                {search_content}
                
                Hãy phân tích và ước tính chi phí du học chi tiết.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "tuition_fees": {
                    "min_per_year": "number",
                    "max_per_year": "number",
                    "average_per_year": "number",
                    "currency": "string",
                    "program_duration": "number (years)"
                },
                "living_costs": {
                    "accommodation": {"min": "number", "max": "number", "currency": "string"},
                    "food": {"min": "number", "max": "number", "currency": "string"},
                    "transportation": {"min": "number", "max": "number", "currency": "string"},
                    "personal_expenses": {"min": "number", "max": "number", "currency": "string"},
                    "total_per_year": {"min": "number", "max": "number", "currency": "string"}
                },
                "other_costs": {
                    "visa_fees": {"amount": "number", "currency": "string"},
                    "health_insurance": {"amount": "number", "currency": "string"},
                    "flights": {"amount": "number", "currency": "string"},
                    "books_supplies": {"amount": "number", "currency": "string"}
                },
                "total_estimated_cost": {
                    "min_total": "number",
                    "max_total": "number",
                    "realistic_estimate": "number",
                    "currency": "string"
                }
            }
        )
        
        return response
    
    async def _calculate_base_costs(
        self,
        cost_data: Dict[str, Any],
        country: str
    ) -> Dict[str, Any]:
        """Tính toán chi phí cơ bản"""
        
        tuition_analysis = cost_data.get("tuition_analysis", {})
        
        # Extract cost components
        tuition = tuition_analysis.get("tuition_fees", {})
        living = tuition_analysis.get("living_costs", {})
        other = tuition_analysis.get("other_costs", {})
        
        # Calculate yearly costs
        yearly_costs = {
            "tuition": tuition.get("average_per_year", 0),
            "living": living.get("total_per_year", {}).get("max", 0),
            "other": sum([
                other.get("health_insurance", {}).get("amount", 0),
                other.get("books_supplies", {}).get("amount", 0)
            ]),
            "currency": tuition.get("currency", "USD")
        }
        
        # Calculate one-time costs
        one_time_costs = {
            "visa": other.get("visa_fees", {}).get("amount", 0),
            "flights": other.get("flights", {}).get("amount", 0),
            "currency": tuition.get("currency", "USD")
        }
        
        # Calculate total program cost
        duration = tuition.get("program_duration", 4)
        total_program_cost = (
            yearly_costs["tuition"] + yearly_costs["living"] + yearly_costs["other"]
        ) * duration + one_time_costs["visa"] + one_time_costs["flights"]
        
        return {
            "yearly_costs": yearly_costs,
            "one_time_costs": one_time_costs,
            "program_duration": duration,
            "total_program_cost": total_program_cost,
            "base_currency": yearly_costs["currency"],
            "cost_breakdown": {
                "tuition_percentage": round((yearly_costs["tuition"] * duration / total_program_cost) * 100, 1),
                "living_percentage": round((yearly_costs["living"] * duration / total_program_cost) * 100, 1),
                "other_percentage": round(((yearly_costs["other"] * duration + sum(one_time_costs.values())) / total_program_cost) * 100, 1)
            }
        }
    
    async def _analyze_scholarship_savings(
        self,
        scholarships: List[Dict[str, Any]],
        base_costs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phân tích tiết kiệm từ học bổng"""
        
        scholarship_scenarios = []
        total_program_cost = base_costs.get("total_program_cost", 0)
        yearly_tuition = base_costs.get("yearly_costs", {}).get("tuition", 0)
        duration = base_costs.get("program_duration", 4)
        
        for scholarship in scholarships[:5]:  # Top 5 scholarships
            # Parse scholarship value
            value_info = await self._parse_scholarship_value(
                scholarship, yearly_tuition, duration
            )
            
            # Calculate savings
            scenario = {
                "scholarship_name": scholarship.get("name", ""),
                "value_info": value_info,
                "total_savings": value_info.get("total_amount", 0),
                "net_cost": total_program_cost - value_info.get("total_amount", 0),
                "savings_percentage": round((value_info.get("total_amount", 0) / total_program_cost) * 100, 1) if total_program_cost > 0 else 0,
                "match_score": scholarship.get("final_match_score", 0)
            }
            
            scholarship_scenarios.append(scenario)
        
        # Find best scenario
        best_scenario = max(scholarship_scenarios, key=lambda x: x["total_savings"]) if scholarship_scenarios else None
        
        # Calculate combined scenarios
        combined_savings = await self._calculate_combined_scholarships(
            scholarship_scenarios, total_program_cost
        )
        
        return {
            "individual_scenarios": scholarship_scenarios,
            "best_single_scholarship": best_scenario,
            "combined_opportunities": combined_savings,
            "total_potential_savings": best_scenario.get("total_savings", 0) if best_scenario else 0
        }
    
    async def _parse_scholarship_value(
        self,
        scholarship: Dict[str, Any],
        yearly_tuition: float,
        duration: int
    ) -> Dict[str, Any]:
        """Phân tích giá trị học bổng"""
        
        value_text = scholarship.get("value", "").lower()
        
        # Default values
        value_info = {
            "type": "unknown",
            "annual_amount": 0,
            "total_amount": 0,
            "covers": []
        }
        
        try:
            # Full scholarship
            if any(keyword in value_text for keyword in ["full", "100%", "toàn phần"]):
                value_info.update({
                    "type": "full_tuition",
                    "annual_amount": yearly_tuition,
                    "total_amount": yearly_tuition * duration,
                    "covers": ["tuition"]
                })
            
            # Partial percentage
            elif "%" in value_text:
                import re
                percentage_match = re.search(r'(\d+)%', value_text)
                if percentage_match:
                    percentage = int(percentage_match.group(1)) / 100
                    value_info.update({
                        "type": "partial_percentage",
                        "annual_amount": yearly_tuition * percentage,
                        "total_amount": yearly_tuition * percentage * duration,
                        "covers": ["tuition"]
                    })
            
            # Fixed amount
            else:
                # Try to extract amount
                import re
                amount_patterns = [
                    r'\$(\d+,?\d*)',
                    r'(\d+,?\d*)\s*USD',
                    r'(\d+,?\d*)\s*dollars'
                ]
                
                for pattern in amount_patterns:
                    match = re.search(pattern, value_text)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        amount = float(amount_str)
                        
                        # Determine if per year or total
                        if any(keyword in value_text for keyword in ["per year", "annually", "yearly"]):
                            value_info.update({
                                "type": "fixed_annual",
                                "annual_amount": amount,
                                "total_amount": amount * duration,
                                "covers": ["tuition"]
                            })
                        else:
                            value_info.update({
                                "type": "fixed_total",
                                "annual_amount": amount / duration,
                                "total_amount": amount,
                                "covers": ["tuition"]
                            })
                        break
        
        except Exception as e:
            logger.warning(f"Error parsing scholarship value: {str(e)}")
        
        return value_info
    
    async def _calculate_combined_scholarships(
        self,
        scenarios: List[Dict[str, Any]],
        total_cost: float
    ) -> Dict[str, Any]:
        """Tính toán kết hợp nhiều học bổng"""
        
        # Sort by match score and savings
        sorted_scenarios = sorted(
            scenarios,
            key=lambda x: (x["match_score"], x["total_savings"]),
            reverse=True
        )
        
        # Simulate combinations (simplified)
        combinations = []
        
        if len(sorted_scenarios) >= 2:
            # Top 2 combination
            top_two_savings = min(
                sorted_scenarios[0]["total_savings"] + sorted_scenarios[1]["total_savings"],
                total_cost
            )
            
            combinations.append({
                "scholarships": [sorted_scenarios[0]["scholarship_name"], sorted_scenarios[1]["scholarship_name"]],
                "total_savings": top_two_savings,
                "net_cost": total_cost - top_two_savings,
                "success_probability": min(sorted_scenarios[0]["match_score"], sorted_scenarios[1]["match_score"]) * 0.7
            })
        
        if len(sorted_scenarios) >= 3:
            # Top 3 combination
            top_three_savings = min(
                sum(s["total_savings"] for s in sorted_scenarios[:3]),
                total_cost
            )
            
            combinations.append({
                "scholarships": [s["scholarship_name"] for s in sorted_scenarios[:3]],
                "total_savings": top_three_savings,
                "net_cost": total_cost - top_three_savings,
                "success_probability": min(s["match_score"] for s in sorted_scenarios[:3]) * 0.5
            })
        
        return combinations
    
    async def _convert_to_target_currency(
        self,
        base_costs: Dict[str, Any],
        scholarship_analysis: Dict[str, Any],
        target_currency: str
    ) -> Dict[str, Any]:
        """Chuyển đổi sang tiền tệ mục tiêu"""
        
        base_currency = base_costs.get("base_currency", "USD")
        
        if base_currency == target_currency:
            conversion_rate = 1.0
        else:
            conversion_rate = await self.currency_tool.get_exchange_rate(
                base_currency, target_currency
            )
            
        if conversion_rate is None:
            logger.warning(f"Could not get exchange rate from {base_currency} to {target_currency}")
            conversion_rate = 1.0
            target_currency = base_currency
        
        # Convert base costs
        converted_costs = {}
        for cost_type, amount in base_costs.get("yearly_costs", {}).items():
            if isinstance(amount, (int, float)):
                converted_costs[cost_type] = round(amount * conversion_rate, 0)
        
        total_program_cost_converted = round(
            base_costs.get("total_program_cost", 0) * conversion_rate, 0
        )
        
        # Convert scholarship savings
        best_scholarship = scholarship_analysis.get("best_single_scholarship")
        if best_scholarship:
            best_savings_converted = round(
                best_scholarship.get("total_savings", 0) * conversion_rate, 0
            )
            net_cost_converted = total_program_cost_converted - best_savings_converted
        else:
            best_savings_converted = 0
            net_cost_converted = total_program_cost_converted
        
        return {
            "currency": target_currency,
            "exchange_rate": conversion_rate,
            "base_currency": base_currency,
            "total_program_cost": total_program_cost_converted,
            "yearly_costs": converted_costs,
            "best_scholarship_savings": best_savings_converted,
            "net_cost_after_scholarships": net_cost_converted,
            "savings_percentage": round((best_savings_converted / total_program_cost_converted) * 100, 1) if total_program_cost_converted > 0 else 0,
            "cost_breakdown_vnd": {
                "tuition_per_year": converted_costs.get("tuition", 0),
                "living_per_year": converted_costs.get("living", 0),
                "other_per_year": converted_costs.get("other", 0)
            }
        }
    
    async def _generate_financial_recommendations(
        self,
        financial_summary: Dict[str, Any],
        student_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo gợi ý tài chính"""
        
        total_cost = financial_summary.get("total_program_cost", 0)
        net_cost = financial_summary.get("net_cost_after_scholarships", 0)
        currency = financial_summary.get("currency", "VND")
        
        system_prompt = """
        Đưa ra lời khuyên tài chính thực tế cho du học sinh Việt Nam.
        Tập trung vào khả năng tài chính của gia đình Việt Nam và các nguồn tài trợ.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Tổng chi phí: {total_cost:,.0f} {currency}
                Chi phí sau học bổng: {net_cost:,.0f} {currency}
                Thông tin học sinh: {json.dumps(student_info, ensure_ascii=False)}
                
                Hãy đưa ra gợi ý tài chính cụ thể và thực tế.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "affordability_assessment": "string (affordable/challenging/difficult)",
                "funding_strategies": [
                    {
                        "strategy": "string",
                        "description": "string",
                        "potential_amount": "number",
                        "timeline": "string",
                        "difficulty": "string (easy/medium/hard)"
                    }
                ],
                "savings_plan": {
                    "monthly_savings_needed": "number",
                    "savings_duration": "string",
                    "total_family_contribution": "number"
                },
                "alternative_options": [
                    {
                        "option": "string",
                        "description": "string",
                        "cost_reduction": "number"
                    }
                ],
                "financial_timeline": [
                    {
                        "phase": "string",
                        "timeframe": "string",
                        "actions": ["list of actions"],
                        "target_amount": "number"
                    }
                ]
            }
        )
        
        return response

# Global financial calculator instance
financial_calculator_agent = FinancialCalculatorAgent()