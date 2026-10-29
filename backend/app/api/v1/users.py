"""
User Management Endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.task import Task
from backend.app.models.review import Submission
from backend.app.models.audit import AuditLog
from backend.app.schemas.auth import UserResponse
from backend.app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/users", tags=["Users"])

class CreateUserRequest(BaseModel):
    email: str = Field(..., example="intern2@internal.company")
    full_name: str = Field(..., example="Ananya Sen")
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.INTERN

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == request.email.strip().lower()))
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    new_user = User(
        email=request.email.strip().lower(),
        full_name=request.full_name.strip(),
        hashed_password=hash_password(request.password),
        role=request.role,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="USER_CREATED",
        resource_type="user",
        resource_id=new_user.id
    )
    db.add(audit)
    await db.commit()

    return new_user

@router.get("/", response_model=List[UserResponse])
async def list_users(
    role: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ASSIGNER, UserRole.ADMIN]))
):
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.role == UserRole.ASSIGNER and user.role != UserRole.INTERN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assigners can only delete intern accounts")

    # Unlink any tasks assigned to this user
    tasks_res = await db.execute(select(Task).where(Task.intern_id == user.id))
    for t in tasks_res.scalars().all():
        t.intern_id = None

    # Delete submissions if any
    sub_res = await db.execute(select(Submission).where(Submission.intern_id == user.id))
    for s in sub_res.scalars().all():
        await db.delete(s)

    user_email = user.email
    user_name = user.full_name
    await db.delete(user)

    audit = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="USER_DELETED",
        resource_type="user",
        resource_id=user_id,
        details_json=f'{{"email": "{user_email}", "full_name": "{user_name}", "role": "{user.role.value}"}}'
    )
    db.add(audit)
    await db.commit()

    return {"message": f"Intern {user_name} ({user_email}) successfully deleted", "id": user_id}

