"""Contenido curado del KB de TasAR (KSP v1.2, WO F5-01).

Separado de `knowledge_base.py` para que el router quede chico y legible:
esto es texto de marketing (business/offerings/pricing/faq/screens/brand),
no logica. Describe a **TasAR el producto SaaS** (no a un tenant/inmobiliaria
puntual). Lo unico que sale EN VIVO de la base (entities.sample) vive en
`knowledge_base.py`, no aca.

`_TOOLS` reusa 1:1 el JSON Schema (`parameters`) de las tools reales de
`services/bot_tools.py` para que el contrato publicado nunca se desincronice
del que usa Gemini internamente.
"""
from __future__ import annotations

from typing import Any, Dict, List

from services.bot_tools import TOOL_DECLARATIONS

_TOOL_DECL_BY_NAME = {d["name"]: d for d in TOOL_DECLARATIONS}

# Logo TasAR (variante "icon" de frontend/src/components/BrandLogo.tsx),
# portado 1:1 como SVG inline (protocolo 4.11: no hay logo.svg estatico en
# el front -- se renderiza con React -- asi que se embebe el markup en vez
# de depender de una URL que no existe). Colores = paleta light del brand
# book (heatColors del componente), no inventados.
LOGO_SVG = (
    '<svg viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="1" y="11" width="8" height="8" rx="1.8" fill="#bbf7d0"/>'
    '<rect x="11" y="11" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="21" y="11" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="31" y="11" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="41" y="11" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="51" y="11" width="8" height="8" rx="1.8" fill="#bbf7d0"/>'
    '<rect x="1" y="21" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="11" y="21" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="21" y="21" width="8" height="8" rx="1.8" fill="#10b981"/>'
    '<rect x="31" y="21" width="8" height="8" rx="1.8" fill="#10b981"/>'
    '<rect x="41" y="21" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="51" y="21" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="1" y="31" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="11" y="31" width="8" height="8" rx="1.8" fill="#22c55e"/>'
    '<rect x="21" y="31" width="8" height="8" rx="1.8" fill="#065f46"/>'
    '<rect x="31" y="31" width="8" height="8" rx="1.8" fill="#065f46"/>'
    '<rect x="41" y="31" width="8" height="8" rx="1.8" fill="#22c55e"/>'
    '<rect x="51" y="31" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="1" y="41" width="8" height="8" rx="1.8" fill="#bbf7d0"/>'
    '<rect x="11" y="41" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="21" y="41" width="8" height="8" rx="1.8" fill="#22c55e"/>'
    '<rect x="31" y="41" width="8" height="8" rx="1.8" fill="#22c55e"/>'
    '<rect x="41" y="41" width="8" height="8" rx="1.8" fill="#86efac"/>'
    '<rect x="51" y="41" width="8" height="8" rx="1.8" fill="#bbf7d0"/>'
    "</svg>"
)

BUSINESS: Dict[str, Any] = {
    "name": "TasAR",
    "tagline": "El mapa de valor inmobiliario: tasaciones ancladas a mercado real, CRM y bot de WhatsApp con IA, todo en una sola suite.",
    "description": (
        "TasAR es la suite que usan inmobiliarias y tasadores para vender con datos: "
        "tasaciones ACM ancladas a comparables reales de mercado, un CRM de visitas y "
        "negocios, y un bot de WhatsApp con IA que atiende, busca propiedades, agenda "
        "visitas y hace tasaciones express sin intervencion humana. Todo aislado por "
        "workspace (multi-tenant real, cada inmobiliaria ve solo lo suyo)."
    ),
    "value_story": (
        "TasAR conecta la captacion con el cierre: el bot de WhatsApp atiende 24/7, "
        "busca el stock real y da una tasacion express anclada a mercado para enganchar "
        "al propietario en segundos; el CRM convierte ese contacto en visita y negocio; "
        "el tasador cierra con un informe ACM formal y firmable. Una sola suite, un solo "
        "dato de verdad por workspace."
    ),
    "industry": "Proptech / software para inmobiliarias y tasadores (Argentina)",
    "target_audience": (
        "Inmobiliarias, tasadores matriculados y equipos comerciales inmobiliarios que "
        "hoy trabajan con planillas sueltas, WhatsApp manual y tasaciones a ojo."
    ),
    "website": "https://tasar-landing.netlify.app",
}

