from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import CurrentUser, SessionDep
from app.core.config import settings
from app.models import ProductImage
from app.schemas import ProductCreate, ProductImageRead, ProductRead, ProductUpdate
from app.services import DomainError, ForbiddenError, NotFoundError, ProductService

router = APIRouter(prefix="/catalog/products", tags=["Catálogo"])
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {
    "image/jpeg": ("jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": ("png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": ("webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}


def translate_error(error: Exception):
    if isinstance(error, ForbiddenError): raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, NotFoundError): raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, DomainError): raise HTTPException(status_code=422, detail=str(error))
    raise error


@router.get("", response_model=list[ProductRead])
async def list_products(session: SessionDep):
    return await ProductService(session).list()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, session: SessionDep):
    try: return await ProductService(session).get(product_id)
    except (NotFoundError, ForbiddenError, DomainError) as error: translate_error(error)


@router.get("/manage/all", response_model=list[ProductRead])
async def admin_list_products(user: CurrentUser, session: SessionDep):
    try: return await ProductService(session).admin_list(user)
    except (NotFoundError, ForbiddenError, DomainError) as error: translate_error(error)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, user: CurrentUser, session: SessionDep):
    try: return await ProductService(session).create(user, data)
    except (NotFoundError, ForbiddenError, DomainError) as error: translate_error(error)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, data: ProductUpdate, user: CurrentUser, session: SessionDep):
    try: return await ProductService(session).update(user, product_id, data)
    except (NotFoundError, ForbiddenError, DomainError) as error: translate_error(error)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, user: CurrentUser, session: SessionDep):
    try: await ProductService(session).delete(user, product_id)
    except (NotFoundError, ForbiddenError, DomainError) as error: translate_error(error)


@router.post("/{product_id}/images", response_model=ProductImageRead, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    product_id: int,
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None, max_length=180),
):
    media_type = file.content_type or ""
    image_type = IMAGE_TYPES.get(media_type)
    if image_type is None:
        raise HTTPException(status_code=415, detail="Formato no permitido; use JPEG, PNG o WebP")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Cada imagen puede pesar hasta 5 MB")
    extension, validator = image_type
    if not validator(content):
        raise HTTPException(status_code=415, detail="El contenido no coincide con el formato de imagen declarado")

    folder = Path(settings.media_dir) / "products"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    destination = folder / filename
    destination.write_bytes(content)
    try:
        image = await ProductService(session).add_image(user, product_id, f"/media/products/{filename}", alt_text)
        return image
    except (NotFoundError, ForbiddenError, DomainError) as error:
        destination.unlink(missing_ok=True)
        translate_error(error)


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(product_id: int, image_id: int, user: CurrentUser, session: SessionDep):
    try:
        url = await ProductService(session).remove_image(user, product_id, image_id)
        (Path(settings.media_dir) / url.removeprefix("/media/")).unlink(missing_ok=True)
    except (NotFoundError, ForbiddenError, DomainError) as error:
        translate_error(error)
