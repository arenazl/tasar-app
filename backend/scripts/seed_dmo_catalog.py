"""Seed del CATALOGO OFICIAL de DMO (coaches + templates globales) — WO F2-01.

Siembra las 5 metodologias reconocidas como coaches oficiales (is_official=True)
y un template por metodologia en el CATALOGO GLOBAL (workspace_id = NULL). Un
workspace nuevo VE este catalogo y puede clonarlo/asignarlo a sus vendedores.

Metodologias (portadas de AgentFlow; la adaptacion local de AgentFlow fue
RENOMBRADA a "WhatsApp-first AR" por decision del rework):
  - WhatsApp-first AR   (adaptacion local: WhatsApp como canal principal)
  - Tom Ferry           (Hour of Power)
  - Mike Ferry          (prospeccion clasica)
  - Brian Buffini       (trabajo por referidos)
  - Verl Workman        (dollar productive activities)

Los NOMBRES de campos de tabla van en INGLES; los TEXTOS de cara al usuario
(nombres de bloques, descripciones, labels de metrica) van en castellano
rioplatense, que es lo que ve el vendedor.

IDEMPOTENTE: si el coach ya existe (por name), lo saltea. NO crea templates
duplicados si el coach ya estaba.

Fuentes reales de las metodologias: tomferry.com, mikeferry.com,
buffiniandcompany.com, workmansuccess.com.

NOTA DE ENTORNO: NO correr contra la Aiven compartida (regla del rework). Pensado
para una DB local/QA o para que Infra lo ejecute en el deploy inicial del schema.
"""
import asyncio
import os
import sys
from datetime import time

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from models.dmo import Coach, DmoTemplate, DmoBlock

# metric_type: "checkbox" | "quantity"
CHECKBOX = "checkbox"
QUANTITY = "quantity"