KEY_MESSAGES: List[str] = [
    "Tasaciones ancladas a comparables reales de mercado, no un numero a ojo",
    "El bot de WhatsApp atiende, busca stock real y agenda solo, 24/7",
    "Un lead entra por el bot y sale como visita, negocio y tasacion firmada",
    "Un solo dato de verdad por workspace: bot, CRM y tasador ven la misma propiedad",
]

OFFERINGS: List[Dict[str, Any]] = [
    {
        "id": "tasacion_acm",
        "name": "Tasaciones ACM (comparables homologados)",
        "description": (
            "El tasador arma un estudio de mercado con comparables reales, ajustes "
            "ponderados por superficie/ambientes/antiguedad/estado, y genera un informe "
            "firmable en PDF. Metodologia ACM trazable, no una planilla suelta."
        ),
        "key_features": [
            "Comparables reales del catalogo de mercado, no inventados",
            "Ajustes ponderados con pesos por similitud",
            "Informe PDF firmable y colaborativo (comentarios de equipo)",
            "Pipeline de tasaciones por estado",
        ],
        "status": "available",
    },
    {
        "id": "tasacion_express",
        "name": "Tasacion express (web o WhatsApp)",
        "description": (
            "Estimacion instantanea de un RANGO de valor de mercado, anclado a "
            "comparables reales, para enganchar a un propietario en segundos — desde la "
            "web o desde el bot de WhatsApp."
        ),
        "key_features": [
            "Rango de valor (no un numero unico) anclado a la mediana real de mercado",
            "Ajuste por IA con fallback deterministico si la IA no responde",
            "Disponible en la web y en el bot de WhatsApp",
            "Cada estimacion queda persistida y es re-descargable en PDF",
        ],
        "status": "available",
    },
    {
        "id": "crm_inmobiliario",
        "name": "CRM inmobiliario (visitas, pipeline y autorizaciones)",
        "description": (
            "Cada lead entra por el bot o a mano, se agenda una visita, se sigue el "
            "negocio en un pipeline de ventas y se firman autorizaciones de venta en "
            "exclusiva — todo aislado por workspace."
        ),
        "key_features": [
            "Pipeline de ventas por etapa",
            "Agenda de visitas con resultado",
            "Autorizaciones de venta en exclusiva",
            "Ficha de cliente con preferencias e historial",
        ],
        "status": "available",
    },
    {
        "id": "bot_whatsapp_ia",
        "name": "Bot de WhatsApp con IA",
        "description": (
            "Atiende WhatsApp 24/7 con function-calling real sobre el stock del "
            "workspace: busca propiedades, agenda visitas, hace tasaciones express y "
            "deriva a un asesor humano cuando corresponde. Nunca inventa precios ni "
            "propiedades."
        ),
        "key_features": [
            "Busqueda de stock real, nunca inventa propiedades",
            "Tasacion express como gancho de captacion",
            "Derivacion a un asesor humano por round-robin",
            "Modo texto y modo voz (nota de audio) por workspace",
        ],
        "status": "available",
    },
    {
        "id": "mercado_comparables",
        "name": "Mercado y mapa de calor",
        "description": (
            "Catalogo de comparables de mercado (propio + fuentes externas) con mapa de "
            "calor de precio por m2, para anclar cualquier tasacion a datos reales de la "
            "zona."
        ),
        "key_features": [
            "Catalogo de comparables por zona, tipo y operacion",
            "Mapa de calor de precio por m2",
            "Import de datasets externos (ETL)",
        ],
        "status": "available",
    },
]

PRICING: Dict[str, Any] = {
    "model": "human_closes",
    "summary": (
        "TasAR se contrata por suscripcion mensual por equipo/inmobiliaria; el precio "
        "final y el plan lo cierra un asesor comercial segun cantidad de usuarios y "
        "modulos activados."
    ),
    "pricing_disclosed": False,
    "human_closes_price": True,
}

DIFFERENTIATORS: List[str] = [
    "Tasacion anclada a comparables reales de mercado, no un numero tirado a ojo",
    "Un solo dato de verdad por workspace: el bot, el CRM y el tasador ven la misma propiedad",
    "El bot de WhatsApp nunca inventa: si no hay dato, deriva a un humano",
    "Informe de tasacion firmable y colaborativo, no una planilla suelta",
]

