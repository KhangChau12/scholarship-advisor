"""
Chainlit UI Application for Scholarship Advisor
Modern, beautiful interface for scholarship consultation
"""
import chainlit as cl
import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from pathlib import Path

from ..agents.coordinator import coordinator_agent
from ..agents.scholarship_finder import scholarship_finder_agent
from ..agents.profile_analyzer import profile_analyzer_agent
from ..agents.financial_calculator import financial_calculator_agent
from ..agents.advisor import advisor_agent
from ..config.settings import settings

# Global state for multi-step conversation
class ScholarshipSession:
    def __init__(self):
        self.student_info = {}
        self.uploaded_files = []
        self.scholarship_results = {}
        self.profile_results = {}
        self.financial_results = {}
        self.final_advice = {}
        self.current_step = "initial"
        self.user_email = None

@cl.on_chat_start
async def start():
    """Initialize the scholarship consultation session"""
    
    # Store session data
    cl.user_session.set("scholarship_session", ScholarshipSession())
    
    # Welcome message with beautiful formatting
    welcome_message = """
# 🎓 Chào mừng bạn đến với Scholarship Advisor AI

**Trợ lý tư vấn học bổng thông minh dành cho học sinh Việt Nam**

---

## 🚀 Tôi có thể giúp bạn:

✨ **Tìm kiếm học bổng** phù hợp với hồ sơ và ngành học  
📊 **Phân tích hồ sơ** của bạn so với yêu cầu học bổng  
💰 **Tính toán chi phí** du học và tiết kiệm từ học bổng  
📋 **Tạo kế hoạch** cải thiện hồ sơ và timeline nộp đơn  
🎯 **Tư vấn chiến lược** du học toàn diện  

---

## 📝 Để bắt đầu, hãy cho tôi biết:

1. **Quốc gia** bạn muốn du học
2. **Ngành học** bạn quan tâm  
3. **Bậc học** (cử nhân, thạc sĩ, tiến sĩ)
4. **Hồ sơ hiện tại** của bạn (GPA, điểm thi, hoạt động...)

💡 **Tip**: Bạn có thể upload file hồ sơ (PDF, DOCX) để tôi phân tích chi tiết hơn!
    """
    
    await cl.Message(content=welcome_message).send()
    
    # Set up file upload
    files = None
    while files is None:
        files = await cl.AskFileMessage(
            content="📎 **Tùy chọn**: Upload hồ sơ của bạn (PDF, DOCX) hoặc nhấn **Continue** để tiếp tục:",
            accept=["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"],
            max_size_mb=10,
            timeout=180,
        ).send()
        
        if files:
            session = cl.user_session.get("scholarship_session")
            session.uploaded_files = [file.path for file in files]
            cl.user_session.set("scholarship_session", session)
            
            await cl.Message(
                content=f"✅ Đã nhận {len(files)} file. Bây giờ hãy chia sẻ thông tin du học của bạn!"
            ).send()
        break

@cl.on_message
async def main(message: cl.Message):
    """Handle user messages and coordinate the scholarship consultation"""
    
    session = cl.user_session.get("scholarship_session")
    user_input = message.content
    
    # Progress indicator
    progress_msg = cl.Message(content="🤔 Đang xử lý thông tin của bạn...")
    await progress_msg.send()
    
    try:
        if session.current_step == "initial":
            await handle_initial_consultation(user_input, session, progress_msg)
        elif session.current_step == "clarification":
            await handle_clarification(user_input, session, progress_msg)
        elif session.current_step == "email_collection":
            await handle_email_collection(user_input, session, progress_msg)
        else:
            await cl.Message(content="❓ Tôi không hiểu. Bạn có thể nói rõ hơn không?").send()
            
    except Exception as e:
        logger.error(f"Error in main handler: {str(e)}")
        await cl.Message(
            content="😕 Xin lỗi, đã có lỗi xảy ra. Hãy thử lại hoặc liên hệ hỗ trợ."
        ).send()

async def handle_initial_consultation(user_input: str, session: ScholarshipSession, progress_msg: cl.Message):
    """Handle the initial consultation request"""
    
    # Update progress
    await progress_msg.update(content="🧠 **Bước 1/5**: Đang phân tích yêu cầu của bạn...")
    
    # Step 1: Coordinator analysis
    coordinator_result = await coordinator_agent.process_initial_request(
        user_message=user_input,
        uploaded_files=session.uploaded_files
    )
    
    if not coordinator_result.get("success"):
        await cl.Message(content="❌ Có lỗi khi phân tích yêu cầu. Hãy thử lại.").send()
        return
    
    session.student_info = coordinator_result["analysis"]
    
    # Check if need clarification
    completeness = session.student_info.get("completeness_score", 0)
    if completeness < 70:
        session.current_step = "clarification"
        questions = session.student_info.get("clarification_questions", [])
        
        clarification_message = f"""
## 🤔 Tôi cần thêm thông tin để tư vấn tốt hơn:

{chr(10).join([f"• {q}" for q in questions])}

**Hãy trả lời các câu hỏi trên để tôi có thể đưa ra tư vấn chính xác nhất!**
        """
        
        await progress_msg.update(content=clarification_message)
        return
    
    # Continue with full consultation
    await run_full_consultation(session, progress_msg)

