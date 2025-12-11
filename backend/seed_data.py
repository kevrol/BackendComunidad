import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import User, Service, Review, FriendRequest
from app.auth import get_password_hash
from datetime import datetime, timedelta
import random

def seed_database():
    """Poblar base de datos con datos de prueba"""
    db = SessionLocal()
    
    try:
        print("🌱 Poblando base de datos con datos de prueba...")
        
        # Limpiar datos existentes
        db.query(Review).delete()
        db.query(Service).delete()
        db.query(FriendRequest).delete()
        db.query(User).delete()
        db.commit()
        
        # Crear usuarios de prueba
        users_data = [
            # Clientes
            {
                "email": "kevin@test.com",
                "username": "kevin_ruiz",
                "full_name": "Kevin Ruiz",
                "role": "client",
                "location": "Los Mochis, Sinaloa",
                "is_verified": True
            },
            {
                "email": "maria@test.com",
                "username": "maria_lopez",
                "full_name": "María López",
                "role": "client",
                "location": "Los Mochis, Sinaloa",
                "is_verified": True
            },
            {
                "email": "juan@test.com",
                "username": "juan_perez",
                "full_name": "Juan Pérez",
                "role": "client",
                "location": "Los Mochis, Sinaloa",
                "is_verified": True
            },
            # Técnicos
            {
                "email": "carlos@tech.com",
                "username": "carlos_electricista",
                "full_name": "Carlos Pérez",
                "role": "technician",
                "location": "Los Mochis, Sinaloa",
                "bio": "Electricista con 5 años de experiencia en el rubro, especializado en instalaciones residenciales y comerciales.",
                "specialties": '["Eléctrico", "Plomero"]',
                "rating": 4.8,
                "total_reviews": 342,
                "jobs_completed": 280,
                "is_verified": True
            },
            {
                "email": "ana@tech.com",
                "username": "ana_plomera",
                "full_name": "Ana González",
                "role": "technician",
                "location": "Los Mochis, Sinaloa",
                "bio": "Plomera certificada con amplia experiencia en reparaciones de emergencia.",
                "specialties": '["Plomero", "Construcción"]',
                "rating": 4.6,
                "total_reviews": 587,
                "jobs_completed": 450,
                "is_verified": True
            },
            {
                "email": "luis@tech.com",
                "username": "luis_carpintero",
                "full_name": "Luis Martínez",
                "role": "technician",
                "location": "Los Mochis, Sinaloa",
                "bio": "Carpintero especializado en muebles a medida y reparaciones del hogar.",
                "specialties": '["Carpintería", "Hogar"]',
                "rating": 4.9,
                "total_reviews": 156,
                "jobs_completed": 120,
                "is_verified": True
            },
            {
                "email": "roberto@tech.com",
                "username": "roberto_mecanico",
                "full_name": "Roberto Sianuqui",
                "role": "technician",
                "location": "Los Mochis, Sinaloa",
                "bio": "Mecánico automotriz con certificaciones internacionales.",
                "specialties": '["Automotriz", "Mecánica"]',
                "rating": 4.3,
                "total_reviews": 1205,
                "jobs_completed": 890,
                "is_verified": True
            },
            {
                "email": "pedro@tech.com",
                "username": "pedro_constructor",
                "full_name": "Pedro Ramírez",
                "role": "technician",
                "location": "Los Mochis, Sinaloa",
                "bio": "Constructor con 10 años de experiencia en obras residenciales.",
                "specialties": '["Construcción", "Albañilería"]',
                "rating": 4.7,
                "total_reviews": 234,
                "jobs_completed": 180,
                "is_verified": True
            }
        ]
        
        users = []
        for user_data in users_data:
            user = User(
                **user_data,
                hashed_password=get_password_hash("123456"),
                is_active=True
            )
            db.add(user)
            users.append(user)
        
        db.commit()
        print(f"✅ Creados {len(users)} usuarios")
        
        # Crear amistades (red de confianza)
        # Kevin es amigo de María y Juan
        users[0].friends.append(users[1])  # Kevin -> María
        users[0].friends.append(users[2])  # Kevin -> Juan
        
        # María es amiga de Juan
        users[1].friends.append(users[2])  # María -> Juan
        
        db.commit()
        print("✅ Relaciones de amistad creadas")
        
        # Crear servicios
        categories = ["Hogar", "Electrónicos", "Automotriz", "Construcción"]
        services_data = [
            {
                "title": "Instalación eléctrica residencial",
                "description": "Instalación completa de sistema eléctrico para casas y departamentos",
                "category": "Hogar",
                "price": 2500.0,
                "technician": users[3],  # Carlos
                "location": "Los Mochis, Sinaloa"
            },
            {
                "title": "Reparación de plomería",
                "description": "Reparación de fugas, instalación de tuberías y mantenimiento",
                "category": "Hogar",
                "price": 800.0,
                "technician": users[4],  # Ana
                "location": "Los Mochis, Sinaloa"
            },
            {
                "title": "Muebles a medida",
                "description": "Diseño y fabricación de muebles personalizados",
                "category": "Hogar",
                "price": 5000.0,
                "technician": users[5],  # Luis
                "location": "Los Mochis, Sinaloa"
            },
            {
                "title": "Mantenimiento automotriz",
                "description": "Cambio de aceite, revisión general y reparaciones mecánicas",
                "category": "Automotriz",
                "price": 1200.0,
                "technician": users[6],  # Roberto
                "location": "Los Mochis, Sinaloa"
            },
            {
                "title": "Remodelación de baños",
                "description": "Remodelación completa de baños con materiales de calidad",
                "category": "Construcción",
                "price": 15000.0,
                "technician": users[7],  # Pedro
                "location": "Los Mochis, Sinaloa"
            }
        ]
        
        services = []
        for service_data in services_data:
            service = Service(
                title=service_data["title"],
                description=service_data["description"],
                category=service_data["category"],
                price=service_data["price"],
                technician_id=service_data["technician"].id,
                location=service_data["location"],
                status="available"
            )
            db.add(service)
            services.append(service)
        
        db.commit()
        print(f"✅ Creados {len(services)} servicios")
        
        # Crear algunos servicios completados y reviews
        # María contrató a Carlos (electricista) - buena calificación
        completed_service1 = Service(
            title="Instalación de contactos adicionales",
            description="Instalación de 5 contactos en sala y cocina",
            category="Hogar",
            price=600.0,
            technician_id=users[3].id,  # Carlos
            client_id=users[1].id,  # María
            location="Los Mochis, Sinaloa",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=10)
        )
        db.add(completed_service1)
        db.commit()
        
        review1 = Review(
            service_id=completed_service1.id,
            client_id=users[1].id,
            technician_id=users[3].id,
            rating=5.0,
            comment="Excelente servicio, muy profesional y puntual. Lo recomiendo ampliamente."
        )
        db.add(review1)
        
        # Juan contrató a Ana (plomera) - buena calificación
        completed_service2 = Service(
            title="Reparación de fuga en baño",
            description="Reparación de fuga bajo el lavabo",
            category="Hogar",
            price=400.0,
            technician_id=users[4].id,  # Ana
            client_id=users[2].id,  # Juan
            location="Los Mochis, Sinaloa",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=5)
        )
        db.add(completed_service2)
        db.commit()
        
        review2 = Review(
            service_id=completed_service2.id,
            client_id=users[2].id,
            technician_id=users[4].id,
            rating=4.5,
            comment="Muy buen trabajo, resolvió el problema rápidamente."
        )
        db.add(review2)
        
        # María contrató a Luis (carpintero) - excelente calificación
        completed_service3 = Service(
            title="Closet a medida",
            description="Fabricación e instalación de closet empotrado",
            category="Hogar",
            price=7000.0,
            technician_id=users[5].id,  # Luis
            client_id=users[1].id,  # María
            location="Los Mochis, Sinaloa",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=15)
        )
        db.add(completed_service3)
        db.commit()
        
        review3 = Review(
            service_id=completed_service3.id,
            client_id=users[1].id,
            technician_id=users[5].id,
            rating=5.0,
            comment="¡Trabajo impecable! Quedó mejor de lo que imaginaba. 100% recomendado."
        )
        db.add(review3)
        
        db.commit()
        print("✅ Servicios completados y reviews creadas")
        
        print("\n✅ ¡Base de datos poblada exitosamente!")
        print("\n📝 Usuarios de prueba:")
        print("  Cliente: kevin@test.com / 123456")
        print("  Cliente: maria@test.com / 123456")
        print("  Cliente: juan@test.com / 123456")
        print("  Técnico: carlos@tech.com / 123456")
        print("  Técnico: ana@tech.com / 123456")
        print("  Técnico: luis@tech.com / 123456")
        print("  Técnico: roberto@tech.com / 123456")
        print("  Técnico: pedro@tech.com / 123456")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()