OBJECTIONS: List[Dict[str, str]] = [
    {
        "objection": "Ya usamos WhatsApp Business a mano.",
        "response": (
            "TasAR no reemplaza WhatsApp: se conecta a el y le suma un bot que atiende "
            "cuando el equipo no puede, busca en el stock real y agenda solo. El equipo "
            "sigue viendo todo en la Bandeja y puede tomar el control en cualquier momento."
        ),
    },
    {
        "objection": "Ya tenemos un CRM aparte.",
        "response": (
            "TasAR integra CRM, tasacion y bot en un mismo dato por workspace. Si hoy el "
            "CRM y las tasaciones viven en sistemas separados, la ficha del cliente y la "
            "propiedad se desincronizan; acá son la misma fila."
        ),
    },
]

FAQ: List[Dict[str, str]] = [
    {
        "question": "Cuanto tarda una tasacion express?",
        "answer": "Es instantanea: se calcula al toque, anclada a los comparables reales cargados del mercado.",
    },
    {
        "question": "El bot de WhatsApp puede agendar visitas solo?",
        "answer": (
            "Si. Cuando el cliente confirma fecha y hora, el bot crea la visita y notifica "
            "al asesor asignado; queda pendiente de su confirmacion."
        ),
    },
]

CONTACT: Dict[str, Any] = {
    "website": "https://tasar-landing.netlify.app",
    "email": None,
    "demo_url": "https://tasar-app.netlify.app",
    "phone": None,
    "notes": "El contacto comercial lo gestiona un asesor humano; no hay linea publica publicada en este KB.",
}

DO_NOT_SAY: List[str] = [
    "No prometer precio de venta fijo ni de cierre: la tasacion express da un RANGO, no un numero comprometido.",
    "No inventar disponibilidad, propiedades ni fotos que no esten en el stock real del workspace.",
    "No dar el precio ni las condiciones de un plan/suscripcion: lo cierra un asesor humano (pricing_disclosed=false).",
    "No usar emojis ni superlativos vacios (revolucionario, unico, magico).",
]

# Declaracion barata (protocolo 4.12): lo que el sistema puede consultar/hacer
# EN VIVO. Espejo 1:1 de las 7 tools reales de services/bot_tools.py (el bot
# de WhatsApp ya las ejecuta en produccion); solo 3 quedan ademas publicadas
# como `tools` HTTP porque son las que tiene sentido demostrar sin una
# conversacion de WhatsApp real detras (ver `TOOLS` mas abajo).
CAPABILITIES: List[Dict[str, Any]] = [
    {
        "id": "buscar_propiedades", "kind": "read", "label": "Busqueda de propiedades",
        "description": "Busca en el stock real del workspace por zona, tipo, ambientes y presupuesto.",
        "identifica_por": ["zona", "tipo", "ambientes", "presupuesto_min_usd", "presupuesto_max_usd"],
        "devuelve": ["count", "propiedades"], "sensible": False,
    },
    {
        "id": "consultar_propiedad", "kind": "read", "label": "Detalle de una propiedad",
        "description": "Trae el detalle completo y las fotos de una propiedad del stock por su ID.",
        "identifica_por": ["propiedad_id"], "devuelve": ["titulo", "direccion", "precio_usd", "fotos"],
        "sensible": False,
    },
    {
        "id": "agendar_visita", "kind": "action", "label": "Agendar visita",
        "description": "Agenda una visita a una propiedad para un cliente, en una fecha/hora concreta.",
        "identifica_por": ["propiedad_id", "fecha_propuesta", "telefono_cliente"],
        "devuelve": ["visita_id", "fecha"], "sensible": True,
    },
    {
        "id": "registrar_lead", "kind": "action", "label": "Registrar lead",
        "description": "Registra o actualiza a un cliente como lead con su interes de busqueda.",
        "identifica_por": ["nombre", "interes", "zona", "presupuesto_max_usd"],
        "devuelve": ["cliente_id", "lead_status"], "sensible": True,
    },
    {
        "id": "tasacion_express", "kind": "read", "label": "Tasacion express anclada a mercado",
        "description": "Estima un rango de valor USD para una propiedad, anclado a comparables reales.",
        "identifica_por": ["tipo_propiedad", "superficie_m2", "ciudad", "barrio"],
        "devuelve": ["rango_usd", "confianza", "comparables"], "sensible": False,
    },
    {
        "id": "derivar_a_humano", "kind": "action", "label": "Derivar a un asesor humano",
        "description": "Deriva la conversacion a un asesor humano por round-robin del equipo.",
        "identifica_por": ["motivo"], "devuelve": ["vendor_name"], "sensible": True,
    },
    {
        "id": "cerrar_conversacion", "kind": "action", "label": "Cerrar conversacion",
        "description": "Marca una conversacion como cerrada cuando no queda nada pendiente.",
        "identifica_por": [], "devuelve": ["estado"], "sensible": False,
    },
]

