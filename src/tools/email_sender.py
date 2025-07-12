"""
Email Sender Tool using SendGrid for scholarship recommendations
"""
import asyncio
from typing import Dict, List, Optional, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from loguru import logger
import base64
import os
import json
from datetime import datetime

from ..config.settings import settings

class EmailSenderTool:
    """Email sender for scholarship recommendations and updates"""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.client = SendGridAPIClient(api_key=self.api_key)
        
    async def send_scholarship_recommendation(
        self,
        to_email: str,
        student_name: str,
        scholarships: List[Dict[str, Any]],
        financial_summary: Dict[str, Any],
        recommendations: List[str],
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send comprehensive scholarship recommendation email
        
        Args:
            to_email: Recipient email
            student_name: Student's name
            scholarships: List of recommended scholarships
            financial_summary: Financial breakdown
            recommendations: List of improvement recommendations
            additional_info: Additional information (visa, timeline, etc.)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Generate email content
            html_content = self._generate_scholarship_email_html(
                student_name=student_name,
                scholarships=scholarships,
                financial_summary=financial_summary,
                recommendations=recommendations,
                additional_info=additional_info
            )
            
            plain_content = self._generate_scholarship_email_plain(
                student_name=student_name,
                scholarships=scholarships,
                financial_summary=financial_summary,
                recommendations=recommendations
            )
            
            # Create email
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=f"🎓 Tư vấn học bổng cá nhân cho {student_name}",
                html_content=html_content,
                plain_text_content=plain_content
            )
            
            # Send email
            response = self.client.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Scholarship recommendation email sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending scholarship recommendation email: {str(e)}")
            return False
    
    def _generate_scholarship_email_html(
        self,
        student_name: str,
        scholarships: List[Dict[str, Any]],
        financial_summary: Dict[str, Any],
        recommendations: List[str],
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate HTML email content"""
        
        # Scholarship list HTML
        scholarship_html = ""
        for i, scholarship in enumerate(scholarships[:5], 1):
            scholarship_html += f"""
            <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #007bff;">
                <h4 style="color: #007bff; margin: 0 0 10px 0;">{i}. {scholarship.get('name', 'Học bổng không tên')}</h4>
                <p><strong>Tổ chức:</strong> {scholarship.get('organization', 'N/A')}</p>
                <p><strong>Giá trị:</strong> {scholarship.get('value', 'N/A')}</p>
                <p><strong>Yêu cầu:</strong> {scholarship.get('requirements', 'N/A')}</p>
                <p><strong>Hạn nộp:</strong> {scholarship.get('deadline', 'N/A')}</p>
                {f'<p><strong>Link:</strong> <a href="{scholarship.get("link", "#")}" target="_blank">Xem chi tiết</a></p>' if scholarship.get('link') else ''}
            </div>
            """
        
        # Recommendations HTML
        recommendations_html = ""
        for i, rec in enumerate(recommendations, 1):
            recommendations_html += f"<li style='margin: 8px 0;'>{rec}</li>"
        
        # Financial summary
        total_cost = financial_summary.get('total_cost', 0)
        currency = financial_summary.get('target_currency', 'VND')
        potential_savings = financial_summary.get('potential_scholarship_savings', 0)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Tư vấn học bổng</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
            
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px;">🎓 Tư Vấn Học Bổng Cá Nhân</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">Dành cho {student_name}</p>
            </div>
            
            <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #28a745; margin-top: 0;">💰 Tóm Tắt Tài Chính</h2>
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                    <div style="background: white; padding: 15px; border-radius: 8px; margin: 5px; flex: 1; min-width: 200px;">
                        <h4 style="margin: 0 0 10px 0; color: #dc3545;">Tổng Chi Phí Ước Tính</h4>
                        <p style="font-size: 24px; font-weight: bold; margin: 0; color: #dc3545;">{total_cost:,.0f} {currency}</p>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 8px; margin: 5px; flex: 1; min-width: 200px;">
                        <h4 style="margin: 0 0 10px 0; color: #28a745;">Tiềm Năng Tiết Kiệm</h4>
                        <p style="font-size: 24px; font-weight: bold; margin: 0; color: #28a745;">{potential_savings:,.0f} {currency}</p>
                    </div>
                </div>
            </div>
            
            <div style="margin-bottom: 30px;">
                <h2 style="color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 10px;">🏆 Học Bổng Được Đề Xuất</h2>
                {scholarship_html}
            </div>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #856404; margin-top: 0;">📋 Gợi Ý Cải Thiện Hồ Sơ</h2>
                <ul style="margin: 0; padding-left: 20px;">
                    {recommendations_html}
                </ul>
            </div>
            
            {self._generate_additional_info_html(additional_info) if additional_info else ''}
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin-top: 30px;">
                <p style="margin: 0; color: #6c757d;">
                    📧 Email này được tạo tự động bởi <strong>Scholarship Advisor AI</strong><br>
                    Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </p>
            </div>
            
        </body>
        </html>
        """
        
        return html_content
    
    def _generate_additional_info_html(self, additional_info: Dict[str, Any]) -> str:
        """Generate HTML for additional information section"""
        visa_info = additional_info.get('visa_requirements', '')
        timeline = additional_info.get('application_timeline', [])
        
        html = '<div style="background: #d1ecf1; padding: 20px; border-radius: 8px; margin-bottom: 25px;">'
        html += '<h2 style="color: #0c5460; margin-top: 0;">ℹ️ Thông Tin Bổ Sung</h2>'
        
        if visa_info:
            html += f'<h4>Thông Tin Visa:</h4><p>{visa_info}</p>'
        
        if timeline:
            html += '<h4>Timeline Nộp Đơn:</h4><ul>'
            for item in timeline:
                html += f'<li>{item}</li>'
            html += '</ul>'
        
        html += '</div>'
        return html
    
    def _generate_scholarship_email_plain(
        self,
        student_name: str,
        scholarships: List[Dict[str, Any]],
        financial_summary: Dict[str, Any],
        recommendations: List[str]
    ) -> str:
        """Generate plain text email content"""
        
        content = f"""
TƯ VẤN HỌC BỔNG CÁ NHÂN
Dành cho: {student_name}
Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M')}

=== TÓM TẮT TÀI CHÍNH ===
Tổng chi phí ước tính: {financial_summary.get('total_cost', 0):,.0f} {financial_summary.get('target_currency', 'VND')}
Tiềm năng tiết kiệm: {financial_summary.get('potential_scholarship_savings', 0):,.0f} {financial_summary.get('target_currency', 'VND')}

=== HỌC BỔNG ĐƯỢC ĐỀ XUẤT ===
"""
        
        for i, scholarship in enumerate(scholarships[:5], 1):
            content += f"""
{i}. {scholarship.get('name', 'Học bổng không tên')}
   - Tổ chức: {scholarship.get('organization', 'N/A')}
   - Giá trị: {scholarship.get('value', 'N/A')}
   - Yêu cầu: {scholarship.get('requirements', 'N/A')}
   - Hạn nộp: {scholarship.get('deadline', 'N/A')}
"""
        
        content += "\n=== GỢI Ý CẢI THIỆN HỒ SƠ ===\n"
        for i, rec in enumerate(recommendations, 1):
            content += f"{i}. {rec}\n"
        
        content += "\n---\nEmail này được tạo tự động bởi Scholarship Advisor AI"
        
        return content
    
    async def send_reminder_email(
        self,
        to_email: str,
        student_name: str,
        deadlines: List[Dict[str, Any]]
    ) -> bool:
        """Send scholarship deadline reminder email"""
        try:
            html_content = f"""
            <h2>⏰ Nhắc Nhở Hạn Nộp Học Bổng</h2>
            <p>Chào {student_name},</p>
            <p>Đây là nhắc nhở về các hạn nộp học bổng sắp tới:</p>
            <ul>
            """
            
            for deadline in deadlines:
                html_content += f"""
                <li><strong>{deadline.get('name', '')}</strong> - Hạn: {deadline.get('date', '')}</li>
                """
            
            html_content += """
            </ul>
            <p>Hãy chuẩn bị hồ sơ càng sớm càng tốt!</p>
            """
            
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=f"⏰ Nhắc nhở deadline học bổng - {student_name}",
                html_content=html_content
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Reminder email sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send reminder email: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reminder email: {str(e)}")
            return False

# Global email sender instance
email_sender = EmailSenderTool()