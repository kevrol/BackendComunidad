from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Tuple
from . import models, schemas
from collections import defaultdict, deque

class FriendshipService:
    """Servicio para gestionar amistades y red de confianza"""
    
    @staticmethod
    def send_friend_request(db: Session, sender_id: int, receiver_email: str):
        """Enviar solicitud de amistad"""
        receiver = db.query(models.User).filter(models.User.email == receiver_email).first()
        if not receiver:
            return None
        
        # Verificar si ya son amigos
        if FriendshipService.are_friends(db, sender_id, receiver.id):
            return None
        
        # Verificar si ya existe una solicitud pendiente
        existing = db.query(models.FriendRequest).filter(
            and_(
                models.FriendRequest.sender_id == sender_id,
                models.FriendRequest.receiver_id == receiver.id,
                models.FriendRequest.status == "pending"
            )
        ).first()
        
        if existing:
            return existing
        
        friend_request = models.FriendRequest(
            sender_id=sender_id,
            receiver_id=receiver.id
        )
        db.add(friend_request)
        db.commit()
        db.refresh(friend_request)
        return friend_request
    
    @staticmethod
    def accept_friend_request(db: Session, request_id: int, receiver_id: int):
        """Aceptar solicitud de amistad"""
        # Buscar la solicitud
        friend_request = db.query(models.FriendRequest).filter(
            models.FriendRequest.id == request_id,
            models.FriendRequest.receiver_id == receiver_id,
            models.FriendRequest.status == "pending"
        ).first()
        
        if not friend_request:
            return False
        
        # Actualizar el estado de la solicitud
        friend_request.status = "accepted"
        
        # Verificar si ya existe para evitar duplicados
        existing_friendship = db.query(models.friendship).filter(
            or_(
                and_(
                    models.friendship.c.user_id == friend_request.sender_id,
                    models.friendship.c.friend_id == friend_request.receiver_id
                ),
                and_(
                    models.friendship.c.user_id == friend_request.receiver_id,
                    models.friendship.c.friend_id == friend_request.sender_id
                )
            )
        ).first()
        
        if not existing_friendship:
            # Insertar en la tabla friendship
            stmt = models.friendship.insert().values(
                user_id=friend_request.sender_id,
                friend_id=friend_request.receiver_id,
                status="accepted"
            )
            db.execute(stmt)
        else:
            # Si ya existe, actualizar su estado a accepted
            stmt = (
                models.friendship.update()
                .where(models.friendship.c.id == existing_friendship.id)
                .values(status="accepted")
            )
            db.execute(stmt)
        
        db.commit()
        
        return True
    
    @staticmethod
    def are_friends(db: Session, user_id: int, friend_id: int):
        """Verificar si dos usuarios son amigos"""
        friendship = db.query(models.friendship).filter(
            or_(
                and_(
                    models.friendship.c.user_id == user_id,
                    models.friendship.c.friend_id == friend_id,
                    models.friendship.c.status == "accepted"
                ),
                and_(
                    models.friendship.c.user_id == friend_id,
                    models.friendship.c.friend_id == user_id,
                    models.friendship.c.status == "accepted"
                )
            )
        ).first()
        
        return friendship is not None
    
    @staticmethod
    def get_friends(db: Session, user_id: int):
        """Obtener lista de amigos aceptados"""
        # Buscar en la tabla friendship
        friendships = db.query(models.friendship).filter(
            or_(
                models.friendship.c.user_id == user_id,
                models.friendship.c.friend_id == user_id
            ),
            models.friendship.c.status == "accepted"
        ).all()
        
        friends = []
        for friendship in friendships:
            # Determinar quién es el amigo (el que no es el usuario actual)
            friend_id = friendship.friend_id if friendship.user_id == user_id else friendship.user_id
            
            # Obtener datos del amigo
            friend = db.query(models.User).filter(models.User.id == friend_id).first()
            
            if friend:
                friends.append(friend)
        
        return friends
    
    @staticmethod
    def get_network_graph(db: Session, user_id: int, max_depth: int = 2):
        """Obtener grafo de red de confianza usando BFS"""
        nodes = []
        connections = []
        visited = set()
        queue = deque([(user_id, 0)])  # (user_id, depth)
        
        while queue:
            current_id, depth = queue.popleft()
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            user = db.query(models.User).filter(models.User.id == current_id).first()
            if not user:
                continue
            
            # Agregar nodo
            nodes.append(schemas.NetworkNode(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                is_friend=depth == 1,
                is_technician=user.role == "technician",
                distance=depth
            ))
            
            # Agregar conexiones de amistad
            for friend in user.friends:
                if friend.id not in visited or depth + 1 <= max_depth:
                    connections.append(schemas.NetworkConnection(
                        source=current_id,
                        target=friend.id,
                        type="friendship"
                    ))
                    queue.append((friend.id, depth + 1))
        
        return schemas.TrustNetworkResponse(
            nodes=nodes,
            connections=connections,
            center_user_id=user_id
        )