SCREENS: List[Dict[str, Any]] = [
    {
        "label": "Dashboard", "kind": "dashboard", "headline": "Dashboard", "framework": "Tailwind CSS",
        "nav": ["Dashboard", "Tasador AI", "Captar", "Cartera", "Equipo", "Chat", "Mercado", "Configuracion"],
        "components": ["KPI cards con delta % vs. periodo anterior", "icono por metrica", "accesos rapidos a modulos"],
        "layout": "Header con saludo. Grid de KPI cards (leads nuevos, visitas, tasaciones firmadas), cada una con icono, valor grande y delta % en badge de color.",
        "style": "Cards con sombra suave y hover elevado; badge verde si el delta es positivo, rojo si es negativo.",
        "data": [
            {"label": "Leads nuevos", "value": 12, "delta_pct": 8},
            {"label": "Visitas agendadas", "value": 5, "delta_pct": -3},
            {"label": "Tasaciones firmadas", "value": 3, "delta_pct": 0},
        ],
        "flow": "El equipo entra y ve de un vistazo como viene la semana antes de entrar a un modulo puntual.",
        "route": "/",
    },
    {
        "label": "Tasacion express", "kind": "form", "headline": "Tasacion express", "framework": "Tailwind CSS",
        "nav": ["Tasacion express", "Tasaciones", "Estudios ACM"],
        "components": ["formulario de datos de la propiedad", "selector de estado de conservacion", "resultado en rango de valor al enviar"],
        "layout": "Formulario vertical: provincia/ciudad/barrio, superficie, ambientes, dormitorios, antiguedad, caracteristicas. Boton 'Calcular' al pie.",
        "style": "Campos con label arriba, bordes redondeados, foco en verde de marca.",
        "data": [
            {"field": "Superficie total (m2)", "placeholder": "80"},
            {"field": "Ambientes", "placeholder": "3"},
            {"field": "Antiguedad (anios)", "placeholder": "10"},
        ],
        "flow": "El asesor carga los datos de una propiedad y en segundos recibe un rango de valor anclado a mercado.",
        "route": "/tasacion-express",
    },
    {
        "label": "Mapa de calor de mercado", "kind": "map", "headline": "Mapa", "framework": "Tailwind CSS",
        "nav": ["Mercado", "Comparables", "Mapa", "Reportes"],
        "components": ["mapa con puntos de calor por precio/m2", "filtros de zona y tipo", "leyenda de rango de precio"],
        "layout": "Mapa a pantalla completa con puntos coloreados segun precio por m2; panel lateral de filtros (zona, tipo de propiedad, operacion).",
        "style": "Paleta de calor verde-a-oscuro consistente con la marca.",
        "data": [
            {"zona": "Palermo", "precio_m2_usd": 2450},
            {"zona": "Belgrano", "precio_m2_usd": 2100},
            {"zona": "Caballito", "precio_m2_usd": 1800},
        ],
        "flow": "El tasador ubica visualmente donde esta parado el precio de la zona antes de anclar una tasacion.",
        "route": "/mapa",
    },
    {
        "label": "Inbox WhatsApp", "kind": "feed", "headline": "Inbox WhatsApp", "framework": "Tailwind CSS",
        "nav": ["Bandeja", "Inbox WhatsApp", "Datos IA · Bot"],
        "components": ["lista de conversaciones con ultimo mensaje", "badge de estado (bot activo / derivada / cerrada)", "chat con historial + tomar mando"],
        "layout": "Lista de conversaciones a la izquierda (contacto, ultimo mensaje, hora); panel de chat a la derecha con historial y boton 'Tomar conversacion'.",
        "style": "Conversacion activa del bot con badge verde; derivada a humano con badge naranja.",
        "data": [
            {"contacto": "Juan Perez", "ultimo_mensaje": "Tienen algo en Palermo 2 ambientes?", "estado": "bot"},
            {"contacto": "Maria Gomez", "ultimo_mensaje": "Quiero hablar con alguien", "estado": "derivada"},
        ],
        "flow": "El asesor ve todas las conversaciones de WhatsApp (las que atiende el bot y las derivadas) y puede tomar el control en cualquier momento.",
        "route": "/whatsapp",
    },
]

