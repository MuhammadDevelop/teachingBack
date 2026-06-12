import asyncio
import cloudinary
import cloudinary.uploader
from app.config import get_settings

settings = get_settings()

# Cloudinary sozlamasi
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True
)


def get_resource_type(filename: str) -> str:
    """Fayl turini aniqlash: image, video, yoki raw"""
    if not filename:
        return "raw"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    image_exts = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico", "tiff"}
    video_exts = {"mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"}
    if ext in image_exts:
        return "image"
    elif ext in video_exts:
        return "video"
    return "raw"


async def upload_to_cloudinary(
    file_content: bytes,
    filename: str,
    folder: str = "homework_submissions"
) -> dict:
    """
    Faylni Cloudinary ga yuklash (async — event loop bloklanmaydi).
    
    Returns:
        dict: {"url": "https://res.cloudinary.com/...", "public_id": "..."}
    """
    resource_type = get_resource_type(filename)

    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        file_content,
        folder=folder,
        resource_type=resource_type,
        public_id=filename.rsplit(".", 1)[0] if "." in filename else filename,
        overwrite=True,
    )

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
    }


async def delete_from_cloudinary(public_id: str, resource_type: str = "image") -> bool:
    """Faylni Cloudinary dan o'chirish"""
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result.get("result") == "ok"
    except Exception:
        return False
