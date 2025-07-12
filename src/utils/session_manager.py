"""
Session Manager for Scholarship Advisor
Handles user sessions, state management, and data persistence
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from loguru import logger
import redis.asyncio as redis

from ..config.settings import settings

class SessionManager:
    """Manages user sessions and conversation state"""
    
    def __init__(self):
        self.use_redis = settings.USE_REDIS
        self.session_timeout = settings.SESSION_TIMEOUT
        self.redis_client = None
        self.local_sessions = {}  # Fallback for local storage
        
    async def initialize(self):
        """Initialize session storage"""
        if self.use_redis:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed, using local storage: {str(e)}")
                self.use_redis = False
        
        if not self.use_redis:
            logger.info("Using local session storage")
    
    async def create_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new session"""
        session_data = {
            "session_id": session_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "student_info": {},
            "uploaded_files": [],
            "conversation_history": [],
            "agent_results": {},
            "current_step": "initial",
            "user_email": None,
            "preferences": {}
        }
        
        await self.save_session(session_id, session_data)
        logger.info(f"Created new session: {session_id}")
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        try:
            if self.use_redis and self.redis_client:
                data = await self.redis_client.get(f"session:{session_id}")
                if data:
                    session_data = json.loads(data)
                    # Check if session expired
                    if time.time() - session_data.get("last_activity", 0) > self.session_timeout:
                        await self.delete_session(session_id)
                        return None
                    return session_data
            else:
                session_data = self.local_sessions.get(session_id)
                if session_data:
                    # Check if session expired
                    if time.time() - session_data.get("last_activity", 0) > self.session_timeout:
                        self.local_sessions.pop(session_id, None)
                        return None
                    return session_data
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
        
        return None
    
    async def save_session(self, session_id: str, session_data: Dict[str, Any]):
        """Save session data"""
        try:
            # Update last activity
            session_data["last_activity"] = time.time()
            
            if self.use_redis and self.redis_client:
                await self.redis_client.setex(
                    f"session:{session_id}",
                    self.session_timeout,
                    json.dumps(session_data, default=str)
                )
            else:
                self.local_sessions[session_id] = session_data
                
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {str(e)}")
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update specific session fields"""
        session_data = await self.get_session(session_id)
        if session_data:
            session_data.update(updates)
            await self.save_session(session_id, session_data)
            return session_data
        return None
    
    async def delete_session(self, session_id: str):
        """Delete a session"""
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(f"session:{session_id}")
            else:
                self.local_sessions.pop(session_id, None)
            
            logger.info(f"Deleted session: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
    
    async def add_message_to_history(
        self,
        session_id: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to conversation history"""
        session_data = await self.get_session(session_id)
        if session_data:
            message = {
                "timestamp": time.time(),
                "type": message_type,  # user, agent, system
                "content": content,
                "metadata": metadata or {}
            }
            
            if "conversation_history" not in session_data:
                session_data["conversation_history"] = []
                
            session_data["conversation_history"].append(message)
            
            # Keep only last 50 messages
            if len(session_data["conversation_history"]) > 50:
                session_data["conversation_history"] = session_data["conversation_history"][-50:]
            
            await self.save_session(session_id, session_data)
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        session_data = await self.get_session(session_id)
        return session_data.get("conversation_history", []) if session_data else []
    
    async def save_agent_result(
        self,
        session_id: str,
        agent_name: str,
        result: Dict[str, Any]
    ):
        """Save result from an agent"""
        session_data = await self.get_session(session_id)
        if session_data:
            if "agent_results" not in session_data:
                session_data["agent_results"] = {}
            
            session_data["agent_results"][agent_name] = {
                "timestamp": time.time(),
                "result": result
            }
            
            await self.save_session(session_id, session_data)
    
    async def get_agent_result(
        self,
        session_id: str,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get result from a specific agent"""
        session_data = await self.get_session(session_id)
        if session_data and "agent_results" in session_data:
            agent_data = session_data["agent_results"].get(agent_name)
            return agent_data.get("result") if agent_data else None
        return None
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (for local storage)"""
        if not self.use_redis:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, session_data in self.local_sessions.items():
                if current_time - session_data.get("last_activity", 0) > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self.local_sessions.pop(session_id, None)
                logger.info(f"Cleaned up expired session: {session_id}")
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            if self.use_redis and self.redis_client:
                keys = await self.redis_client.keys("session:*")
                active_sessions = len(keys)
            else:
                current_time = time.time()
                active_sessions = sum(
                    1 for session_data in self.local_sessions.values()
                    if current_time - session_data.get("last_activity", 0) <= self.session_timeout
                )
            
            return {
                "active_sessions": active_sessions,
                "storage_type": "redis" if self.use_redis else "local",
                "session_timeout": self.session_timeout
            }
        except Exception as e:
            logger.error(f"Error getting session stats: {str(e)}")
            return {"error": str(e)}

# Global session manager instance
session_manager = SessionManager()