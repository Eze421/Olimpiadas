from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, SessionDep
from app.schemas import CartItemCreate, CartItemUpdate, CartRead
from app.services import CartService, DomainError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/cart", tags=["Carrito"])


def translate_error(error: Exception):
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ForbiddenError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, DomainError):
        raise HTTPException(status_code=422, detail=str(error))
    raise error


@router.get("", response_model=CartRead)
async def get_cart(user: CurrentUser, session: SessionDep):
    try:
        return await CartService(session).get(user)
    except (NotFoundError, ForbiddenError, DomainError) as error:
        translate_error(error)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_200_OK)
async def add_cart_item(data: CartItemCreate, user: CurrentUser, session: SessionDep):
    try:
        return await CartService(session).add(user, data)
    except (NotFoundError, ForbiddenError, DomainError) as error:
        translate_error(error)


@router.patch("/items/{item_id}", response_model=CartRead)
async def update_cart_item(item_id: int, data: CartItemUpdate, user: CurrentUser, session: SessionDep):
    try:
        return await CartService(session).update(user, item_id, data)
    except (NotFoundError, ForbiddenError, DomainError) as error:
        translate_error(error)


@router.delete("/items/{item_id}", response_model=CartRead)
async def remove_cart_item(item_id: int, user: CurrentUser, session: SessionDep):
    try:
        return await CartService(session).remove(user, item_id)
    except (NotFoundError, ForbiddenError, DomainError) as error:
        translate_error(error)


@router.delete("", response_model=CartRead)
async def clear_cart(user: CurrentUser, session: SessionDep):
    try:
        return await CartService(session).clear(user)
    except (NotFoundError, ForbiddenError, DomainError) as error:
        translate_error(error)
