"""
Scholarship Finder Agent - Agent tìm kiếm học bổng
Nhiệm vụ: Tìm kiếm và phân tích các học bổng phù hợp với học sinh
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from ..utils.llm_client import llm_manager
from ..config.prompts import SCHOLARSHIP_FINDER_PROMPT, POPULAR_DESTINATIONS
from ..tools.web_search import web_search_tool

class ScholarshipFinderAgent:
    """Agent tìm kiếm học bổng chuyên nghiệp"""
    
    def __init__(self):
        self.name = "ScholarshipFinderAgent"
        self.llm = llm_manager
        self.search_tool = web_search_tool
        
    async def find_scholarships(
        self,
        student_info: Dict[str, Any],
        search_depth: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Tìm kiếm học bổng phù hợp
        
        Args:
            student_info: Thông tin học sinh từ coordinator
            search_depth: Mức độ tìm kiếm (quick/comprehensive/deep)
            
        Returns:
            Danh sách học bổng được đề xuất
        """
        logger.info(f"Starting scholarship search for: {student_info.get('field_of_study', 'Unknown')}")
        
        try:
            # Parse student information
            target_country = student_info.get("target_country", "")
            field_of_study = student_info.get("field_of_study", "")
            degree_level = student_info.get("degree_level", "")
            
            # Perform multiple searches
            search_results = await self._perform_comprehensive_search(
                target_country, field_of_study, degree_level
            )
            
            # Analyze and filter scholarships
            analyzed_scholarships = await self._analyze_scholarship_results(
                search_results, student_info
            )
            
            # Rank scholarships by suitability
            ranked_scholarships = await self._rank_scholarships(
                analyzed_scholarships, student_info
            )
            
            return {
                "success": True,
                "total_found": len(search_results),
                "filtered_count": len(analyzed_scholarships),
                "recommended_count": len(ranked_scholarships),
                "scholarships": ranked_scholarships,
                "search_summary": self._create_search_summary(search_results, ranked_scholarships)
            }
            
        except Exception as e:
            logger.error(f"Error in scholarship search: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "scholarships": []
            }
    
    async def _perform_comprehensive_search(
        self,
        country: str,
        field: str,
        degree: str
    ) -> List[Dict[str, Any]]:
        """Thực hiện tìm kiếm toàn diện"""
        
        all_results = []
        
        # Primary search queries
        search_queries = [
            f"{country} scholarship {field} {degree} Vietnam students",
            f"{field} scholarship {country} international students 2024",
            f"merit scholarship {country} {field} undergraduate graduate",
            f"{country} university funding {field} Vietnamese students",
            f"full scholarship {country} {field} {degree} 2024 2025"
        ]
        
        # Specific scholarship programs to search
        if country.lower() in ["usa", "united states", "america"]:
            search_queries.extend([
                "Fulbright scholarship Vietnam",
                "AAUW fellowship women",
                "Gates Cambridge scholarship",
                "Rhodes scholarship"
            ])
        elif country.lower() in ["uk", "united kingdom", "england"]:
            search_queries.extend([
                "Chevening scholarship Vietnam",
                "Commonwealth scholarship",
                "Gates Cambridge scholarship"
            ])
        elif country.lower() in ["canada"]:
            search_queries.extend([
                "Vanier scholarship",
                "Trudeau foundation scholarship",
                "IDRC scholarship"
            ])
        elif country.lower() in ["australia"]:
            search_queries.extend([
                "Australia Awards scholarship",
                "Endeavour scholarship",
                "University of Melbourne scholarship"
            ])
        
        # Execute searches
        for query in search_queries:
            try:
                results = await self.search_tool.search_scholarships(
                    query=query,
                    country=country,
                    field=field,
                    num_results=8
                )
                all_results.extend(results)
                
                # Add small delay to respect rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {str(e)}")
                continue
        
        # Remove duplicates based on title and link
        unique_results = []
        seen_titles = set()
        seen_links = set()
        
        for result in all_results:
            title = result.get("title", "").lower()
            link = result.get("link", "")
            
            if title not in seen_titles and link not in seen_links:
                unique_results.append(result)
                seen_titles.add(title)
                if link:
                    seen_links.add(link)
        
        logger.info(f"Found {len(unique_results)} unique scholarship results")
        return unique_results
    
    async def _analyze_scholarship_results(
        self,
        search_results: List[Dict[str, Any]],
        student_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Phân tích và trích xuất thông tin chi tiết từ kết quả tìm kiếm"""
        
        analyzed_scholarships = []
        
        # Process results in batches for efficiency
        batch_size = 5
        for i in range(0, len(search_results), batch_size):
            batch = search_results[i:i+batch_size]
            
            try:
                batch_analysis = await self._analyze_scholarship_batch(batch, student_info)
                analyzed_scholarships.extend(batch_analysis)
            except Exception as e:
                logger.warning(f"Error analyzing batch {i//batch_size + 1}: {str(e)}")
                continue
        
        return analyzed_scholarships
    
    async def _analyze_scholarship_batch(
        self,
        search_batch: List[Dict[str, Any]],
        student_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Phân tích một batch kết quả tìm kiếm"""
        
        # Prepare search results for LLM analysis
        search_summary = "\n\n".join([
            f"Title: {result.get('title', '')}\nLink: {result.get('link', '')}\nSnippet: {result.get('snippet', '')}"
            for result in search_batch
        ])
        
        system_prompt = f"""
        {SCHOLARSHIP_FINDER_PROMPT}
        
        {POPULAR_DESTINATIONS}
        
        Phân tích các kết quả tìm kiếm về học bổng và trích xuất thông tin có cấu trúc.
        Tập trung vào học bổng dành cho sinh viên Việt Nam hoặc sinh viên quốc tế.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Thông tin học sinh:
                - Quốc gia: {student_info.get('target_country', '')}
                - Ngành học: {student_info.get('field_of_study', '')}
                - Bậc học: {student_info.get('degree_level', '')}
                
                Kết quả tìm kiếm:
                {search_summary}
                
                Hãy phân tích và trích xuất thông tin học bổng có cấu trúc.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "scholarships": [
                    {
                        "name": "string",
                        "organization": "string",
                        "value": "string", 
                        "requirements": {
                            "gpa": "string",
                            "language": "string",
                            "other": "string"
                        },
                        "deadline": "string",
                        "link": "string",
                        "description": "string",
                        "eligibility": "string",
                        "application_process": "string",
                        "match_score": "number 0-100"
                    }
                ]
            }
        )
        
        return response.get("scholarships", [])
    
    async def _rank_scholarships(
        self,
        scholarships: List[Dict[str, Any]],
        student_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Xếp hạng học bổng theo độ phù hợp"""
        
        # Enhanced ranking based on multiple factors
        for scholarship in scholarships:
            score = scholarship.get("match_score", 50)
            
            # Boost score based on scholarship characteristics
            name = scholarship.get("name", "").lower()
            value = scholarship.get("value", "").lower()
            requirements = scholarship.get("requirements", {})
            
            # High-value scholarships
            if any(term in value for term in ["full", "100%", "toàn phần"]):
                score += 15
            elif any(term in value for term in ["partial", "50%", "một phần"]):
                score += 10
            
            # Prestigious scholarships
            prestigious_keywords = ["fulbright", "chevening", "gates", "rhodes", "commonwealth"]
            if any(keyword in name for keyword in prestigious_keywords):
                score += 20
            
            # Vietnamese-specific scholarships
            if any(term in name.lower() for term in ["vietnam", "vietnamese", "việt nam"]):
                score += 15
            
            # Field relevance
            field = student_info.get("field_of_study", "").lower()
            if field and field in name:
                score += 10
            
            # Reasonable requirements
            gpa_req = requirements.get("gpa", "").lower()
            if "3.0" in gpa_req or "good" in gpa_req:
                score += 5
            elif "3.5" in gpa_req or "excellent" in gpa_req:
                score -= 5
            
            # Update match score
            scholarship["final_match_score"] = min(score, 100)
        
        # Sort by final match score
        ranked_scholarships = sorted(
            scholarships,
            key=lambda x: x.get("final_match_score", 0),
            reverse=True
        )
        
        # Return top 10 scholarships
        return ranked_scholarships[:10]
    
    def _create_search_summary(
        self,
        search_results: List[Dict[str, Any]],
        final_scholarships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tạo tóm tắt quá trình tìm kiếm"""
        
        # Count scholarship types
        scholarship_types = {
            "full_scholarships": 0,
            "partial_scholarships": 0,
            "merit_based": 0,
            "need_based": 0,
            "field_specific": 0
        }
        
        for scholarship in final_scholarships:
            value = scholarship.get("value", "").lower()
            name = scholarship.get("name", "").lower()
            
            if "full" in value or "100%" in value:
                scholarship_types["full_scholarships"] += 1
            elif "partial" in value or "%" in value:
                scholarship_types["partial_scholarships"] += 1
            
            if "merit" in name or "academic" in name:
                scholarship_types["merit_based"] += 1
            elif "need" in name or "financial" in name:
                scholarship_types["need_based"] += 1
        
        # Calculate average match score
        avg_match_score = 0
        if final_scholarships:
            avg_match_score = sum(
                s.get("final_match_score", 0) for s in final_scholarships
            ) / len(final_scholarships)
        
        return {
            "total_searched": len(search_results),
            "final_recommendations": len(final_scholarships),
            "scholarship_types": scholarship_types,
            "average_match_score": round(avg_match_score, 1),
            "search_quality": "High" if avg_match_score >= 70 else "Medium" if avg_match_score >= 50 else "Low"
        }
    
    async def search_specific_scholarship(
        self,
        scholarship_name: str,
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """Tìm kiếm thông tin chi tiết về một học bổng cụ thể"""
        
        try:
            query = f"{scholarship_name} scholarship details requirements application {additional_context}"
            
            search_results = await self.search_tool.search_scholarships(
                query=query,
                num_results=5
            )
            
            if not search_results:
                return {
                    "success": False,
                    "error": "No detailed information found",
                    "scholarship_name": scholarship_name
                }
            
            # Analyze detailed information
            detailed_info = await self._extract_detailed_scholarship_info(
                scholarship_name, search_results
            )
            
            return {
                "success": True,
                "scholarship_name": scholarship_name,
                "detailed_info": detailed_info,
                "sources": [r.get("link", "") for r in search_results]
            }
            
        except Exception as e:
            logger.error(f"Error searching specific scholarship: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "scholarship_name": scholarship_name
            }
    
    async def _extract_detailed_scholarship_info(
        self,
        scholarship_name: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Trích xuất thông tin chi tiết về học bổng"""
        
        search_content = "\n\n".join([
            f"Source: {result.get('source', '')}\nContent: {result.get('snippet', '')}"
            for result in search_results
        ])
        
        system_prompt = """
        Trích xuất thông tin chi tiết về học bổng từ kết quả tìm kiếm.
        Tập trung vào: giá trị, yêu cầu, hạn nộp, quy trình đăng ký.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Học bổng: {scholarship_name}
                
                Thông tin tìm được:
                {search_content}
                
                Hãy trích xuất thông tin chi tiết và có cấu trúc.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "scholarship_value": "string",
                "coverage": "string",
                "eligibility_requirements": {
                    "academic": "string",
                    "language": "string", 
                    "nationality": "string",
                    "other": "string"
                },
                "application_requirements": ["list of requirements"],
                "deadline": "string",
                "application_process": "string",
                "selection_criteria": "string",
                "contact_information": "string"
            }
        )
        
        return response

# Global scholarship finder instance
scholarship_finder_agent = ScholarshipFinderAgent()