import os
import google.generativeai as genai
from typing import List, Dict, Optional
from dotenv import load_dotenv
# Cargar variables de entorno
load_dotenv()
# Configurar Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY no encontrada en .env")
class GeminiService:
    """Servicio para generar respuestas con Gemini AI"""
    
    def __init__(self):
        if GEMINI_API_KEY:
            # Usar gemini-pro o gemini-1.5-flash según disponibilidad
            self.model = genai.GenerativeModel('gemini-2.5-flash') 
            self.enabled = True
        else:
            self.model = None
            self.enabled = False
    
    def generate_review_suggestion(self, user_input: str, rating: int, service_context: str) -> str:
        """Generar una sugerencia de reseña basada en input parcial y rating"""
        if not self.enabled:
            return user_input or "Excelente servicio."
            
        prompt = f"""
        Actúa como un cliente de servicios del hogar.
        Escribe una reseña corta (máximo 2-3 frases), natural y útil.
        
        Contexto del servicio: {service_context}
        Calificación dada: {rating}/5 estrellas.
        
        Lo que el usuario escribió (borrador): "{user_input}"
        
        Instrucciones:
        - Si el borrador está vacío, genera una reseña coherente con la calificación.
        - Si hay texto, mejóralo, corrige ortografía y dale un tono más profesional pero cercano.
        - NO uses frases como "Aquí tienes una reseña". Devuelve SOLO el texto de la reseña.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generando review: {e}")
            return user_input
    def generate_message_suggestions(self, context: str, conversation_history: List[Dict] = None) -> List[str]:
        """Generar sugerencias de mensajes"""
        if not self.enabled:
            return self._get_default_suggestions()
        
        prompt = f"""Eres un asistente que ayuda a clientes a comunicarse con técnicos.
Contexto: {context}
Genera 3 sugerencias de mensajes cortos y profesionales.
Formato: Separados por "|||". 
Ejemplo: Hola, precio?|||Disponibilidad?|||Gracias
"""
        try:
            response = self.model.generate_content(prompt)
            return [s.strip() for s in response.text.split("|||")[:3]]
        except Exception as e:
            print(f"Error suggestions: {e}")
            return self._get_default_suggestions()
    
    def generate_smart_reply(self, last_message: str, user_role: str) -> str:
        """Generar respuesta inteligente"""
        if not self.enabled: return "Gracias."
        prompt = f"Responde corto y profesional a: '{last_message}'"
        try:
            return self.model.generate_content(prompt).text.strip()
        except: return "Gracias."
    def generate_service_description(self, category: str, description: str) -> str:
        """Mejorar descripción de servicio"""
        if not self.enabled: return description
        
        prompt = f"""
        Mejora esta descripción de servicio para un profesional de {category}.
        Texto original: "{description}"
        
        Objetivo: Hacerla atractiva, profesional y confiable para potenciales clientes.
        Mantén un tono cercano pero experto. Máximo 50-60 palabras.
        """
        try:
            return self.model.generate_content(prompt).text.strip()
        except: return description

    def summarize_reviews(self, reviews: List[str]) -> str:
        """Resumir opiniones"""
        if not self.enabled or not reviews: return "Sin suficientes opiniones para generar resumen."
        
        # Tomar solo las últimas 10 para no exceder tokens si hay muchas
        reviews_text = "\n- ".join(reviews[:10])
        
        prompt = f"""
        Resume las siguientes opiniones de clientes sobre un técnico:
        
        {reviews_text}
        
        Genera un párrafo corto (máximo 3 frases) destacando los puntos fuertes y áreas de mejora mencionadas.
        Tono objetivo y útil para futuros clientes.
        """
        try:
            return self.model.generate_content(prompt).text.strip()
        except: return "Resumen no disponible temporalmente."

    def estimate_price_range(self, category: str, description: str) -> str:
        """Estimar rango de precios"""
        if not self.enabled: return "Precio a convenir"
        
        prompt = f"""
        Estima un rango de precio razonable (en moneda local, asume contexto general o USD si no es claro) para este servicio:
        Categoría: {category}
        Descripción: {description}
        
        Devuelve SOLO el rango numérico estimado (ej: "$50 - $80") y una brevísima justificación (max 5 palabras).
        Si no es posible estimar, di "A convenir".
        """
        try:
            return self.model.generate_content(prompt).text.strip()
        except: return "A convenir"

    def _get_default_suggestions(self) -> List[str]:
        return ["¿Está disponible?", "¿Presupuesto?", "Gracias"]

# Instancia global
gemini_service = GeminiService()