class RecommendationService:
    """Servicio para generar recomendaciones basadas en la red de confianza"""
    
    @staticmethod
    def get_recommended_technicians(db: Session, user_id: int, category: str = None) -> List[schemas.RecommendationResponse]:
        """Obtener técnicos recomendados basados en la red de confianza"""
        recommendations = []
        
        # Obtener amigos
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return []
        
        friend_ids = [friend.id for friend in user.friends]
        
        # Obtener servicios completados por amigos con buenas calificaciones
        services_query = db.query(models.Service).filter(
            and_(
                models.Service.client_id.in_(friend_ids),
                models.Service.status == "completed"
            )
        )
        
        if category:
            services_query = services_query.filter(models.Service.category == category)
        
        services = services_query.all()
        
        # Agrupar por técnico y calcular score
        technician_scores = defaultdict(lambda: {"reviews": [], "friends": set()})
        
        for service in services:
            # Iterar sobre las reviews del servicio (aunque usualmente es una)
            for review in service.reviews:
                if review.rating >= 4.0:
                    tech_id = service.technician_id
                    technician_scores[tech_id]["reviews"].append(review.rating)
                    technician_scores[tech_id]["friends"].add(service.client_id)
        
        # Crear recomendaciones
        for tech_id, data in technician_scores.items():
            technician = db.query(models.User).filter(models.User.id == tech_id).first()
            if not technician:
                continue
            
            avg_rating = sum(data["reviews"]) / len(data["reviews"])
            num_friends = len(data["friends"])
            score = avg_rating * (1 + num_friends * 0.1)  # Más amigos = mayor score
            
            # Crear mensaje de razón
            friend_names = []
            for friend_id in list(data["friends"])[:3]:
                friend = db.query(models.User).filter(models.User.id == friend_id).first()
                if friend:
                    friend_names.append(friend.full_name or friend.username)
            
            if len(friend_names) == 1:
                reason = f"Tu amigo {friend_names[0]} lo contrató y lo calificó con {avg_rating:.1f} estrellas"
            else:
                reason = f"{num_friends} de tus amigos lo contrataron y lo calificaron con {avg_rating:.1f} estrellas en promedio"
            
            recommendations.append(schemas.RecommendationResponse(
                technician=schemas.UserSummary(
                    id=technician.id,
                    email=technician.email,
                    username=technician.username,
                    full_name=technician.full_name,
                    role=technician.role,

                    rating=technician.rating,
                    total_reviews=technician.total_reviews
                ),
                score=score,
                reason=reason,
                common_friends=num_friends
            ))
        
        # Ordenar por score descendente
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations


class ReviewService:
    """Servicio para gestionar reviews"""
    
    @staticmethod
    def create_review(db: Session, review_data: schemas.ReviewCreate, client_id: int):
        """Crear una review y actualizar estadísticas del técnico"""
        # Verificar que el servicio existe y pertenece al cliente
        service = db.query(models.Service).filter(
            and_(
                models.Service.id == review_data.service_id,
                models.Service.client_id == client_id,
                models.Service.status == "completed"
            )
        ).first()
        
        if not service:
            return None
        
        # Verificar que no exista ya una review
        existing_review = db.query(models.Review).filter(
            models.Review.service_id == review_data.service_id
        ).first()
        
        if existing_review:
            return None
        
        # Crear review
        review = models.Review(
            service_id=review_data.service_id,
            client_id=client_id,
            technician_id=service.technician_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        
        db.add(review)
        
        # Actualizar estadísticas del técnico
        technician = service.technician
        total_reviews = technician.total_reviews + 1
        new_rating = ((technician.rating * technician.total_reviews) + review_data.rating) / total_reviews
        
        technician.rating = round(new_rating, 2)
        technician.total_reviews = total_reviews
        
        db.commit()
        db.refresh(review)
        
        return review

class MessagingService:
    """Servicio para gestionar conversaciones y mensajes"""
    
    @staticmethod
    def get_or_create_conversation(db: Session, client_id: int, technician_id: int):
        """Obtener o crear una conversación entre cliente y técnico"""
        # Verificar que el técnico existe
        technician = db.query(models.User).filter(
            models.User.id == technician_id,
            models.User.role == "technician"
        ).first()
        
        if not technician:
            # Si no es técnico, verificar si es cliente (para casos de prueba o flexibilidad)
            # Pero idealmente solo se crean con técnicos
            pass

        # Buscar conversación existente
        conversation = db.query(models.Conversation).filter(
            or_(
                and_(
                    models.Conversation.client_id == client_id,
                    models.Conversation.technician_id == technician_id
                ),
                and_(
                    models.Conversation.client_id == technician_id,
                    models.Conversation.technician_id == client_id
                )
            )
        ).first()
        
        if conversation:
            return conversation
        
        # Crear nueva conversación
        conversation = models.Conversation(
            client_id=client_id,
            technician_id=technician_id
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def send_message(db: Session, conversation_id: int, sender_id: int, content: str, is_ai_generated: bool = False):
        """Enviar un mensaje en una conversación"""
        # Verificar que la conversación existe
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        # Verificar que el sender es parte de la conversación
        if sender_id not in [conversation.client_id, conversation.technician_id]:
            return None
        
        # Crear mensaje
        message = models.Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            is_ai_generated=is_ai_generated
        )
        
        db.add(message)
        
        # Actualizar conversación
        conversation.last_message = content[:100]  # Primeros 100 caracteres
        conversation.last_message_at = func.now()
        
        # Incrementar contador de no leídos
        if sender_id == conversation.client_id:
            conversation.unread_technician += 1
        else:
            conversation.unread_client += 1
        
        db.commit()
        db.refresh(message)
        
        return message
    
    @staticmethod
    def get_user_conversations(db: Session, user_id: int):
        """Obtener todas las conversaciones de un usuario"""
        conversations = db.query(models.Conversation).filter(
            or_(
                models.Conversation.client_id == user_id,
                models.Conversation.technician_id == user_id
            ),
            models.Conversation.is_active == True
        ).order_by(models.Conversation.last_message_at.desc()).all()
        
        result = []
        for conv in conversations:
            # Determinar el otro usuario
            other_user_id = conv.technician_id if conv.client_id == user_id else conv.client_id
            other_user = db.query(models.User).filter(models.User.id == other_user_id).first()
            
            # Determinar mensajes no leídos
            unread_count = conv.unread_client if user_id == conv.client_id else conv.unread_technician
            
            result.append({
                "id": conv.id,
                "client_id": conv.client_id,
                "technician_id": conv.technician_id,
                "last_message": conv.last_message,
                "last_message_at": conv.last_message_at,
                "unread_count": unread_count,
                "other_user": other_user,
                "is_active": conv.is_active,
                "created_at": conv.created_at
            })
        
        return result
    
    @staticmethod
    def get_conversation_messages(db: Session, conversation_id: int, user_id: int):
        """Obtener todos los mensajes de una conversación"""
        # Verificar que el usuario es parte de la conversación
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id,
            or_(
                models.Conversation.client_id == user_id,
                models.Conversation.technician_id == user_id
            )
        ).first()
        
        if not conversation:
            return None
        
        # Obtener mensajes
        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conversation_id
        ).order_by(models.Message.created_at.asc()).all()
        
        # Marcar mensajes como leídos
        for message in messages:
            if message.sender_id != user_id and not message.is_read:
                message.is_read = True
        
        # Resetear contador de no leídos
        if user_id == conversation.client_id:
            conversation.unread_client = 0
        else:
            conversation.unread_technician = 0
        
        db.commit()
        
        return {
            "conversation": conversation,
            "messages": messages
        }
    
    @staticmethod
    def mark_as_read(db: Session, conversation_id: int, user_id: int):
        """Marcar todos los mensajes de una conversación como leídos"""
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        # Marcar mensajes como leídos
        db.query(models.Message).filter(
            models.Message.conversation_id == conversation_id,
            models.Message.sender_id != user_id,
            models.Message.is_read == False
        ).update({"is_read": True})
        
        # Resetear contador
        if user_id == conversation.client_id:
            conversation.unread_client = 0
        else:
            conversation.unread_technician = 0
        
        db.commit()
        
        return True
    
    @staticmethod
    def get_unread_messages_count(db: Session, user_id: int) -> int:
        """Obtener total de mensajes no leídos"""
        conversations = db.query(models.Conversation).filter(
            or_(
                models.Conversation.client_id == user_id,
                models.Conversation.technician_id == user_id
            ),
            models.Conversation.is_active == True
        ).all()
        
        total_unread = 0
        for conv in conversations:
            if user_id == conv.client_id:
                total_unread += conv.unread_client
            else:
                total_unread += conv.unread_technician
        
        return total_unread
    