BRAND: Dict[str, Any] = {
    "logo": {"primary": None, "isotype": None, "svg": LOGO_SVG},
    "colors": {"primary": "#10b981", "accent": "#34d399", "ink": "#0a1410", "surface": "#fafafa"},
    "fonts": {"display": "Inter Tight", "text": "Inter"},
    "style": {"radius": "rounded", "density": "comoda", "vibe": "proptech serio, verde-negro, sobrio"},
    "phonetic": "Tasar (se lee como el verbo tasar, agudo en la ultima silaba)",
    "tone": "profesional",
    "avoid": ["No tono informal/juvenil", "No usar colores fuera de la paleta verde-negro del brand book"],
}

# `tools` publicadas (protocolo 4.14): SOLO las 3 que tienen endpoint HTTP
# real implementado en knowledge_base.py. `parameters` reusa 1:1 el JSON
# Schema de la tool del bot para buscar_propiedades/tasacion_express;
# agendar_visita tiene schema propio porque el bot la resuelve con el
# telefono de la conversacion de WhatsApp (no aplica aca: no hay
# conversacion, lo pide explicito).
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "buscar_propiedades",
        "description": _TOOL_DECL_BY_NAME["buscar_propiedades"]["description"],
        "parameters": _TOOL_DECL_BY_NAME["buscar_propiedades"]["parameters"],
        "endpoint": {"method": "POST", "path": "/api/tools/buscar_propiedades"},
        "response_example": {
            "count": 1,
            "propiedades": [{
                "id": 101, "titulo": "Departamento 3 amb. moderno", "tipo": "departamento",
                "operacion": "venta", "barrio": "Palermo", "ciudad": "CABA",
                "ambientes": 3, "precio_usd": 220000, "moneda": "USD",
            }],
        },
    },
    {
        "name": "tasacion_express",
        "description": _TOOL_DECL_BY_NAME["tasacion_express"]["description"],
        "parameters": _TOOL_DECL_BY_NAME["tasacion_express"]["parameters"],
        "endpoint": {"method": "POST", "path": "/api/tools/tasacion_express"},
        "response_example": {
            "ok": True,
            "rango_usd": {"min": 195000, "tipico": 215000, "max": 235000},
            "confianza": "media", "comparables": 14, "alcance": "zona",
        },
    },
    {
        "name": "agendar_visita",
        "description": (
            "Agenda una visita a una propiedad para un cliente identificado por telefono. "
            "Usar cuando el prospecto acepta ver una propiedad en una fecha/hora concreta."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "propiedad_id": {"type": "integer", "description": "ID interno de la propiedad"},
                "fecha_propuesta": {"type": "string", "description": "Fecha y hora ISO 8601 (ej '2026-07-14T17:00:00-03:00')"},
                "telefono_cliente": {"type": "string", "description": "Telefono del cliente, solo numeros"},
                "nombre_cliente": {"type": "string", "description": "Nombre del cliente si se conoce"},
            },
            "required": ["propiedad_id", "fecha_propuesta", "telefono_cliente"],
        },
        "endpoint": {"method": "POST", "path": "/api/tools/agendar_visita"},
        "response_example": {"ok": True, "visita_id": 55, "cliente_id": 30, "propiedad": "Departamento 3 amb. moderno", "fecha": "2026-07-14T17:00:00-03:00"},
    },
]
