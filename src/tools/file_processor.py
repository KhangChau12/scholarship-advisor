"""
File Processing Tool for student documents (PDF, DOCX)
"""
import asyncio
import os
import tempfile
from typing import Dict, List, Optional, Any
import fitz  # PyMuPDF
from docx import Document
from loguru import logger
import re
import json

from ..config.settings import settings

class FileProcessorTool:
    """File processor for student academic documents"""
    
    def __init__(self):
        self.max_file_size = settings.MAX_FILE_SIZE * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        
    def validate_file(self, file_path: str, file_size: int) -> Dict[str, Any]:
        """
        Validate uploaded file
        
        Args:
            file_path: Path to the file
            file_size: Size of file in bytes
            
        Returns:
            Validation result
        """
        result = {
            "valid": False,
            "errors": [],
            "file_type": None,
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }
        
        # Check file size
        if file_size > self.max_file_size:
            result["errors"].append(f"File quá lớn. Tối đa {settings.MAX_FILE_SIZE}MB")
            return result
        
        # Check file extension
        file_extension = os.path.splitext(file_path)[1][1:].lower()
        if file_extension not in self.allowed_extensions:
            result["errors"].append(f"Định dạng file không hỗ trợ. Chỉ chấp nhận: {', '.join(self.allowed_extensions)}")
            return result
        
        result["file_type"] = file_extension
        result["valid"] = True
        
        return result
    
    async def extract_text_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text content from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted content and metadata
        """
        try:
            doc = fitz.open(file_path)
            
            text_content = ""
            page_contents = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                text_content += page_text + "\n"
                page_contents.append({
                    "page": page_num + 1,
                    "content": page_text.strip()
                })
            
            doc.close()
            
            return {
                "success": True,
                "content": text_content.strip(),
                "page_count": len(doc),
                "pages": page_contents,
                "file_type": "pdf"
            }
            
        except Exception as e:
            logger.error(f"Error extracting PDF content: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "file_type": "pdf"
            }
    
    async def extract_text_from_docx(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text content from DOCX file
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted content and metadata
        """
        try:
            doc = Document(file_path)
            
            text_content = ""
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                para_text = paragraph.text.strip()
                if para_text:
                    text_content += para_text + "\n"
                    paragraphs.append(para_text)
            
            return {
                "success": True,
                "content": text_content.strip(),
                "paragraph_count": len(paragraphs),
                "paragraphs": paragraphs,
                "file_type": "docx"
            }
            
        except Exception as e:
            logger.error(f"Error extracting DOCX content: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "file_type": "docx"
            }
    
    async def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from supported file types
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted content
        """
        file_extension = os.path.splitext(file_path)[1][1:].lower()
        
        if file_extension == "pdf":
            return await self.extract_text_from_pdf(file_path)
        elif file_extension in ["docx", "doc"]:
            return await self.extract_text_from_docx(file_path)
        elif file_extension == "txt":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "success": True,
                    "content": content,
                    "file_type": "txt"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "content": "",
                    "file_type": "txt"
                }
        else:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_extension}",
                "content": "",
                "file_type": file_extension
            }
    
    def analyze_academic_profile(self, text_content: str) -> Dict[str, Any]:
        """
        Analyze academic profile from extracted text
        
        Args:
            text_content: Extracted text from document
            
        Returns:
            Structured academic profile
        """
        profile = {
            "personal_info": {},
            "education": {},
            "achievements": [],
            "skills": [],
            "languages": [],
            "activities": [],
            "certifications": [],
            "gpa": None,
            "test_scores": {}
        }
        
        # Extract GPA
        gpa_patterns = [
            r"GPA[:\s]*(\d+\.?\d*)",
            r"Grade Point Average[:\s]*(\d+\.?\d*)",
            r"Điểm trung bình[:\s]*(\d+\.?\d*)",
        ]
        
        for pattern in gpa_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                try:
                    profile["gpa"] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Extract test scores (IELTS, TOEFL, SAT, etc.)
        test_patterns = {
            "ielts": r"IELTS[:\s]*(\d+\.?\d*)",
            "toefl": r"TOEFL[:\s]*(\d+)",
            "sat": r"SAT[:\s]*(\d+)",
            "gre": r"GRE[:\s]*(\d+)",
            "gmat": r"GMAT[:\s]*(\d+)"
        }
        
        for test_name, pattern in test_patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                try:
                    profile["test_scores"][test_name.upper()] = int(float(match.group(1)))
                except ValueError:
                    continue
        
        # Extract achievements and awards
        achievement_keywords = [
            "award", "prize", "honor", "recognition", "achievement",
            "giải thưởng", "thành tích", "danh hiệu", "khen thưởng"
        ]
        
        lines = text_content.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in achievement_keywords):
                if len(line.strip()) > 10:  # Avoid very short lines
                    profile["achievements"].append(line.strip())
        
        # Extract skills
        skill_keywords = [
            "skill", "programming", "software", "language", "technology",
            "kỹ năng", "lập trình", "phần mềm", "công nghệ"
        ]
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in skill_keywords):
                if len(line.strip()) > 5:
                    profile["skills"].append(line.strip())
        
        # Extract languages
        language_patterns = [
            r"English[:\s]*([A-Za-z\s]+)",
            r"Vietnamese[:\s]*([A-Za-z\s]+)",
            r"Chinese[:\s]*([A-Za-z\s]+)",
            r"Tiếng Anh[:\s]*([A-Za-zÀ-ỹ\s]+)",
            r"Tiếng Việt[:\s]*([A-Za-zÀ-ỹ\s]+)",
        ]
        
        for pattern in language_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                language_info = match.group(0).strip()
                if language_info not in profile["languages"]:
                    profile["languages"].append(language_info)
        
        # Extract activities
        activity_keywords = [
            "volunteer", "club", "society", "organization", "activity",
            "tình nguyện", "câu lạc bộ", "tổ chức", "hoạt động"
        ]
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in activity_keywords):
                if len(line.strip()) > 10:
                    profile["activities"].append(line.strip())
        
        return profile
    
    async def process_student_profile(self, file_path: str) -> Dict[str, Any]:
        """
        Process student profile document comprehensively
        
        Args:
            file_path: Path to student profile document
            
        Returns:
            Comprehensive profile analysis
        """
        # Extract text content
        extraction_result = await self.extract_text_from_file(file_path)
        
        if not extraction_result["success"]:
            return {
                "success": False,
                "error": extraction_result["error"],
                "profile": {}
            }
        
        # Analyze academic profile
        profile = self.analyze_academic_profile(extraction_result["content"])
        
        # Add metadata
        profile["document_info"] = {
            "file_type": extraction_result["file_type"],
            "content_length": len(extraction_result["content"]),
            "processed_at": asyncio.get_event_loop().time()
        }
        
        return {
            "success": True,
            "profile": profile,
            "raw_content": extraction_result["content"][:1000] + "..." if len(extraction_result["content"]) > 1000 else extraction_result["content"]
        }
    
    def calculate_profile_score(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate profile strength score for scholarship matching
        
        Args:
            profile: Analyzed academic profile
            
        Returns:
            Profile scoring breakdown
        """
        scores = {
            "academic": 0,
            "extracurricular": 0,
            "language": 0,
            "achievements": 0,
            "total": 0
        }
        
        # Academic score (40% weight)
        if profile.get("gpa"):
            if profile["gpa"] >= 3.5:
                scores["academic"] += 30
            elif profile["gpa"] >= 3.0:
                scores["academic"] += 20
            elif profile["gpa"] >= 2.5:
                scores["academic"] += 10
        
        # Test scores
        test_scores = profile.get("test_scores", {})
        if "IELTS" in test_scores and test_scores["IELTS"] >= 6.5:
            scores["academic"] += 10
        if "TOEFL" in test_scores and test_scores["TOEFL"] >= 90:
            scores["academic"] += 10
        if "SAT" in test_scores and test_scores["SAT"] >= 1200:
            scores["academic"] += 10
        
        # Extracurricular score (25% weight)
        activities_count = len(profile.get("activities", []))
        scores["extracurricular"] = min(activities_count * 5, 25)
        
        # Language score (15% weight)
        languages_count = len(profile.get("languages", []))
        scores["language"] = min(languages_count * 5, 15)
        
        # Achievements score (20% weight)
        achievements_count = len(profile.get("achievements", []))
        scores["achievements"] = min(achievements_count * 4, 20)
        
        # Calculate total
        scores["total"] = sum(scores.values())
        
        # Determine strength level
        if scores["total"] >= 80:
            strength = "Excellent"
        elif scores["total"] >= 60:
            strength = "Good"
        elif scores["total"] >= 40:
            strength = "Average"
        else:
            strength = "Needs Improvement"
        
        return {
            "scores": scores,
            "strength_level": strength,
            "total_score": scores["total"],
            "max_score": 100
        }

# Global file processor instance
file_processor = FileProcessorTool()