async def handle_clarification(user_input: str, session: ScholarshipSession, progress_msg: cl.Message):
    """Handle clarification from user"""
    
    await progress_msg.update(content="🔄 Đang cập nhật thông tin...")
    
    # Update information with clarification
    updated_info = await coordinator_agent.clarify_information(
        original_request="",  # Can be stored in session
        user_response=user_input,
        previous_analysis=session.student_info
    )
    
    session.student_info = updated_info
    
    if updated_info.get("ready_for_processing", False):
        session.current_step = "consultation"
        await run_full_consultation(session, progress_msg)
    else:
        await cl.Message(content="🤔 Tôi vẫn cần thêm thông tin. Bạn có thể chia sẻ thêm không?").send()

async def run_full_consultation(session: ScholarshipSession, progress_msg: cl.Message):
    """Run the complete scholarship consultation workflow"""
    
    try:
        # Step 2: Find scholarships
        await progress_msg.update(content="🔍 **Bước 2/5**: Đang tìm kiếm học bổng phù hợp...")
        
        scholarship_result = await scholarship_finder_agent.find_scholarships(
            student_info=session.student_info,
            search_depth="comprehensive"
        )
        session.scholarship_results = scholarship_result
        
        # Step 3: Analyze profile  
        await progress_msg.update(content="📊 **Bước 3/5**: Đang phân tích hồ sơ của bạn...")
        
        file_analysis = None
        if session.uploaded_files:
            file_analysis = {"successful_files": len(session.uploaded_files), "results": []}
        
        profile_result = await profile_analyzer_agent.analyze_student_profile(
            student_info=session.student_info,
            file_analysis=file_analysis,
            scholarship_requirements=[s.get("requirements", {}) for s in scholarship_result.get("scholarships", [])]
        )
        session.profile_results = profile_result
        
        # Step 4: Calculate finances
        await progress_msg.update(content="💰 **Bước 4/5**: Đang tính toán chi phí và tài chính...")
        
        financial_result = await financial_calculator_agent.calculate_study_costs(
            student_info=session.student_info,
            scholarships=scholarship_result.get("scholarships", []),
            target_currency="VND"
        )
        session.financial_results = financial_result
        
        # Step 5: Generate comprehensive advice
        await progress_msg.update(content="🎯 **Bước 5/5**: Đang tạo tư vấn cá nhân hóa...")
        
        advice_result = await advisor_agent.generate_comprehensive_advice(
            student_info=session.student_info,
            scholarship_analysis=scholarship_result,
            profile_analysis=profile_result,
            financial_analysis=financial_result
        )
        session.final_advice = advice_result
        
        # Display results
        await display_consultation_results(session, progress_msg)
        
        # Ask for email
        session.current_step = "email_collection"
        await cl.Message(
            content="📧 **Muốn nhận báo cáo chi tiết qua email?** Hãy chia sẻ email của bạn, hoặc gõ 'skip' để bỏ qua."
        ).send()
        
    except Exception as e:
        logger.error(f"Error in consultation workflow: {str(e)}")
        await progress_msg.update(content="❌ Có lỗi trong quá trình tư vấn. Vui lòng thử lại.")

