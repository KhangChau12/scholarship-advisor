"""
Profile Analyzer Agent - Agent phân tích hồ sơ học sinh
Nhiệm vụ: Phân tích hồ sơ học tập, đánh giá điểm mạnh/yếu, so sánh với yêu cầu học bổng
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from ..utils.llm_client import llm_manager
from ..config.prompts import PROFILE_ANALYZER_PROMPT, VIETNAMESE_STUDENT_CONTEXT
from ..tools.file_processor import file_processor

class ProfileAnalyzerAgent:
    """Agent phân tích hồ sơ học tập chuyên nghiệp"""
    
    def __init__(self):
        self.name = "ProfileAnalyzerAgent"
        self.llm = llm_manager
        
    async def analyze_student_profile(
        self,
        student_info: Dict[str, Any],
        file_analysis: Optional[Dict[str, Any]] = None,
        scholarship_requirements: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Phân tích toàn diện hồ sơ học sinh
        
        Args:
            student_info: Thông tin cơ bản của học sinh
            file_analysis: Kết quả phân tích file upload
            scholarship_requirements: Yêu cầu của các học bổng
            
        Returns:
            Phân tích hồ sơ chi tiết với điểm mạnh/yếu và gợi ý cải thiện
        """
        logger.info("Starting comprehensive profile analysis")
        
        try:
            # Combine all available information
            combined_profile = await self._combine_profile_data(
                student_info, file_analysis
            )
            
            # Analyze academic performance
            academic_analysis = await self._analyze_academic_performance(
                combined_profile
            )
            
            # Analyze extracurricular activities
            extracurricular_analysis = await self._analyze_extracurricular_activities(
                combined_profile
            )
            
            # Analyze competitiveness
            competitiveness_analysis = await self._analyze_competitiveness(
                combined_profile, scholarship_requirements
            )
            
            # Generate improvement recommendations
            improvement_recommendations = await self._generate_improvement_recommendations(
                academic_analysis, extracurricular_analysis, competitiveness_analysis
            )
            
            # Calculate overall profile score
            overall_score = self._calculate_overall_profile_score(
                academic_analysis, extracurricular_analysis
            )
            
            return {
                "success": True,
                "profile_data": combined_profile,
                "academic_analysis": academic_analysis,
                "extracurricular_analysis": extracurricular_analysis,
                "competitiveness": competitiveness_analysis,
                "improvement_recommendations": improvement_recommendations,
                "overall_score": overall_score,
                "profile_summary": self._create_profile_summary(
                    academic_analysis, extracurricular_analysis, overall_score
                )
            }
            
        except Exception as e:
            logger.error(f"Error in profile analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "profile_data": {}
            }
    
    async def _combine_profile_data(
        self,
        student_info: Dict[str, Any],
        file_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Kết hợp tất cả thông tin hồ sơ"""
        
        combined_profile = {
            "basic_info": student_info,
            "academic_record": {},
            "test_scores": {},
            "achievements": [],
            "activities": [],
            "skills": [],
            "languages": [],
            "work_experience": [],
            "profile_strength": "Unknown"
        }
        
        # Extract information from file analysis if available
        if file_analysis and file_analysis.get("successful_files", 0) > 0:
            for result in file_analysis.get("results", []):
                if result.get("success"):
                    profile_data = result.get("profile", {})
                    
                    # Merge academic data
                    if "gpa" in profile_data:
                        combined_profile["academic_record"]["gpa"] = profile_data["gpa"]
                    
                    # Merge test scores
                    combined_profile["test_scores"].update(
                        profile_data.get("test_scores", {})
                    )
                    
                    # Merge activities and achievements
                    combined_profile["achievements"].extend(
                        profile_data.get("achievements", [])
                    )
                    combined_profile["activities"].extend(
                        profile_data.get("activities", [])
                    )
                    combined_profile["skills"].extend(
                        profile_data.get("skills", [])
                    )
                    combined_profile["languages"].extend(
                        profile_data.get("languages", [])
                    )
                    
                    # Add profile score if available
                    if "score" in result:
                        combined_profile["profile_strength"] = result["score"].get("strength_level", "Unknown")
        
        return combined_profile
    
    async def _analyze_academic_performance(
        self,
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phân tích thành tích học tập"""
        
        academic_data = profile.get("academic_record", {})
        test_scores = profile.get("test_scores", {})
        
        system_prompt = f"""
        {PROFILE_ANALYZER_PROMPT}
        
        {VIETNAMESE_STUDENT_CONTEXT}
        
        Phân tích thành tích học tập của học sinh Việt Nam.
        Lưu ý về hệ thống giáo dục Việt Nam: thang điểm 10 hoặc 4.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Thông tin học tập:
                - GPA: {academic_data.get('gpa', 'Chưa có')}
                - Điểm thi: {json.dumps(test_scores, ensure_ascii=False)}
                - Thành tích: {json.dumps(profile.get('achievements', []), ensure_ascii=False)}
                
                Hãy phân tích thành tích học tập và đánh giá điểm mạnh/yếu.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "gpa_analysis": {
                    "score": "number or null",
                    "scale": "string (10-point or 4-point)",
                    "strength": "string (excellent/good/average/needs_improvement)",
                    "percentile": "string"
                },
                "test_score_analysis": {
                    "ielts": {"score": "number or null", "target": "number", "gap": "number"},
                    "toefl": {"score": "number or null", "target": "number", "gap": "number"},
                    "sat": {"score": "number or null", "target": "number", "gap": "number"},
                    "other_tests": "object"
                },
                "academic_strengths": ["list of strengths"],
                "academic_weaknesses": ["list of weaknesses"],
                "competitiveness_level": "string (high/medium/low)",
                "improvement_priority": "string (gpa/test_scores/achievements)"
            }
        )
        
        return response
    
    async def _analyze_extracurricular_activities(
        self,
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phân tích hoạt động ngoại khóa"""
        
        activities = profile.get("activities", [])
        skills = profile.get("skills", [])
        work_experience = profile.get("work_experience", [])
        
        system_prompt = """
        Phân tích hoạt động ngoại khóa và kỹ năng của học sinh.
        Đánh giá mức độ đa dạng, leadership, và impact.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Hoạt động ngoại khóa: {json.dumps(activities, ensure_ascii=False)}
                Kỹ năng: {json.dumps(skills, ensure_ascii=False)}
                Kinh nghiệm làm việc: {json.dumps(work_experience, ensure_ascii=False)}
                
                Hãy phân tích và đánh giá hoạt động ngoại khóa.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "activity_diversity": {
                    "score": "number 0-100",
                    "categories": ["list of activity categories"],
                    "strength": "string"
                },
                "leadership_experience": {
                    "score": "number 0-100",
                    "examples": ["list of leadership examples"],
                    "level": "string (high/medium/low/none)"
                },
                "community_impact": {
                    "score": "number 0-100",
                    "examples": ["list of impact examples"],
                    "significance": "string"
                },
                "skill_assessment": {
                    "technical_skills": ["list"],
                    "soft_skills": ["list"],
                    "language_skills": ["list"],
                    "marketability": "string"
                },
                "extracurricular_strengths": ["list of strengths"],
                "extracurricular_gaps": ["list of gaps"],
                "activity_recommendations": ["list of recommended activities"]
            }
        )
        
        return response
    
    async def _analyze_competitiveness(
        self,
        profile: Dict[str, Any],
        scholarship_requirements: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Phân tích tính cạnh tranh so với yêu cầu học bổng"""
        
        if not scholarship_requirements:
            return {
                "overall_competitiveness": "medium",
                "scholarship_matches": [],
                "improvement_needed": []
            }
        
        system_prompt = """
        So sánh hồ sơ học sinh với yêu cầu của các học bổng.
        Đánh giá khả năng cạnh tranh và xác suất thành công.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Hồ sơ học sinh: {json.dumps(profile, ensure_ascii=False)}
                
                Yêu cầu học bổng: {json.dumps(scholarship_requirements, ensure_ascii=False)}
                
                Hãy so sánh và đánh giá tính cạnh tranh.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "scholarship_matches": [
                    {
                        "scholarship_name": "string",
                        "match_percentage": "number 0-100",
                        "meets_requirements": "boolean",
                        "missing_requirements": ["list"],
                        "competitive_advantage": ["list"],
                        "success_probability": "string (high/medium/low)"
                    }
                ],
                "overall_competitiveness": "string (excellent/good/average/weak)",
                "strongest_areas": ["list"],
                "weakest_areas": ["list"],
                "immediate_improvements": ["list"],
                "long_term_goals": ["list"]
            }
        )
        
        return response
    
    async def _generate_improvement_recommendations(
        self,
        academic_analysis: Dict[str, Any],
        extracurricular_analysis: Dict[str, Any],
        competitiveness_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo gợi ý cải thiện cụ thể"""
        
        system_prompt = """
        Dựa trên phân tích hồ sơ, tạo ra các gợi ý cải thiện cụ thể và có thể thực hiện.
        Ưu tiên các hành động có impact cao và timeline thực tế.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Phân tích học tập: {json.dumps(academic_analysis, ensure_ascii=False)}
                Phân tích ngoại khóa: {json.dumps(extracurricular_analysis, ensure_ascii=False)}
                Phân tích cạnh tranh: {json.dumps(competitiveness_analysis, ensure_ascii=False)}
                
                Tạo kế hoạch cải thiện hồ sơ cụ thể cho học sinh Việt Nam.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "immediate_actions": [
                    {
                        "action": "string",
                        "timeline": "string (1-3 months)",
                        "impact": "string (high/medium/low)",
                        "difficulty": "string (easy/medium/hard)",
                        "cost": "string (free/low/medium/high)"
                    }
                ],
                "short_term_goals": [
                    {
                        "goal": "string",
                        "timeline": "string (3-6 months)",
                        "steps": ["list of steps"],
                        "success_metrics": "string"
                    }
                ],
                "long_term_objectives": [
                    {
                        "objective": "string",
                        "timeline": "string (6-12 months)",
                        "preparation_needed": ["list"],
                        "expected_outcome": "string"
                    }
                ],
                "priority_matrix": {
                    "high_priority": ["list of high priority items"],
                    "medium_priority": ["list of medium priority items"],
                    "low_priority": ["list of low priority items"]
                },
                "resource_recommendations": {
                    "books": ["list of recommended books"],
                    "courses": ["list of recommended courses"],
                    "activities": ["list of recommended activities"],
                    "certifications": ["list of recommended certifications"]
                }
            }
        )
        
        return response
    
    def _calculate_overall_profile_score(
        self,
        academic_analysis: Dict[str, Any],
        extracurricular_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tính điểm tổng thể của hồ sơ"""
        
        # Extract scores from analyses
        academic_score = 0
        if "gpa_analysis" in academic_analysis:
            gpa_strength = academic_analysis["gpa_analysis"].get("strength", "average")
            if gpa_strength == "excellent":
                academic_score += 30
            elif gpa_strength == "good":
                academic_score += 20
            elif gpa_strength == "average":
                academic_score += 10
        
        # Test scores contribution
        test_analysis = academic_analysis.get("test_score_analysis", {})
        if test_analysis.get("ielts", {}).get("score"):
            ielts_score = test_analysis["ielts"]["score"]
            if ielts_score >= 7.0:
                academic_score += 15
            elif ielts_score >= 6.5:
                academic_score += 10
            elif ielts_score >= 6.0:
                academic_score += 5
        
        # Extracurricular scores
        extracurricular_score = 0
        if "activity_diversity" in extracurricular_analysis:
            extracurricular_score += extracurricular_analysis["activity_diversity"].get("score", 0) * 0.2
        
        if "leadership_experience" in extracurricular_analysis:
            extracurricular_score += extracurricular_analysis["leadership_experience"].get("score", 0) * 0.15
        
        if "community_impact" in extracurricular_analysis:
            extracurricular_score += extracurricular_analysis["community_impact"].get("score", 0) * 0.15
        
        # Calculate total score
        total_score = academic_score + extracurricular_score
        
        # Determine overall rating
        if total_score >= 80:
            rating = "Outstanding"
        elif total_score >= 65:
            rating = "Strong"
        elif total_score >= 50:
            rating = "Competitive"
        elif total_score >= 35:
            rating = "Developing"
        else:
            rating = "Needs Significant Improvement"
        
        return {
            "total_score": round(total_score, 1),
            "max_score": 100,
            "academic_component": round(academic_score, 1),
            "extracurricular_component": round(extracurricular_score, 1),
            "overall_rating": rating,
            "percentile_estimate": self._estimate_percentile(total_score)
        }
    
    def _estimate_percentile(self, score: float) -> str:
        """Ước tính percentile dựa trên điểm số"""
        if score >= 85:
            return "Top 5%"
        elif score >= 75:
            return "Top 15%"
        elif score >= 65:
            return "Top 30%"
        elif score >= 55:
            return "Top 50%"
        elif score >= 45:
            return "Top 70%"
        else:
            return "Below 70%"
    
    def _create_profile_summary(
        self,
        academic_analysis: Dict[str, Any],
        extracurricular_analysis: Dict[str, Any],
        overall_score: Dict[str, Any]
    ) -> str:
        """Tạo tóm tắt hồ sơ ngắn gọn"""
        
        rating = overall_score.get("overall_rating", "Unknown")
        percentile = overall_score.get("percentile_estimate", "Unknown")
        
        academic_strength = academic_analysis.get("competitiveness_level", "medium")
        activities_level = extracurricular_analysis.get("leadership_experience", {}).get("level", "medium")
        
        summary = f"""
        Hồ sơ tổng thể: {rating} ({percentile})
        Thành tích học tập: {academic_strength.title()}
        Hoạt động ngoại khóa: {activities_level.title()}
        
        Điểm mạnh chính: {', '.join(academic_analysis.get('academic_strengths', [])[:3])}
        Khu vực cần cải thiện: {academic_analysis.get('improvement_priority', 'Chưa xác định')}
        """
        
        return summary.strip()

# Global profile analyzer instance
profile_analyzer_agent = ProfileAnalyzerAgent()