# Cada entrada: coach (catalogo global) + su template oficial (workspace_id NULL).
CATALOG = [
    {
        "coach": {
            "name": "WhatsApp-first AR",
            "description": (
                "DMO adaptado al mercado argentino. Reemplaza el cold calling "
                "(que no funciona en AR post-pandemia) por el bloque de WhatsApp como "
                "canal principal de conversacion. Combina prospeccion calida + presencia "
                "en calle/visitas + captacion activa."
            ),
            "source_url": None,
            "is_official": True,
        },
        "template": {
            "name": "DMO Argentina (WhatsApp-first)",
            "description": "Rutina diaria adaptada al canal WhatsApp + presencia presencial.",
            "market": "AR",
            "blocks": [
                {
                    "name": "Apertura",
                    "description": "Revisar nuevos listings en portales (ZonaProp, Argenprop, ML), leads de la noche, agenda del dia.",
                    "start_time": time(8, 30), "end_time": time(9, 0),
                    "color": "#94a3b8", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Bloque WhatsApp",
                    "description": "El bloque clave del dia. Responder leads, nutrir cartera, pop-ins por WhatsApp. Meta: 10-15 conversaciones reales.",
                    "start_time": time(9, 0), "end_time": time(10, 30),
                    "color": "#25D366", "is_money_block": True,
                    "metric_type": QUANTITY, "metric_label": "Conversaciones", "metric_goal": 12,
                },
                {
                    "name": "Captacion activa",
                    "description": "Llamados a contactos calidos, pop-bys digitales, prospeccion a vencimientos de autorizacion de competencia.",
                    "start_time": time(10, 30), "end_time": time(11, 30),
                    "color": "#f59e0b", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Contactos calidos", "metric_goal": 5,
                },
                {
                    "name": "Calle / Visitas",
                    "description": "Visitas a propiedades, tasaciones, cafe con referentes, captaciones presenciales. En AR la confianza presencial pesa.",
                    "start_time": time(14, 0), "end_time": time(17, 0),
                    "color": "#22c55e", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Visitas/reuniones", "metric_goal": 1,
                },
                {
                    "name": "Cierre",
                    "description": "Cargar todo al CRM, agendar manana, mandar follow-ups pendientes, actualizar pipeline.",
                    "start_time": time(17, 30), "end_time": time(18, 30),
                    "color": "#3b82f6", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
            ],
        },
    },
    {
        "coach": {
            "name": "Tom Ferry",
            "description": (
                "Hijo y heredero de Mike Ferry, fundador de Tom Ferry International. "
                "Su metodologia 'Hour of Power' propone 60 minutos diarios de prospecting "
                "hasta lograr 6 conversaciones reales. Coach del top 1% de USA."
            ),
            "source_url": "https://www.tomferry.com/",
            "is_official": True,
        },
        "template": {
            "name": "Hora de Poder (Tom Ferry)",
            "description": "Desafio 90 dias: 6 conversaciones reales por dia.",
            "market": "USA",
            "blocks": [
                {
                    "name": "Mentalidad Matinal",
                    "description": "Meditacion, journaling, lectura. Visualizar el dia.",
                    "start_time": time(7, 0), "end_time": time(8, 0),
                    "color": "#a78bfa", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Hora de Poder",
                    "description": "60 minutos de prospeccion intensa. Meta: 6 conversaciones reales.",
                    "start_time": time(8, 0), "end_time": time(9, 0),
                    "color": "#ef4444", "is_money_block": True,
                    "metric_type": QUANTITY, "metric_label": "Conversaciones reales", "metric_goal": 6,
                },
                {
                    "name": "Seguimiento de Leads",
                    "description": "45 min de seguimiento a leads activos del CRM. Cadencia: dia 1, dia 3, dia 7.",
                    "start_time": time(9, 15), "end_time": time(10, 0),
                    "color": "#f59e0b", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Seguimientos", "metric_goal": 10,
                },
                {
                    "name": "Prospeccion de Zona",
                    "description": "15 min de prospeccion en zona propia (puerta a puerta, vecinos, autorizaciones vencidas).",
                    "start_time": time(10, 0), "end_time": time(10, 15),
                    "color": "#10b981", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Contactos en zona", "metric_goal": 3,
                },
                {
                    "name": "Visitas y Presentaciones",
                    "description": "Presentaciones de tasacion, recorridas, jornadas de puertas abiertas, reuniones con compradores y vendedores.",
                    "start_time": time(11, 0), "end_time": time(16, 0),
                    "color": "#22c55e", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Citas", "metric_goal": 2,
                },
                {
                    "name": "Cierre del Dia",
                    "description": "Actualizar CRM, armar agenda de manana, revisar metricas del dia.",
                    "start_time": time(16, 30), "end_time": time(17, 0),
                    "color": "#3b82f6", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
            ],
        },
    },
    {
        "coach": {
            "name": "Mike Ferry",
            "description": (
                "Fundador en 1975 de The Mike Ferry Organization, pionero del coaching "
                "inmobiliario moderno. Su DMO clasico exige 3 horas diarias de prospecting "
                "ininterrumpido a la manana, con scripts estructurados."
            ),
            "source_url": "https://www.mikeferry.com/",
            "is_official": True,
        },
        "template": {
            "name": "Prospeccion Clasica (Mike Ferry)",
            "description": "3h de prospeccion a la manana, ininterrumpidas. Scripts estructurados.",
            "market": "USA",
            "blocks": [
                {
                    "name": "Rutina Matinal",
                    "description": "Levantarse 6 AM, ejercicio, revisar agenda del dia.",
                    "start_time": time(6, 0), "end_time": time(8, 0),
                    "color": "#94a3b8", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Bloque de Prospeccion",
                    "description": "3 horas seguidas de llamados con scripts. Pomodoro: 25min activo, 5min pausa. SIN interrupciones.",
                    "start_time": time(8, 0), "end_time": time(11, 0),
                    "color": "#ef4444", "is_money_block": True,
                    "metric_type": QUANTITY, "metric_label": "Contactos", "metric_goal": 20,
                },
                {
                    "name": "Seguimiento de Leads",
                    "description": "Re-llamar leads, agendar citas, manejo de objeciones.",
                    "start_time": time(11, 0), "end_time": time(12, 0),
                    "color": "#f59e0b", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Citas agendadas", "metric_goal": 2,
                },
                {
                    "name": "Citas y Visitas",
                    "description": "Presentaciones de tasacion, consultas con compradores, visitas a propiedades.",
                    "start_time": time(13, 0), "end_time": time(17, 0),
                    "color": "#22c55e", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Citas", "metric_goal": 2,
                },
                {
                    "name": "Cierre Administrativo",
                    "description": "Papeleria, CRM, agenda del dia siguiente.",
                    "start_time": time(17, 0), "end_time": time(18, 0),
                    "color": "#3b82f6", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
            ],
        },
    },
    {
        "coach": {
            "name": "Brian Buffini",
            "description": (
                "Fundador en 1996 de Buffini & Company. Su sistema 'Work by Referral' "
                "rechaza el cold calling y construye negocio sobre la esfera de influencia "
                "via calls + notes + pop-bys (visitas con regalo). Members ganan ~10x el promedio."
            ),
            "source_url": "https://www.buffiniandcompany.com/",
            "is_official": True,
        },
        "template": {
            "name": "Trabajo por Referidos (Buffini)",
            "description": "Basado en la cartera de contactos. Sin llamadas frias. Llamadas + Notas + Visitas con atencion.",
            "market": "USA",
            "blocks": [
                {
                    "name": "Rutina Matinal",
                    "description": "Reflexion + planificacion. Repaso de la cartera del dia.",
                    "start_time": time(7, 30), "end_time": time(8, 30),
                    "color": "#a78bfa", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Llamadas a Cartera",
                    "description": "Llamados calidos a la cartera de contactos. Sin scripts agresivos, charla genuina de seguimiento.",
                    "start_time": time(9, 0), "end_time": time(10, 30),
                    "color": "#ef4444", "is_money_block": True,
                    "metric_type": QUANTITY, "metric_label": "Llamadas a cartera", "metric_goal": 5,
                },
                {
                    "name": "Notas Personales",
                    "description": "Escribir 3-5 notas a mano: agradecimientos, felicitaciones, recordatorios. El diferenciador clave del sistema.",
                    "start_time": time(10, 30), "end_time": time(11, 0),
                    "color": "#f59e0b", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Notas escritas", "metric_goal": 5,
                },
                {
                    "name": "Visitas con Atencion",
                    "description": "Visitas cortas a 2-3 contactos calidos con un detalle (cafe, planta, alfajor). 5 minutos cada una.",
                    "start_time": time(11, 0), "end_time": time(12, 30),
                    "color": "#10b981", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Visitas con atencion", "metric_goal": 3,
                },
                {
                    "name": "Generacion de Negocio",
                    "description": "Trabajo con compradores y vendedores actuales, visitas a propiedades, presentaciones.",
                    "start_time": time(13, 30), "end_time": time(17, 0),
                    "color": "#22c55e", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Actualizacion del CRM",
                    "description": "Cargar en el CRM cada interaccion con la cartera del dia.",
                    "start_time": time(17, 0), "end_time": time(17, 30),
                    "color": "#3b82f6", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
            ],
        },
    },
    {
        "coach": {
            "name": "Verl Workman",
            "description": (
                "Fundador de Workman Success Systems. Acuno el concepto 'Dollar Productive "
                "Activities' (DPA) y el principio 'anything you do 3 times, create a system'. "
                "Foco en time-blocking semanal y coaching de teams."
            ),
            "source_url": "https://workmansuccess.com/",
            "is_official": True,
        },
        "template": {
            "name": "Actividades Que Generan Plata (Workman)",
            "description": "Bloques de tiempo enfocados en actividades que generan ingresos directos.",
            "market": "USA",
            "blocks": [
                {
                    "name": "Foto del Mercado",
                    "description": "Revisar portales, listings nuevos en zona, precios que se mueven.",
                    "start_time": time(8, 0), "end_time": time(8, 45),
                    "color": "#94a3b8", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Actividades Que Generan Plata",
                    "description": "El bloque sagrado. Solo actividades que generan ingreso: captacion de leads, citas con vendedores, negociacion de contratos.",
                    "start_time": time(9, 0), "end_time": time(11, 0),
                    "color": "#ef4444", "is_money_block": True,
                    "metric_type": QUANTITY, "metric_label": "Contactos productivos", "metric_goal": 15,
                },
                {
                    "name": "Formacion",
                    "description": "30-60 min de capacitacion: scripts, role-play, lectura, podcast del rubro.",
                    "start_time": time(11, 0), "end_time": time(11, 45),
                    "color": "#a78bfa", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
                {
                    "name": "Atencion al Cliente",
                    "description": "Reuniones con clientes activos, visitas a propiedades, presentaciones, negociaciones.",
                    "start_time": time(13, 0), "end_time": time(16, 30),
                    "color": "#22c55e", "is_money_block": False,
                    "metric_type": QUANTITY, "metric_label": "Reuniones", "metric_goal": 2,
                },
                {
                    "name": "Sistemas y Procesos",
                    "description": "Trabajo sobre el negocio: mejorar checklists, automatizar, delegar.",
                    "start_time": time(16, 30), "end_time": time(17, 30),
                    "color": "#3b82f6", "is_money_block": False,
                    "metric_type": CHECKBOX, "metric_label": None, "metric_goal": 0,
                },
            ],
        },
    },
]


async def seed(db: AsyncSession) -> None:
    created_coaches = 0
    created_templates = 0
    for entry in CATALOG:
        cdata = entry["coach"]
        existing = (await db.execute(
            select(Coach).where(Coach.name == cdata["name"])
        )).scalar_one_or_none()
        if existing:
            print(f"  = coach ya existe, salteo: {cdata['name']}")
            continue

        coach = Coach(**cdata)
        db.add(coach)
        await db.flush()
        created_coaches += 1

        tdata = entry["template"]
        template = DmoTemplate(
            workspace_id=None,           # catalogo oficial GLOBAL
            coach_id=coach.id,
            name=tdata["name"],
            description=tdata["description"],
            market=tdata["market"],
            is_active=True,
            is_office_default=False,     # el "default" es una eleccion por workspace
        )
        db.add(template)
        await db.flush()
        for idx, b in enumerate(tdata["blocks"]):
            db.add(DmoBlock(template_id=template.id, sort_order=idx, **b))
        created_templates += 1
        print(f"  + coach + template oficial: {cdata['name']} -> {tdata['name']} ({len(tdata['blocks'])} bloques)")

    await db.commit()
    print(f"\nListo. Coaches nuevos: {created_coaches} | Templates oficiales nuevos: {created_templates}")


async def main() -> None:
    print("Seed catalogo DMO oficial (coaches globales + templates workspace_id=NULL)...")
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
