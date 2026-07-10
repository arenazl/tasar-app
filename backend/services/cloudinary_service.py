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


async def upload_image(file_bytes: bytes, folder: str, filename: str | None = None) -> dict:
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