class ServiceRequestService:
    """Servicio para gestionar solicitudes de servicio"""
    
    @staticmethod
    def create_service_request(db: Session, client_id: int, service_data: schemas.ServiceCreate):
        """Crear una solicitud de servicio"""
        try:
            # Verificar que el técnico existe
            technician = db.query(models.User).filter(
                models.User.id == service_data.technician_id,
                models.User.role == "technician"
            ).first()
            
            if not technician:
                print(f"Técnico no encontrado con ID: {service_data.technician_id}")
                return None
            
            # Crear solicitud
            service = models.Service(
                client_id=client_id,
                technician_id=service_data.technician_id,
                title="Servicio acordado por chat",
                category=service_data.category,
                description=service_data.description,
                scheduled_date=service_data.scheduled_date,
                address=service_data.address,
                status="pending"
            )
            
            db.add(service)
            db.commit()
            db.refresh(service)
            
            print(f"Servicio creado exitosamente: ID {service.id}")
            return service
            
        except Exception as e:
            print(f"Error en create_service_request: {e}")
            db.rollback()
            raise e

    @staticmethod
    def get_user_services(db: Session, user_id: int, role: str):
        """Obtener servicios del usuario"""
        if role == "client":
            return db.query(models.Service).filter(
                models.Service.client_id == user_id
            ).order_by(models.Service.created_at.desc()).all()
        else:
            return db.query(models.Service).filter(
                models.Service.technician_id == user_id
            ).order_by(models.Service.created_at.desc()).all()

    @staticmethod
    def get_pending_requests(db: Session, technician_id: int):
        """Obtener solicitudes pendientes para un técnico"""
        return db.query(models.Service).filter(
            models.Service.technician_id == technician_id,
            models.Service.status == "pending"
        ).order_by(models.Service.created_at.desc()).all()

    @staticmethod
    def update_service_status(db: Session, service_id: int, user_id: int, status: str, price: float = None):
        """Actualizar estado del servicio"""
        service = db.query(models.Service).filter(
            models.Service.id == service_id
        ).first()
        
        if not service:
            return None
            
        # Verificar permisos (el usuario debe ser parte del servicio)
        if service.client_id != user_id and service.technician_id != user_id:
            return None
            
        service.status = status
        service.updated_at = func.now()
        
        if status == "accepted" and price is not None:
            service.price = price
            
        if status == "completed":
            service.completed_at = func.now()
            
        db.commit()
        db.refresh(service)
        return service