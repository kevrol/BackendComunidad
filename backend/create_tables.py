import sys
from pathlib import Path

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base
from app.models import User, Service, Review, Recommendation, FriendRequest

def create_tables():
    """Crear todas las tablas en la base de datos"""
    try:
        print("Eliminando tablas existentes...")
        Base.metadata.drop_all(bind=engine)
        
        print("Creando tablas en la base de datos...")
        Base.metadata.create_all(bind=engine)
        print("Tablas creadas exitosamente!")
        
        # Verificar que se crearon las tablas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTablas existentes: {tables}")
        
        # Mostrar columnas de cada tabla
        for table in tables:
            columns = inspector.get_columns(table)
            print(f"\nColumnas en la tabla '{table}':")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        
    except Exception as e:
        print(f"Error al crear tablas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_tables()