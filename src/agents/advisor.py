"""
Advisor Agent - Agent tư vấn tổng hợp
Nhiệm vụ: Tổng hợp thông tin từ tất cả agents, đưa ra tư vấn toàn diện và kế hoạch hành động
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime, timedelta

from ..utils.llm_client import llm_manager
from ..config.prompts import ADVISOR_PROMPT, VIETNAMESE_STUDENT_CONTEXT
from ..tools.email_sender import email_sender
from ..tools.web_search import web_search_tool

class AdvisorAgent:
    """Agent tư vấn tổng hợp - chuyên gia tư vấn du học"""
    
    def __init__(self):
        self.name = "AdvisorAgent"
        self.llm = llm_manager
        self.email_tool = email_sender
        self.search_tool = web_search_tool
        
    async def generate_comprehensive_advice(
        self,
        student_info: Dict[str, Any],
        scholarship_analysis: Dict[str, Any],
        profile_analysis: Dict[str, Any],
        financial_analysis: Dict[str, Any],
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo tư vấn tổng hợp từ tất cả thông tin
        
        Args:
            student_info: Thông tin cơ bản của học sinh
            scholarship_analysis: Kết quả phân tích học bổng
            profile_analysis: Kết quả phân tích hồ sơ
            financial_analysis: Kết quả phân tích tài chính
            user_email: Email để gửi tư vấn
            
        Returns:
            Tư vấn tổng hợp và kế hoạch hành động
        """
        logger.info("Generating comprehensive scholarship advice")
        
        try:
            # Generate executive summary
            executive_summary = await self._create_executive_summary(
                student_info, scholarship_analysis, profile_analysis, financial_analysis
            )
            
            # Prioritize scholarship recommendations
            prioritized_scholarships = await self._prioritize_scholarship_recommendations(
                scholarship_analysis, profile_analysis, financial_analysis
            )
            
            # Create detailed improvement plan
            improvement_plan = await self._create_improvement_plan(
                profile_analysis, prioritized_scholarships
            )
            
            # Generate application timeline
            application_timeline = await self._create_application_timeline(
                prioritized_scholarships, improvement_plan
            )
            
            # Research visa and administrative requirements
            visa_info = await self._research_visa_requirements(
                student_info.get("target_country", "")
            )
            
            # Calculate success probability
            success_analysis = await self._analyze_success_probability(
                profile_analysis, prioritized_scholarships, improvement_plan
            )
            
            # Create final recommendations
            final_recommendations = await self._create_final_recommendations(
                executive_summary, prioritized_scholarships, improvement_plan,
                application_timeline, visa_info, success_analysis
            )
            
            # Send email if requested
            email_sent = False
            if user_email:
                email_sent = await self._send_comprehensive_email(
                    user_email, student_info, final_recommendations
                )
            
            return {
                "success": True,
                "executive_summary": executive_summary,
                "prioritized_scholarships": prioritized_scholarships,
                "improvement_plan": improvement_plan,
                "application_timeline": application_timeline,
                "visa_requirements": visa_info,
                "success_analysis": success_analysis,
                "final_recommendations": final_recommendations,
                "email_sent": email_sent
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive advice: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "final_recommendations": {}
            }
    
    async def _create_executive_summary(
        self,
        student_info: Dict[str, Any],
        scholarship_analysis: Dict[str, Any],
        profile_analysis: Dict[str, Any],
        financial_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo tóm tắt tổng quan"""
        
        system_prompt = f"""
        {ADVISOR_PROMPT}
        
        Tạo tóm tắt tổng quan ngắn gọn và súc tích cho phiên tư vấn học bổng.
        Tập trung vào những điểm quan trọng nhất và kết luận chính.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Thông tin học sinh: {json.dumps(student_info, ensure_ascii=False)}
                
                Phân tích học bổng: Tìm được {scholarship_analysis.get('recommended_count', 0)} học bổng phù hợp
                
                Phân tích hồ sơ: Điểm tổng thể {profile_analysis.get('overall_score', {}).get('total_score', 0)}/100
                
                Phân tích tài chính: Chi phí ước tính {financial_analysis.get('financial_summary', {}).get('total_program_cost', 0):,.0f} {financial_analysis.get('financial_summary', {}).get('currency', 'VND')}
                
                Tạo tóm tắt tổng quan cho phiên tư vấn này.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "key_findings": [
                    {
                        "category": "string (academic/financial/opportunities/challenges)",
                        "finding": "string",
                        "impact": "string (high/medium/low)"
                    }
                ],
                "overall_assessment": "string",
                "top_opportunities": ["list of top 3 opportunities"],
                "main_challenges": ["list of main challenges"],
                "recommended_focus": "string",
                "success_outlook": "string (very_positive/positive/moderate/challenging)"
            }
        )
        
        return response
    
    async def _prioritize_scholarship_recommendations(
        self,
        scholarship_analysis: Dict[str, Any],
        profile_analysis: Dict[str, Any],
        financial_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Sắp xếp ưu tiên học bổng"""
        
        scholarships = scholarship_analysis.get("scholarships", [])
        profile_score = profile_analysis.get("overall_score", {}).get("total_score", 50)
        
        prioritized = []
        
        for scholarship in scholarships:
            # Calculate comprehensive priority score
            priority_score = 0
            
            # Match score from scholarship finder
            match_score = scholarship.get("final_match_score", 50)
            priority_score += match_score * 0.4
            
            # Financial value
            value_text = scholarship.get("value", "").lower()
            if "full" in value_text or "100%" in value_text:
                priority_score += 30
            elif "50%" in value_text or "partial" in value_text:
                priority_score += 20
            
            # Profile compatibility
            if profile_score >= 70:
                priority_score += 15
            elif profile_score >= 50:
                priority_score += 10
            
            # Deadline urgency
            deadline = scholarship.get("deadline", "").lower()
            if any(month in deadline for month in ["january", "february", "march"]):
                priority_score += 10  # Early deadlines get priority
            
            # Determine priority level
            if priority_score >= 80:
                priority = "high"
            elif priority_score >= 60:
                priority = "medium"
            else:
                priority = "low"
            
            prioritized.append({
                **scholarship,
                "priority": priority,
                "priority_score": round(priority_score, 1),
                "recommendation_reason": self._get_recommendation_reason(
                    scholarship, priority, profile_score
                )
            })
        
        # Sort by priority score
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return prioritized[:8]  # Top 8 scholarships
    
    def _get_recommendation_reason(
        self,
        scholarship: Dict[str, Any],
        priority: str,
        profile_score: float
    ) -> str:
        """Tạo lý do đề xuất học bổng"""
        
        reasons = []
        
        if priority == "high":
            reasons.append("Độ phù hợp cao với hồ sơ của bạn")
        
        value = scholarship.get("value", "").lower()
        if "full" in value:
            reasons.append("Học bổng toàn phần, tiết kiệm tối đa chi phí")
        elif "50%" in value:
            reasons.append("Giá trị học bổng cao")
        
        if profile_score >= 70:
            reasons.append("Hồ sơ của bạn có thể cạnh tranh tốt")
        
        name = scholarship.get("name", "").lower()
        if any(keyword in name for keyword in ["vietnam", "vietnamese"]):
            reasons.append("Dành riêng cho sinh viên Việt Nam")
        
        return "; ".join(reasons) if reasons else "Phù hợp với ngành học và quốc gia mục tiêu"
    
    async def _create_improvement_plan(
        self,
        profile_analysis: Dict[str, Any],
        prioritized_scholarships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tạo kế hoạch cải thiện hồ sơ"""
        
        improvement_recs = profile_analysis.get("improvement_recommendations", {})
        scholarship_requirements = [s.get("requirements", {}) for s in prioritized_scholarships[:3]]
        
        system_prompt = """
        Tạo kế hoạch cải thiện hồ sơ cụ thể và có thể thực hiện.
        Ưu tiên các hành động có impact cao và phù hợp với sinh viên Việt Nam.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Gợi ý cải thiện từ phân tích hồ sơ: {json.dumps(improvement_recs, ensure_ascii=False)}
                
                Yêu cầu học bổng hàng đầu: {json.dumps(scholarship_requirements, ensure_ascii=False)}
                
                Tạo kế hoạch cải thiện hồ sơ theo timeline cụ thể.
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
                        "timeline": "string",
                        "priority": "string (high/medium/low)",
                        "cost": "string",
                        "expected_impact": "string"
                    }
                ],
                "short_term_goals": [
                    {
                        "goal": "string",
                        "timeline": "string",
                        "steps": ["list of steps"],
                        "resources_needed": ["list"],
                        "success_metrics": "string"
                    }
                ],
                "long_term_objectives": [
                    {
                        "objective": "string",
                        "timeline": "string",
                        "preparation": ["list"],
                        "milestones": ["list"]
                    }
                ],
                "monthly_checklist": {
                    "month_1": ["list of tasks"],
                    "month_2": ["list of tasks"],
                    "month_3": ["list of tasks"],
                    "month_6": ["list of tasks"]
                }
            }
        )
        
        return response
    
    async def _create_application_timeline(
        self,
        prioritized_scholarships: List[Dict[str, Any]],
        improvement_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo timeline nộp đơn"""
        
        # Extract deadlines
        deadlines = []
        for scholarship in prioritized_scholarships[:5]:
            deadline_text = scholarship.get("deadline", "")
            if deadline_text and deadline_text.lower() != "rolling":
                deadlines.append({
                    "scholarship": scholarship.get("name", ""),
                    "deadline": deadline_text,
                    "priority": scholarship.get("priority", "medium")
                })
        
        # Create month-by-month timeline
        current_date = datetime.now()
        timeline = {}
        
        for i in range(12):
            month_date = current_date + timedelta(days=30*i)
            month_key = month_date.strftime("%Y-%m")
            month_name = month_date.strftime("%B %Y")
            
            timeline[month_key] = {
                "month_name": month_name,
                "scholarship_deadlines": [],
                "preparation_tasks": [],
                "milestones": []
            }
        
        # Populate timeline with scholarship deadlines
        for deadline_info in deadlines:
            # Simplified deadline parsing - in real implementation, use proper date parsing
            deadline_month = current_date + timedelta(days=60)  # Placeholder
            month_key = deadline_month.strftime("%Y-%m")
            
            if month_key in timeline:
                timeline[month_key]["scholarship_deadlines"].append(deadline_info)
        
        # Add preparation tasks from improvement plan
        immediate_actions = improvement_plan.get("immediate_actions", [])
        for action in immediate_actions:
            first_month = list(timeline.keys())[0]
            timeline[first_month]["preparation_tasks"].append(action["action"])
        
        return {
            "timeline": timeline,
            "critical_deadlines": deadlines,
            "preparation_overview": {
                "total_scholarships": len(prioritized_scholarships),
                "immediate_tasks": len(immediate_actions),
                "preparation_months": 6
            }
        }
    
    async def _research_visa_requirements(
        self,
        country: str
    ) -> Dict[str, Any]:
        """Nghiên cứu yêu cầu visa"""
        
        if not country:
            return {"visa_info": "Chưa xác định quốc gia"}
        
        try:
            visa_results = await self.search_tool.search_visa_requirements(
                country=country,
                nationality="Vietnam"
            )
            
            # Analyze visa information
            visa_content = "\n".join([
                f"{result.get('title', '')}: {result.get('snippet', '')}"
                for result in visa_results
            ])
            
            system_prompt = """
            Trích xuất thông tin visa du học cho sinh viên Việt Nam.
            Tập trung vào yêu cầu, thủ tục, và timeline.
            """
            
            messages = [
                {
                    "role": "user",
                    "content": f"""
                    Quốc gia: {country}
                    Thông tin visa tìm được: {visa_content}
                    
                    Trích xuất thông tin visa du học.
                    """
                }
            ]
            
            response = await self.llm.get_structured_response(
                messages=messages,
                system_prompt=system_prompt,
                schema={
                    "visa_type": "string",
                    "requirements": ["list of requirements"],
                    "documents_needed": ["list of documents"],
                    "processing_time": "string",
                    "fees": "string",
                    "important_notes": ["list of notes"]
                }
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"Could not research visa requirements: {str(e)}")
            return {
                "visa_info": f"Cần tìm hiểu thêm về visa du học {country}",
                "recommendation": "Liên hệ đại sứ quán để biết thông tin chính xác"
            }
    
    async def _analyze_success_probability(
        self,
        profile_analysis: Dict[str, Any],
        prioritized_scholarships: List[Dict[str, Any]],
        improvement_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phân tích xác suất thành công"""
        
        profile_score = profile_analysis.get("overall_score", {}).get("total_score", 50)
        high_priority_scholarships = [s for s in prioritized_scholarships if s.get("priority") == "high"]
        
        # Calculate base success probability
        if profile_score >= 80:
            base_probability = 0.8
        elif profile_score >= 65:
            base_probability = 0.6
        elif profile_score >= 50:
            base_probability = 0.4
        else:
            base_probability = 0.2
        
        # Adjust for scholarship fit
        if len(high_priority_scholarships) >= 3:
            scholarship_boost = 0.15
        elif len(high_priority_scholarships) >= 1:
            scholarship_boost = 0.1
        else:
            scholarship_boost = 0
        
        # Improvement plan impact
        immediate_actions = len(improvement_plan.get("immediate_actions", []))
        improvement_boost = min(immediate_actions * 0.05, 0.2)
        
        # Calculate final probability
        success_probability = min(base_probability + scholarship_boost + improvement_boost, 0.95)
        
        return {
            "overall_success_probability": round(success_probability, 2),
            "base_profile_strength": round(base_probability, 2),
            "scholarship_fit_bonus": round(scholarship_boost, 2),
            "improvement_potential": round(improvement_boost, 2),
            "confidence_level": "High" if success_probability >= 0.7 else "Medium" if success_probability >= 0.4 else "Moderate",
            "key_success_factors": [
                "Cải thiện điểm thi tiếng Anh",
                "Tăng cường hoạt động ngoại khóa",
                "Viết essay ấn tượng",
                "Nộp đơn sớm"
            ]
        }
    
    async def _create_final_recommendations(
        self,
        executive_summary: Dict[str, Any],
        prioritized_scholarships: List[Dict[str, Any]],
        improvement_plan: Dict[str, Any],
        application_timeline: Dict[str, Any],
        visa_info: Dict[str, Any],
        success_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo khuyến nghị cuối cùng"""
        
        return {
            "summary": executive_summary.get("overall_assessment", ""),
            "top_3_scholarships": prioritized_scholarships[:3],
            "immediate_action_plan": improvement_plan.get("immediate_actions", [])[:5],
            "next_6_months": improvement_plan.get("monthly_checklist", {}),
            "success_probability": success_analysis.get("overall_success_probability", 0),
            "key_deadlines": application_timeline.get("critical_deadlines", [])[:3],
            "visa_preparation": visa_info.get("requirements", [])[:3],
            "final_advice": [
                "Tập trung vào 3-5 học bổng có độ phù hợp cao nhất",
                "Bắt đầu chuẩn bị hồ sơ ngay từ bây giờ",
                "Cải thiện điểm số tiếng Anh là ưu tiên hàng đầu",
                "Tham gia thêm hoạt động tình nguyện và ngoại khóa",
                "Chuẩn bị essay cá nhân sớm và chỉnh sửa kỹ lưỡng"
            ]
        }
    
    async def _send_comprehensive_email(
        self,
        user_email: str,
        student_info: Dict[str, Any],
        recommendations: Dict[str, Any]
    ) -> bool:
        """Gửi email tư vấn toàn diện"""
        
        try:
            student_name = student_info.get("profile_summary", "").split()[0] if student_info.get("profile_summary") else "Bạn"
            
            return await self.email_tool.send_scholarship_recommendation(
                to_email=user_email,
                student_name=student_name,
                scholarships=recommendations.get("top_3_scholarships", []),
                financial_summary={
                    "total_cost": 0,  # Will be filled from financial analysis
                    "potential_savings": 0,
                    "target_currency": "VND"
                },
                recommendations=recommendations.get("final_advice", []),
                additional_info={
                    "visa_requirements": recommendations.get("visa_preparation", []),
                    "application_timeline": recommendations.get("key_deadlines", [])
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending comprehensive email: {str(e)}")
            return False

# Global advisor instance
advisor_agent = AdvisorAgent()