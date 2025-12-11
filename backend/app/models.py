from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from .database import Base

def utc_now():
    return datetime.now(timezone.utc)

friendship = Table(
    'friendship',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('friend_id', Integer, ForeignKey('users.id')),
    Column('status', String(50), default='pending'),  
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)

# Tabla intermedia para favoritos
favorites = Table(
    'favorites',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('technician_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('created_at', DateTime, default=utc_now)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="client")  # 'client' o 'technician'
    location = Column(String(255), nullable=True)

    bio = Column(Text, nullable=True)
    specialties = Column(Text, nullable=True)  

    
    # Estadísticas
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    jobs_completed = Column(Integer, default=0)
    jobs_active = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relaciones
    friends = relationship(
        'User',
        secondary=friendship,
        primaryjoin=id == friendship.c.user_id,
        secondaryjoin=id == friendship.c.friend_id,
        backref='friend_of'
    )
    
    favorite_technicians = relationship(
        'User',
        secondary=favorites,
        primaryjoin=id == favorites.c.user_id,
        secondaryjoin=id == favorites.c.technician_id,
        backref='favorited_by'
    )
    
    services_offered = relationship('Service', foreign_keys='Service.technician_id', overlaps="client,technician")
    services_hired = relationship('Service', foreign_keys='Service.client_id', overlaps="client,technician")
    
    reviews_received = relationship('Review', foreign_keys='Review.technician_id', overlaps="client,technician")
    reviews_given = relationship('Review', foreign_keys='Review.client_id', overlaps="client,technician")


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('users.id'))
    technician_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(200), default="Servicio acordado por chat")
    category = Column(String(100))
    description = Column(Text)
    status = Column(String(50), default="pending")
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    price = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    client = relationship("User", foreign_keys=[client_id], overlaps="services_hired,services_offered")
    technician = relationship("User", foreign_keys=[technician_id], overlaps="services_hired,services_offered")
    reviews = relationship("Review", back_populates="service", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)    
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    service = relationship('Service', back_populates='reviews')
    # Cliente que da la review
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client = relationship('User', foreign_keys=[client_id], overlaps="reviews_given,reviews_received")
    # Técnico que recibe la review
    technician_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    technician = relationship('User', foreign_keys=[technician_id], overlaps="reviews_given,reviews_received")   
    # Contenido de la review
    rating = Column(Float, nullable=False)  
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    recommender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    technician_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    score = Column(Float, default=0.0)
    reason = Column(Text, nullable=True) 
    created_at = Column(DateTime, default=utc_now)


class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('users.id'))
    technician_id = Column(Integer, ForeignKey('users.id'))
    last_message = Column(Text, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    unread_client = Column(Integer, default=0)
    unread_technician = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    client = relationship("User", foreign_keys=[client_id])
    technician = relationship("User", foreign_keys=[technician_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    is_ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")