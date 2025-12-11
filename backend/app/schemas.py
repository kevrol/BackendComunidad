from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: Optional[str] = "client"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None

    role: Optional[str] = None
class UserResponse(UserBase):
    id: int
    full_name: Optional[str] = None
    role: str
    location: Optional[str] = None

    bio: Optional[str] = None
    specialties: Optional[str] = None


    rating: Optional[float] = 0.0
    total_reviews: Optional[int] = 0
    jobs_completed: Optional[int] = 0
    jobs_active: Optional[int] = 0
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserSummary(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    role: str

    rating: float
    total_reviews: int
    bio: Optional[str] = None
    
    class Config:
        from_attributes = True

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class EmailVerification(BaseModel):
    token: str

# Service Schemas
class ServiceBase(BaseModel):
    title: str
    description: str
    category: str
    price: Optional[float] = None
    location: Optional[str] = None

class ServiceCreate(BaseModel):
    technician_id: int
    category: str
    description: str
    title: Optional[str] = "Servicio acordado por chat"  
    scheduled_date: Optional[datetime] = None
    address: Optional[str] = None

class ServiceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    location: Optional[str] = None
    status: Optional[str] = None

class ServiceResponse(ServiceBase):
    id: int
    technician_id: int
    technician: UserSummary
    title: str
    client_id: Optional[int]
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Review Schemas
class ReviewCreate(BaseModel):
    service_id: int
    rating: float = Field(..., ge=1.0, le=5.0)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    service_id: int
    client_id: int
    client: UserSummary
    technician_id: int
    rating: float
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Friend Request Schemas
class FriendRequestCreate(BaseModel):
    receiver_email: str

class FriendRequestResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    status: str
    created_at: datetime
    sender: Optional[UserSummary] = None 
    
    class Config:
        from_attributes = True

# Network Schemas
class NetworkNode(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_friend: bool
    is_technician: bool
    distance: int  # Distancia en la red (0 = tú, 1 = amigo directo, 2 = amigo de amigo)

class NetworkConnection(BaseModel):
    source: int
    target: int
    type: str  # 'friendship' o 'recommendation'

class TrustNetworkResponse(BaseModel):
    nodes: List[NetworkNode]
    connections: List[NetworkConnection]
    center_user_id: int

# Recommendation Schemas
class RecommendationResponse(BaseModel):
    technician: UserSummary
    score: float
    reason: str
    common_friends: int
    
    class Config:
        from_attributes = True

# Dashboard Stats
class ClientStats(BaseModel):
    contacts: int
    hired_services: int
    friends: int
    favorites: int
    profile_views: int
    unread_messages: int

class TechnicianStats(BaseModel):
    active_jobs: int
    completed_jobs: int
    rating: float
    total_reviews: int
    profile_views: int
    unread_messages: int

class DashboardResponse(BaseModel):
    user: UserResponse
    stats: ClientStats | TechnicianStats
    recent_activity: List[dict]

class UserSummaryWithEmail(BaseModel):
    id: int
    username: str
    email: str 
    full_name: Optional[str]
    role: str

    rating: float
    total_reviews: int
    
    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: int
    service_id: int
    client_id: int
    client: UserSummaryWithEmail  
    technician_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TechnicianProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    location: Optional[str]
    
    bio: Optional[str]
    specialties: Optional[str]

    rating: float
    total_reviews: int
    jobs_completed: int
    jobs_active: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    reviews: List[ReviewResponse] = [] 
    
    class Config:
        from_attributes = True
        

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    is_read: bool
    is_ai_generated: bool
    created_at: datetime
    sender: UserSummary
    
    class Config:
        from_attributes = True

class ConversationSummary(BaseModel):
    id: int
    client_id: int
    technician_id: int
    last_message: Optional[str]
    last_message_at: Optional[datetime]
    unread_count: int  
    other_user: UserSummary  
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConversationDetail(BaseModel):
    id: int
    client_id: int
    technician_id: int
    client: UserSummary
    technician: UserSummary
    messages: List[MessageResponse]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ SERVICE SCHEMAS ============

class ServiceCreate(BaseModel):
    technician_id: int
    category: str
    description: str
    scheduled_date: Optional[datetime] = None
    address: Optional[str] = None

class ServiceUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    price: Optional[float] = None

class ServiceAccept(BaseModel):
    price: float

class ServiceResponse(BaseModel):
    id: int
    client_id: Optional[int] = None
    technician_id: int
    category: str
    description: str
    status: str
    scheduled_date: Optional[datetime]
    completed_date: Optional[datetime]
    price: Optional[float]
    address: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime]
    client: Optional[UserSummary] = None
    technician: UserSummary
    
    class Config:
        from_attributes = True