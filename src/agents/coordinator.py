"""
Coordinator Agent - Agent điều phối trung tâm
Nhiệm vụ: Nhận yêu cầu, phân tích thông tin, điều phối các agent khác
"""
import os
import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from ..utils.llm_client import llm_manager
from ..config.prompts import COORDINATOR_PROMPT, VIETNAMESE_STUDENT_CONTEXT
from ..tools.file_processor import file_processor

class CoordinatorAgent:
    """Agent điều phối trung tâm"""
    
    def __init__(self):
        self.name = "CoordinatorAgent"
        self.llm = llm_manager
        
    async def process_initial_request(
        self,
        user_message: str,
        uploaded_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Xử lý yêu cầu ban đầu từ học sinh
        
        Args:
            user_message: Tin nhắn từ học sinh
            uploaded_files: Danh sách file upload (nếu có)
            
        Returns:
            Thông tin đã phân tích và kế hoạch xử lý
        """
        logger.info(f"Coordinator processing request: {user_message[:100]}...")
        
        try:
            # Phân tích yêu cầu ban đầu
            analysis_result = await self._analyze_user_request(user_message)
            
            # Xử lý file upload nếu có
            file_analysis = {}
            if uploaded_files:
                file_analysis = await self._process_uploaded_files(uploaded_files)
            
            # Tạo kế hoạch xử lý
            processing_plan = self._create_processing_plan(analysis_result, file_analysis)
            
            return {
                "success": True,
                "user_request": user_message,
                "analysis": analysis_result,
                "file_analysis": file_analysis,
                "processing_plan": processing_plan,
                "next_agents": self._determine_next_agents(analysis_result)
            }
            
        except Exception as e:
            logger.error(f"Error in coordinator: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_request": user_message
            }
    
    async def _analyze_user_request(self, user_message: str) -> Dict[str, Any]:
        """Phân tích yêu cầu của người dùng"""
        
        system_prompt = f"""
        {COORDINATOR_PROMPT}
        
        {VIETNAMESE_STUDENT_CONTEXT}
        
        Hãy phân tích yêu cầu của học sinh và trích xuất thông tin quan trọng.
        """
        
        messages = [
            {
                "role": "user", 
                "content": f"Yêu cầu của học sinh: {user_message}"
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "target_country": "string",
                "field_of_study": "string", 
                "degree_level": "string",
                "budget_range": "string",
                "profile_summary": "string",
                "completeness_score": "number 0-100",
                "missing_info": ["list of missing information"],
                "clarification_questions": ["list of questions to ask user"]
            }
        )
        
        return response
    
    async def _process_uploaded_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Xử lý các file được upload"""
        
        file_results = []
        
        for file_path in file_paths:
            try:
                # Validate file
                file_size = os.path.getsize(file_path)
                validation = file_processor.validate_file(file_path, file_size)
                
                if not validation["valid"]:
                    file_results.append({
                        "file": file_path,
                        "success": False,
                        "errors": validation["errors"]
                    })
                    continue
                
                # Process file
                processing_result = await file_processor.process_student_profile(file_path)
                
                if processing_result["success"]:
                    # Calculate profile score
                    profile_score = file_processor.calculate_profile_score(
                        processing_result["profile"]
                    )
                    
                    file_results.append({
                        "file": file_path,
                        "success": True,
                        "profile": processing_result["profile"],
                        "score": profile_score,
                        "content_preview": processing_result["raw_content"]
                    })
                else:
                    file_results.append({
                        "file": file_path,
                        "success": False,
                        "error": processing_result["error"]
                    })
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                file_results.append({
                    "file": file_path,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "total_files": len(file_paths),
            "successful_files": len([r for r in file_results if r["success"]]),
            "results": file_results
        }
    
    def _create_processing_plan(
        self,
        analysis_result: Dict[str, Any],
        file_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo kế hoạch xử lý cho các agent tiếp theo"""
        
        plan = {
            "workflow_steps": [],
            "estimated_time": 0,
            "complexity": "medium"
        }
        
        # Xác định độ phức tạp
        completeness = analysis_result.get("completeness_score", 50)
        has_files = file_analysis.get("successful_files", 0) > 0
        
        if completeness >= 80 and has_files:
            plan["complexity"] = "low"
            plan["estimated_time"] = 180  # 3 minutes
        elif completeness >= 60:
            plan["complexity"] = "medium" 
            plan["estimated_time"] = 300  # 5 minutes
        else:
            plan["complexity"] = "high"
            plan["estimated_time"] = 600  # 10 minutes
        
        # Xác định các bước workflow
        if completeness < 70:
            plan["workflow_steps"].append({
                "step": "clarification",
                "description": "Cần làm rõ thông tin với học sinh",
                "questions": analysis_result.get("clarification_questions", [])
            })
        
        plan["workflow_steps"].extend([
            {
                "step": "scholarship_search",
                "description": "Tìm kiếm học bổng phù hợp",
                "agent": "ScholarshipFinderAgent"
            },
            {
                "step": "profile_analysis", 
                "description": "Phân tích hồ sơ học sinh",
                "agent": "ProfileAnalyzerAgent"
            },
            {
                "step": "financial_calculation",
                "description": "Tính toán chi phí và tài chính",
                "agent": "FinancialCalculatorAgent"
            },
            {
                "step": "comprehensive_advice",
                "description": "Tư vấn tổng hợp và kế hoạch hành động",
                "agent": "AdvisorAgent"
            }
        ])
        
        return plan
    
    def _determine_next_agents(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Xác định thứ tự các agent tiếp theo"""
        
        completeness = analysis_result.get("completeness_score", 50)
        
        if completeness < 70:
            # Cần clarification trước
            return ["clarification_needed"]
        
        # Workflow bình thường
        return [
            "ScholarshipFinderAgent",
            "ProfileAnalyzerAgent", 
            "FinancialCalculatorAgent",
            "AdvisorAgent"
        ]
    
    async def clarify_information(
        self,
        original_request: str,
        user_response: str,
        previous_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Làm rõ thông tin dựa trên phản hồi của người dùng
        
        Args:
            original_request: Yêu cầu ban đầu
            user_response: Phản hồi của người dùng
            previous_analysis: Phân tích trước đó
            
        Returns:
            Thông tin đã được làm rõ
        """
        
        system_prompt = f"""
        {COORDINATOR_PROMPT}
        
        Bạn đã phân tích yêu cầu ban đầu và nhận được thêm thông tin từ học sinh.
        Hãy cập nhật và hoàn thiện thông tin.
        """
        
        messages = [
            {
                "role": "user",
                "content": f"""
                Yêu cầu ban đầu: {original_request}
                
                Phân tích trước đó: {json.dumps(previous_analysis, ensure_ascii=False)}
                
                Thông tin bổ sung từ học sinh: {user_response}
                
                Hãy cập nhật và hoàn thiện thông tin.
                """
            }
        ]
        
        response = await self.llm.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
            schema={
                "target_country": "string",
                "field_of_study": "string",
                "degree_level": "string", 
                "budget_range": "string",
                "profile_summary": "string",
                "completeness_score": "number 0-100",
                "updated_info": "string describing what was updated",
                "ready_for_processing": "boolean"
            }
        )
        
        return response
    
    def get_progress_message(self, step: str) -> str:
        """Tạo thông báo tiến trình cho UI"""
        
        progress_messages = {
            "analyzing": "🧠 Đang phân tích yêu cầu của bạn...",
            "processing_files": "📄 Đang xử lý hồ sơ của bạn...",
            "creating_plan": "📋 Đang tạo kế hoạch tư vấn...",
            "searching_scholarships": "🔍 Đang tìm kiếm học bổng phù hợp...",
            "analyzing_profile": "📊 Đang phân tích điểm mạnh của bạn...",
            "calculating_costs": "💰 Đang tính toán chi phí du học...",
            "generating_advice": "🎯 Đang tạo tư vấn cá nhân hóa...",
            "finalizing": "✨ Đang hoàn thiện kết quả..."
        }
        
        return progress_messages.get(step, "⚙️ Đang xử lý...")

# Global coordinator instance
coordinator_agent = CoordinatorAgent()