async def display_consultation_results(session: ScholarshipSession, progress_msg: cl.Message):
    """Display the comprehensive consultation results"""
    
    final_advice = session.final_advice
    scholarships = final_advice.get("prioritized_scholarships", [])[:3]
    financial_summary = session.financial_results.get("financial_summary", {})
    
    # Executive Summary
    summary_content = f"""
# 🎯 Kết Quả Tư Vấn Học Bổng

## 📋 Tóm Tắt Tổng Quan
{final_advice.get("executive_summary", {}).get("overall_assessment", "Đang tạo tóm tắt...")}

**Triển vọng thành công**: {final_advice.get("success_analysis", {}).get("confidence_level", "Trung bình")} 
({final_advice.get("success_analysis", {}).get("overall_success_probability", 0)*100:.0f}%)

---
"""
    
    # Top Scholarships
    if scholarships:
        summary_content += "## 🏆 Top 3 Học Bổng Được Đề Xuất\n\n"
        
        for i, scholarship in enumerate(scholarships, 1):
            priority_emoji = "🔥" if scholarship.get("priority") == "high" else "⭐" if scholarship.get("priority") == "medium" else "💡"
            
            summary_content += f"""
### {priority_emoji} {i}. {scholarship.get('name', 'Học bổng không tên')}

**🏛️ Tổ chức**: {scholarship.get('organization', 'N/A')}  
**💰 Giá trị**: {scholarship.get('value', 'N/A')}  
**📅 Hạn nộp**: {scholarship.get('deadline', 'N/A')}  
**🎯 Độ phù hợp**: {scholarship.get('priority_score', 0):.1f}/100  

**💡 Lý do đề xuất**: {scholarship.get('recommendation_reason', 'Phù hợp với hồ sơ của bạn')}

---
"""
    
    # Financial Summary
    total_cost = financial_summary.get("total_program_cost", 0)
    savings = financial_summary.get("best_scholarship_savings", 0)
    net_cost = financial_summary.get("net_cost_after_scholarships", 0)
    currency = financial_summary.get("currency", "VND")
    
    summary_content += f"""
## 💰 Tóm Tắt Tài Chính

| Khoản Chi | Số Tiền |
|-----------|---------|
| **Tổng chi phí ước tính** | {total_cost:,.0f} {currency} |
| **Tiết kiệm từ học bổng** | {savings:,.0f} {currency} |
| **Chi phí thực tế** | {net_cost:,.0f} {currency} |
| **Tỷ lệ tiết kiệm** | {financial_summary.get('savings_percentage', 0):.1f}% |

---
"""
    
    # Improvement Plan
    improvement_plan = final_advice.get("improvement_plan", {})
    immediate_actions = improvement_plan.get("immediate_actions", [])
    
    if immediate_actions:
        summary_content += "## 🚀 Kế Hoạch Hành Động Ngay\n\n"
        
        for i, action in enumerate(immediate_actions[:5], 1):
            priority_badge = "🔴" if action.get("priority") == "high" else "🟡" if action.get("priority") == "medium" else "🟢"
            
            summary_content += f"""
**{i}. {action.get('action', '')}** {priority_badge}
- ⏰ Timeline: {action.get('timeline', 'N/A')}
- 📈 Impact: {action.get('expected_impact', 'N/A')}
- 💵 Chi phí: {action.get('cost', 'N/A')}

"""
    
    # Final advice
    final_recommendations = final_advice.get("final_recommendations", {})
    advice_list = final_recommendations.get("final_advice", [])
    
    if advice_list:
        summary_content += "\n## 💡 Lời Khuyên Cuối Cùng\n\n"
        summary_content += "\n".join([f"✅ {advice}" for advice in advice_list])
    
    await progress_msg.update(content=summary_content)

async def handle_email_collection(user_input: str, session: ScholarshipSession, progress_msg: cl.Message):
    """Handle email collection for sending detailed report"""
    
    if user_input.lower().strip() in ["skip", "bỏ qua", "không"]:
        await cl.Message(content="✅ **Hoàn tất tư vấn!** Cảm ơn bạn đã sử dụng Scholarship Advisor AI. Chúc bạn thành công! 🎓").send()
        return
    
    # Validate email (simple check)
    if "@" in user_input and "." in user_input:
        session.user_email = user_input.strip()
        
        await progress_msg.update(content="📨 Đang gửi báo cáo chi tiết...")
        
        try:
            # Send email using advisor agent
            email_sent = await advisor_agent._send_comprehensive_email(
                user_email=session.user_email,
                student_info=session.student_info,
                recommendations=session.final_advice.get("final_recommendations", {})
            )
            
            if email_sent:
                await progress_msg.update(content=f"✅ **Đã gửi báo cáo chi tiết đến {session.user_email}**\n\nCảm ơn bạn đã sử dụng Scholarship Advisor AI! 🎓")
            else:
                await progress_msg.update(content="❌ Có lỗi khi gửi email. Vui lòng kiểm tra lại địa chỉ email.")
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            await progress_msg.update(content="❌ Có lỗi khi gửi email. Vui lòng thử lại sau.")
    else:
        await cl.Message(content="❌ Email không hợp lệ. Vui lòng nhập lại hoặc gõ 'skip' để bỏ qua.").send()

@cl.on_chat_start
async def setup_ui():
    # Load custom CSS
    css_path = Path(__file__).parent.parent.parent / "static" / "css" / "custom.css"
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        await cl.Message(
            content=f"<style>{css_content}</style>",
            author="system"
        ).send()

# Custom styling
@cl.on_chat_start
async def set_custom_styling():
    """Apply custom CSS styling"""
    
    custom_css = """
    <style>
    .chainlit-message {
        font-family: 'Inter', sans-serif;
    }
    
    .chainlit-message h1 {
        color: #667eea;
        border-bottom: 2px solid #667eea;
        padding-bottom: 10px;
    }
    
    .chainlit-message h2 {
        color: #764ba2;
        margin-top: 25px;
    }
    
    .chainlit-message table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }
    
    .chainlit-message th, .chainlit-message td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }
    
    .chainlit-message th {
        background-color: #f8f9fa;
        font-weight: bold;
    }
    
    .progress-indicator {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
    }
    </style>
    """
    
    await cl.Message(content=custom_css).send()

if __name__ == "__main__":
    cl.run(
        host="0.0.0.0",
        port=8000,
        debug=settings.DEBUG
    )