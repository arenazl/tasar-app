import asyncio
import time

import cloudinary
import cloudinary.uploader
from core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def _upload_image_sync(file_bytes: bytes, folder: str, filename: str | None) -> dict:
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=f"tasar/{folder}",
        public_id=filename,
        resource_type="image",
        overwrite=True,
    )
    return {
        "url": result.get("secure_url"),
        "public_id": result.get("public_id"),
        "width": result.get("width"),
        "height": result.get("height"),
    }


async def upload_image(file_bytes: bytes, folder: str, filename: str | None = None) -> dict:
    """Sube una foto de propiedad. to_thread: el SDK de Cloudinary es
    sync/bloqueante -- bloqueaba el event loop en cada subida (hallazgo
    F3-05). Mismo patron que upload_audio (WO F3-01)."""
    return await asyncio.to_thread(_upload_image_sync, file_bytes, folder, filename)


def delete_image(public_id: str) -> bool:
    res = cloudinary.uploader.destroy(public_id)
    return res.get("result") == "ok"


def _upload_audio_sync(file_bytes: bytes, folder: str) -> dict:
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=f"tasar/{folder}",
        public_id=f"op_{int(time.time() * 1000)}",
        resource_type="video",  # Cloudinary trata audio bajo 'video'
        format="ogg",           # transcodifica a ogg/opus, formato PTT de WhatsApp
        overwrite=True,
    )
    return {"url": result.get("secure_url"), "public_id": result.get("public_id")}


async def upload_audio(file_bytes: bytes, folder: str) -> dict:
    """Sube un audio grabado (ej. nota de voz del vendedor desde el Inbox, WO
    F3-01) y lo devuelve transcodificado a ogg/opus, listo para mandar como
    PTT por el gateway. to_thread: el SDK de Cloudinary es sync/bloqueante."""
    return await asyncio.to_thread(_upload_audio_sync, file_bytes, folder)


def _upload_pdf_sync(file_bytes: bytes, folder: str, filename: str) -> dict:
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=f"tasar/{folder}",
        # public_id con extension .pdf explicita: los recursos 'raw' de
        # Cloudinary sirven Content-Type segun la extension de la URL --
        # sin esto quedaba como application/octet-stream y el navegador
        # forzaba descarga en vez de abrir el PDF inline (window.open).
        public_id=f"{filename}.pdf",
        resource_type="raw",  # PDFs van como 'raw' en Cloudinary (no son imagen/video)
        overwrite=True,
    )
    return {"url": result.get("secure_url"), "public_id": result.get("public_id")}


async def upload_pdf(file_bytes: bytes, folder: str, filename: str) -> dict:
    """Sube un PDF generado (reportes mensuales, WO F4-03) y devuelve su URL
    publica. to_thread: el SDK de Cloudinary es sync/bloqueante (mismo patron
    que upload_image/upload_audio)."""
    return await asyncio.to_thread(_upload_pdf_sync, file_bytes, folder, filename)
