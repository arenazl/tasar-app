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
