from fastapi import FastAPI, Depends, HTTPException, status, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc, and_
from datetime import timedelta, datetime
from typing import List, Optional
from .gemini_service import gemini_service  
from .database import engine, get_db
from . import models, schemas, auth, email_service, services as app_services
from .config import settings, is_production
from app.config import get_cors_origins
import json

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kaimo API",
    version="4.0.0",
    docs_url="/docs" if not is_production() else None,
    redoc_url="/redoc" if not is_production() else None
)
#CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#AUTENTIFICACION

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": "production" if is_production() else "development"}

@app.post("/api/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registrar un nuevo usuario"""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
    
    verification_token = auth.generate_verification_token()
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=auth.get_password_hash(user.password),
        role=user.role or "client",
        verification_token=verification_token,
        is_active=True,
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    try:
        email_service.send_verification_email(
            email_to=user.email,
            username=user.username,
            token=verification_token
        )
    except Exception as e:
        print(f"Error enviando email: {e}")
    
    return db_user

@app.post("/api/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """Iniciar sesión"""
    user = auth.authenticate_user(db, user_credentials.email, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Por favor verifica tu email antes de iniciar sesión"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/verify-email")
def verify_email(verification: schemas.EmailVerification, db: Session = Depends(get_db)):
    """Verificar email del usuario"""
    user = db.query(models.User).filter(
        models.User.verification_token == verification.token
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Token de verificación inválido")
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verificado exitosamente"}

#USUARIOS

@app.get("/api/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    """Obtener información del usuario actual"""
    return current_user

@app.put("/api/users/me", response_model=schemas.UserResponse)
async def update_user(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualizar perfil del usuario"""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.location is not None:
        current_user.location = user_update.location
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    if user_update.specialties is not None:
        current_user.specialties = user_update.specialties
    if user_update.role is not None:
        current_user.role = user_update.role
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.post("/api/users/switch-role")
async def switch_role(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cambiar entre cliente y técnico"""
    if current_user.role == "client":
        current_user.role = "technician"
    else:
        current_user.role = "client"
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return {"message": f"Rol cambiado a {current_user.role}", "new_role": current_user.role}

@app.get("/api/users/search", response_model=List[schemas.UserSummary])
def search_users(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Buscar usuarios por nombre o email"""
    users = db.query(models.User).filter(
        models.User.id != current_user.id,
        models.User.username.ilike(f"%{query}%") | models.User.email.ilike(f"%{query}%")
    ).limit(10).all()
    
    return users

# ==================== RED DE CONFIANZA ====================

@app.post("/api/friends/request", response_model=schemas.FriendRequestResponse)
def send_friend_request(
    request: schemas.FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Enviar solicitud de amistad"""
    friend_request = app_services.FriendshipService.send_friend_request(
        db, current_user.id, request.receiver_email
    )
    
    if not friend_request:
        raise HTTPException(status_code=400, detail="No se pudo enviar la solicitud")
    
    return friend_request

@app.post("/api/friends/accept/{request_id}")
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Aceptar solicitud de amistad"""
    success = app_services.FriendshipService.accept_friend_request(
        db, request_id, current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="No se pudo aceptar la solicitud")
    
    return {"message": "Solicitud aceptada"}

@app.post("/api/friends/reject/{request_id}")
def reject_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Rechazar solicitud de amistad"""
    request = db.query(models.FriendRequest).filter(
        models.FriendRequest.id == request_id,
        models.FriendRequest.receiver_id == current_user.id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    request.status = "rejected"
    db.commit()
    
    return {"message": "Solicitud rechazada"}

@app.get("/api/friends/requests/pending", response_model=List[schemas.FriendRequestResponse])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener solicitudes de amistad pendientes"""
    requests = db.query(models.FriendRequest).filter(
        models.FriendRequest.receiver_id == current_user.id,
        models.FriendRequest.status == "pending"
    ).all()
    
    result = []
    for request in requests:
        sender = db.query(models.User).filter(models.User.id == request.sender_id).first()
        request_dict = {
            "id": request.id,
            "sender_id": request.sender_id,
            "receiver_id": request.receiver_id,
            "status": request.status,
            "created_at": request.created_at,
            "sender": schemas.UserSummary(
                id=sender.id,
                email=sender.email,
                username=sender.username,
                full_name=sender.full_name,
                role=sender.role,

                rating=sender.rating,
                total_reviews=sender.total_reviews,
                bio=sender.bio
            ) if sender else None
        }
        result.append(request_dict)
    
    return result

@app.get("/api/friends", response_model=List[schemas.UserSummary])
def get_friends(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener lista de amigos"""
    friends = app_services.FriendshipService.get_friends(db, current_user.id)
    return friends

@app.delete("/api/friends/{friend_id}")
def remove_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Eliminar un amigo"""
    friend = db.query(models.User).filter(models.User.id == friend_id).first()
    if not friend:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if friend in current_user.friends:
        current_user.friends.remove(friend)
        db.commit()
        return {"message": "Amigo eliminado"}
    
    raise HTTPException(status_code=400, detail="No son amigos")

@app.get("/api/network/graph", response_model=schemas.TrustNetworkResponse)
def get_trust_network_graph(
    max_depth: int = 2,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener el grafo de red de confianza del usuario"""
    nodes = []
    connections = []
    visited = set()
    
    def add_node(user: models.User, distance: int, is_friend: bool = False):
        if user.id in visited:
            return
        visited.add(user.id)
        
        nodes.append({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_friend": is_friend,
            "is_technician": user.role == "technician",
            "distance": distance,
            "rating": user.rating,
            "total_reviews": user.total_reviews
        })
    
    # Agregar nodo central (usuario actual)
    add_node(current_user, 0, False)
    
    # Nivel 1: Amigos directos
    friendships = db.query(models.friendship).filter(
        or_(
            models.friendship.c.user_id == current_user.id,
            models.friendship.c.friend_id == current_user.id
        ),
        models.friendship.c.status == "accepted"
    ).all()
    
    for friendship in friendships:
        friend_id = friendship.friend_id if friendship.user_id == current_user.id else friendship.user_id
        friend = db.query(models.User).filter(models.User.id == friend_id).first()
        
        if friend:
            add_node(friend, 1, True)
            connections.append({
                "source": current_user.id,
                "target": friend.id,
                "type": "friendship"
            })
            
            # Nivel 2: Técnicos recomendados (si max_depth >= 2)
            if max_depth >= 2:
                # Obtener servicios contratados por el amigo
                services = db.query(models.Service).filter(
                    models.Service.client_id == friend.id,
                    models.Service.status == "completed"
                ).all()
                
                for service in services:
                    # Obtener reviews del técnico
                    review = db.query(models.Review).filter(
                        models.Review.service_id == service.id,
                        models.Review.client_id == friend.id,
                        models.Review.rating >= 4
                    ).first()
                    
                    if review:
                        technician = db.query(models.User).filter(
                            models.User.id == service.technician_id
                        ).first()
                        
                        if technician and technician.id != current_user.id:
                            add_node(technician, 2, False)
                            connections.append({
                                "source": friend.id,
                                "target": technician.id,
                                "type": "recommendation"
                            })
    return {
        "nodes": nodes,
        "connections": connections,
        "center_user_id": current_user.id
    }
# SERVICIOS

@app.post("/api/services", response_model=schemas.ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Crear un nuevo servicio (solo técnicos)"""
    if current_user.role != "technician":
        raise HTTPException(status_code=403, detail="Solo los técnicos pueden crear servicios")
    
    db_service = models.Service(
        **service.dict(),
        technician_id=current_user.id
    )
    
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    return db_service

@app.get("/api/services/hired", response_model=List[schemas.ServiceResponse])
def get_hired_services(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener servicios contratados por el cliente"""
    services = db.query(models.Service).filter(
        models.Service.client_id == current_user.id
    ).all()
    
    return services

@app.post("/api/services/{service_id}/hire")
def hire_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Contratar un servicio"""
    service = db.query(models.Service).filter(
        models.Service.id == service_id,
        models.Service.status == "available"
    ).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no disponible")
    
    service.client_id = current_user.id
    service.status = "in_progress"
    
    # Actualizar estadísticas del técnico
    technician = service.technician
    technician.jobs_active += 1
    
    db.commit()
    
    return {"message": "Servicio contratado exitosamente"}

@app.post("/api/services/{service_id}/complete")
def complete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Marcar servicio como completado (solo técnico)"""
    service = db.query(models.Service).filter(
        models.Service.id == service_id,
        models.Service.technician_id == current_user.id,
        models.Service.status == "in_progress"
    ).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    service.status = "completed"
    service.completed_at = datetime.utcnow()
    
    # Actualizar estadísticas
    current_user.jobs_active -= 1
    current_user.jobs_completed += 1
    
    db.commit()
    
    return {"message": "Servicio marcado como completado"}

@app.get("/api/services/search", response_model=List[schemas.ServiceResponse])
def search_services(
    category: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Buscar servicios disponibles"""
    query = db.query(models.Service).filter(
        models.Service.status == "available"
    )
    
    if category:
        query = query.filter(models.Service.category == category)
    
    if location:
        query = query.filter(models.Service.location.ilike(f"%{location}%"))
    
    services = query.all()
    return services

# RECOMENDACIONES

@app.get("/api/recommendations", response_model=List[schemas.RecommendationResponse])
def get_recommendations(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener técnicos recomendados basados en la red de confianza"""
    return app_services.RecommendationService.get_recommended_technicians(
        db, current_user.id, category
    )

@app.get("/api/technicians/search", response_model=List[schemas.UserSummary])
def search_technicians(
    query: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Buscar técnicos"""
    db_query = db.query(models.User).filter(models.User.role == "technician")
    
    if query:
        db_query = db_query.filter(
            models.User.username.ilike(f"%{query}%") |
            models.User.full_name.ilike(f"%{query}%") |
            models.User.bio.ilike(f"%{query}%")
        )
    
    if location:
        db_query = db_query.filter(models.User.location.ilike(f"%{location}%"))
    
    if category:
        db_query = db_query.filter(models.User.specialties.ilike(f"%{category}%"))
    
    technicians = db_query.limit(20).all()
    return technicians

# REVIEWS

@app.post("/api/reviews", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Crear una review para un servicio completado"""
    db_review = app_services.ReviewService.create_review(db, review, current_user.id)
    
    if not db_review:
        raise HTTPException(status_code=400, detail="No se pudo crear la review")
    
    return db_review

@app.get("/api/reviews/technician/{technician_id}", response_model=List[schemas.ReviewResponse])
def get_technician_reviews(
    technician_id: int,
    db: Session = Depends(get_db)
):
    """Obtener reviews de un técnico"""
    reviews = db.query(models.Review).filter(
        models.Review.technician_id == technician_id
    ).order_by(models.Review.created_at.desc()).all()
    
    return reviews

# FAVORITOS

@app.post("/api/favorites/{technician_id}")
def add_favorite(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Agregar técnico a favoritos"""
    technician = db.query(models.User).filter(
        models.User.id == technician_id,
        models.User.role == "technician"
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    
    if technician not in current_user.favorite_technicians:
        current_user.favorite_technicians.append(technician)
        db.commit()
    
    return {"message": "Agregado a favoritos"}

@app.delete("/api/favorites/{technician_id}")
def remove_favorite(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Eliminar técnico de favoritos"""
    technician = db.query(models.User).filter(models.User.id == technician_id).first()
    
    if technician and technician in current_user.favorite_technicians:
        current_user.favorite_technicians.remove(technician)
        db.commit()
        return {"message": "Eliminado de favoritos"}
    
    raise HTTPException(status_code=400, detail="No está en favoritos")

@app.get("/api/favorites", response_model=List[schemas.UserSummary])
def get_favorites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener lista de técnicos favoritos"""
    return current_user.favorite_technicians

#DASHBOARD

@app.get("/api/dashboard/stats", response_model=schemas.DashboardResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener estadísticas para el dashboard"""
    
    # Obtener mensajes no leídos
    unread_messages = app_services.MessagingService.get_unread_messages_count(db, current_user.id)
    
    # Obtener actividad reciente (últimos 5 eventos)
    # Por ahora simulamos actividad reciente basada en servicios y solicitudes
    recent_activity = []
    
    # Servicios recientes
    services = db.query(models.Service).filter(
        or_(
            models.Service.client_id == current_user.id,
            models.Service.technician_id == current_user.id
        )
    ).order_by(models.Service.updated_at.desc()).limit(5).all()
    
    for service in services:
        activity_type = "Servicio actualizado"
        if service.status == "completed":
            activity_type = "Servicio completado"
        elif service.status == "in_progress":
            activity_type = "Servicio en progreso"
            
        other_user = service.technician if service.client_id == current_user.id else service.client
        
        recent_activity.append({
            "service": activity_type,
            "client": other_user.full_name or other_user.username,
            "time": service.updated_at.strftime("%d/%m/%Y")
        })
    
    if current_user.role == "client":
        # Estadísticas de cliente
        hired_services = db.query(models.Service).filter(
            models.Service.client_id == current_user.id
        ).count()
        
        friends_count = len(current_user.friends)
        
        # Favoritos (simulado por ahora si no hay tabla directa, o usar la relación si existe)
        favorites_count = 0 # Implementar si existe tabla de favoritos
        
        stats = schemas.ClientStats(
            contacts=friends_count, # Usamos amigos como contactos
            hired_services=hired_services,
            friends=friends_count,
            favorites=favorites_count,
            profile_views=current_user.profile_views,
            unread_messages=unread_messages
        )
    else:
        # Estadísticas de técnico
        stats = schemas.TechnicianStats(
            active_jobs=current_user.jobs_active,
            completed_jobs=current_user.jobs_completed,
            rating=current_user.rating,
            total_reviews=current_user.total_reviews,
            profile_views=current_user.profile_views,
            unread_messages=unread_messages
        )
    
    return schemas.DashboardResponse(
        user=current_user,
        stats=stats,
        recent_activity=recent_activity
    )

@app.get("/api/technicians/{technician_id}/profile", response_model=schemas.TechnicianProfileResponse)
def get_technician_profile(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener perfil completo de un técnico con reviews"""
    technician = db.query(models.User).filter(
        models.User.id == technician_id,
        models.User.role == "technician"
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    
    # Obtener reviews del técnico
    reviews = db.query(models.Review).filter(
        models.Review.technician_id == technician_id
    ).order_by(models.Review.created_at.desc()).all()
    
    # Formatear reviews con información del cliente
    formatted_reviews = []
    for review in reviews:
        client = db.query(models.User).filter(models.User.id == review.client_id).first()
        if client:
            formatted_reviews.append({
                "id": review.id,
                "service_id": review.service_id,
                "client_id": review.client_id,
                "client": {
                    "id": client.id,
                    "username": client.username,
                    "email": client.email,
                    "full_name": client.full_name,
                    "role": client.role,

                    "rating": client.rating,
                    "total_reviews": client.total_reviews
                },
                "technician_id": review.technician_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at
            })
    
    return {
        "id": technician.id,
        "username": technician.username,
        "email": technician.email,
        "full_name": technician.full_name,
        "role": technician.role,
        "location": technician.location,

        "bio": technician.bio,
        "specialties": technician.specialties,

        "rating": technician.rating,
        "total_reviews": technician.total_reviews,
        "jobs_completed": technician.jobs_completed,
        "jobs_active": technician.jobs_active,
        "is_active": technician.is_active,
        "is_verified": technician.is_verified,
        "created_at": technician.created_at,
        "reviews": formatted_reviews
    }
    
# ==================== MESSAGING ENDPOINTS ====================

@app.get("/api/conversations", response_model=List[schemas.ConversationSummary])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener todas las conversaciones del usuario"""
    conversations = app_services.MessagingService.get_user_conversations(db, current_user.id)
    return conversations


@app.post("/api/conversations/{technician_id}")
def create_or_get_conversation(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Crear o obtener conversación con un técnico"""
    # Verificar que el técnico existe
    technician = db.query(models.User).filter(
        models.User.id == technician_id,
        models.User.role == "technician"
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    
    conversation = app_services.MessagingService.get_or_create_conversation(
        db, current_user.id, technician_id
    )
    
    return {"conversation_id": conversation.id}


@app.get("/api/conversations/{conversation_id}/messages", response_model=schemas.ConversationDetail)
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener mensajes de una conversación"""
    data = app_services.MessagingService.get_conversation_messages(
        db, conversation_id, current_user.id
    )
    
    if not data:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conversation = data["conversation"]
    messages = data["messages"]
    
    return {
        "id": conversation.id,
        "client_id": conversation.client_id,
        "technician_id": conversation.technician_id,
        "client": conversation.client,
        "technician": conversation.technician,
        "messages": messages,
        "is_active": conversation.is_active,
        "created_at": conversation.created_at
    }


@app.post("/api/conversations/{conversation_id}/messages", response_model=schemas.MessageResponse)
def send_message(
    conversation_id: int,
    message_data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Enviar un mensaje en una conversación"""
    message = app_services.MessagingService.send_message(
        db, conversation_id, current_user.id, message_data.content
    )
    
    if not message:
        raise HTTPException(status_code=400, detail="No se pudo enviar el mensaje")
    
    return message


@app.post("/api/conversations/{conversation_id}/read")
def mark_conversation_as_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Marcar conversación como leída"""
    success = app_services.MessagingService.mark_as_read(db, conversation_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    return {"message": "Conversación marcada como leída"}

#SERVICE REQUEST ENDPOINTS 

@app.post("/api/services/request", response_model=schemas.ServiceResponse)
def create_service_request(
    service_data: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Crear una solicitud de servicio"""
    service = app_services.ServiceRequestService.create_service_request(
        db, current_user.id, service_data
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    
    return service


@app.get("/api/services/my-services", response_model=List[schemas.ServiceResponse])
def get_my_services(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener mis servicios (como cliente o técnico)"""
    services = app_services.ServiceRequestService.get_user_services(
        db, current_user.id, current_user.role
    )
    return services


@app.get("/api/services/pending", response_model=List[schemas.ServiceResponse])
def get_pending_service_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener solicitudes pendientes (para técnicos)"""
    if current_user.role != "technician":
        raise HTTPException(status_code=403, detail="Solo técnicos pueden ver solicitudes pendientes")
    
    services = app_services.ServiceRequestService.get_pending_requests(
        db, current_user.id
    )
    return services


@app.post("/api/services/{service_id}/accept")
def accept_service_request(
    service_id: int,
    data: schemas.ServiceAccept,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Aceptar solicitud de servicio (técnico)"""
    service = app_services.ServiceRequestService.update_service_status(
        db, service_id, current_user.id, "accepted", data.price
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    return {"message": "Servicio aceptado", "service": service}


@app.post("/api/services/{service_id}/reject")
def reject_service_request(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Rechazar solicitud de servicio (técnico)"""
    service = app_services.ServiceRequestService.update_service_status(
        db, service_id, current_user.id, "rejected"
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    return {"message": "Servicio rechazado"}


@app.post("/api/services/{service_id}/start")
def start_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Iniciar servicio (técnico)"""
    service = app_services.ServiceRequestService.update_service_status(
        db, service_id, current_user.id, "in_progress"
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    return {"message": "Servicio iniciado"}


@app.post("/api/services/{service_id}/complete")
def complete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Completar servicio (técnico)"""
    service = app_services.ServiceRequestService.update_service_status(
        db, service_id, current_user.id, "completed"
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    return {"message": "Servicio completado"}


@app.post("/api/services/{service_id}/cancel")
def cancel_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Cancelar servicio"""
    service = app_services.ServiceRequestService.update_service_status(
        db, service_id, current_user.id, "cancelled"
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    return {"message": "Servicio cancelado"}

@app.get("/api/dashboard/stats", response_model=schemas.DashboardResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener estadísticas para el dashboard"""
    
    # Obtener mensajes no leídos
    unread_messages = app_services.MessagingService.get_unread_messages_count(db, current_user.id)
    
    # Obtener actividad reciente (últimos 5 eventos)
    # Por ahora simulamos actividad reciente basada en servicios y solicitudes
    recent_activity = []
    
    # Servicios recientes
    services = db.query(models.Service).filter(
        or_(
            models.Service.client_id == current_user.id,
            models.Service.technician_id == current_user.id
        )
    ).order_by(models.Service.updated_at.desc()).limit(5).all()
    
    for service in services:
        activity_type = "Servicio actualizado"
        if service.status == "completed":
            activity_type = "Servicio completado"
        elif service.status == "in_progress":
            activity_type = "Servicio en progreso"
            
        other_user = service.technician if service.client_id == current_user.id else service.client
        
        recent_activity.append({
            "service": activity_type,
            "client": other_user.full_name or other_user.username,
            "time": service.updated_at.strftime("%d/%m/%Y")
        })
    
    if current_user.role == "client":
        # Estadísticas de cliente
        hired_services = db.query(models.Service).filter(
            models.Service.client_id == current_user.id
        ).count()
        
        friends_count = len(current_user.friends)
        
        # Favoritos (simulado por ahora si no hay tabla directa, o usar la relación si existe)
        favorites_count = 0 # Implementar si existe tabla de favoritos
        
        stats = schemas.ClientStats(
            contacts=friends_count, # Usamos amigos como contactos
            hired_services=hired_services,
            friends=friends_count,
            favorites=favorites_count,
            profile_views=current_user.profile_views,
            unread_messages=unread_messages
        )
    else:
        # Estadísticas de técnico
        stats = schemas.TechnicianStats(
            active_jobs=current_user.jobs_active,
            completed_jobs=current_user.jobs_completed,
            rating=current_user.rating,
            total_reviews=current_user.total_reviews,
            profile_views=current_user.profile_views,
            unread_messages=unread_messages
        )
    
    return schemas.DashboardResponse(
        user=current_user,
        stats=stats,
        recent_activity=recent_activity
    )

# ==================== GEMINI AI ENDPOINTS ====================

@app.post("/api/ai/message-suggestions")
def get_message_suggestions(
    context: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener sugerencias de mensajes generadas por IA"""
    suggestions = gemini_service.generate_message_suggestions(context)
    return {"suggestions": suggestions}


@app.post("/api/ai/smart-reply")
def get_smart_reply(
    last_message: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Generar respuesta inteligente al último mensaje"""
    reply = gemini_service.generate_smart_reply(last_message, current_user.role)
    return {"reply": reply}


@app.post("/api/ai/improve-description")
def improve_service_description(
    category: str,
    description: str,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Mejorar descripción de servicio con IA"""
    improved = gemini_service.generate_service_description(category, description)
    return {"improved_description": improved}

@app.get("/api/ai/reviews-summary/{technician_id}")
def get_reviews_summary(
    technician_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener resumen de opiniones de un técnico con IA"""
    technician = db.query(models.User).filter(models.User.id == technician_id).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
        
    reviews = db.query(models.Review).filter(models.Review.technician_id == technician_id).all()
    review_texts = [r.comment for r in reviews if r.comment]
    
    summary = gemini_service.summarize_reviews(review_texts)
    return {"summary": summary}

@app.post("/api/ai/estimate-price")
def estimate_service_price(
    category: str = Body(...),
    description: str = Body(...),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Estimar rango de precios con IA"""
    estimation = gemini_service.estimate_price_range(category, description)
    return {"estimation": estimation}
    
@app.get("/")
def root():
    return {"message": "API Kaimo", "version": "4.0.0"}