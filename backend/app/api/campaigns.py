from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_client
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.task import Task, TaskStatus
from app.models.user import Client
from app.services.geo import geocode_address

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    city: str  # "Москва" — используется при геокодировании
    category: str
    description: str | None = None
    price_per_task: float = 150
    addresses: list[str]


class CampaignOut(BaseModel):
    id: int
    name: str
    city: str
    category: str
    description: str | None
    price_per_task: float
    status: str
    created_at: datetime
    published_at: datetime | None
    total_tasks: int = 0
    completed_tasks: int = 0
    pending_tasks: int = 0
    pending_review_tasks: int = 0
    rejected_tasks: int = 0
    in_progress_tasks: int = 0

    model_config = {"from_attributes": True}


def _campaign_out(c: Campaign, tasks: list) -> CampaignOut:
    return CampaignOut(
        id=c.id,
        name=c.name,
        city=c.city,
        category=c.category,
        description=c.description,
        price_per_task=float(c.price_per_task),
        status=c.status.value,
        created_at=c.created_at,
        published_at=c.published_at,
        total_tasks=len(tasks),
        completed_tasks=sum(1 for t in tasks if t.status == TaskStatus.completed),
        pending_tasks=sum(1 for t in tasks if t.status == TaskStatus.available),
        pending_review_tasks=sum(1 for t in tasks if t.status == TaskStatus.pending_review),
        in_progress_tasks=sum(1 for t in tasks if t.status == TaskStatus.in_progress),
        rejected_tasks=sum(1 for t in tasks if t.status == TaskStatus.rejected),
    )


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.client_id == client.id)
        .options(selectinload(Campaign.tasks))
        .order_by(Campaign.created_at.desc())
    )
    return [_campaign_out(c, c.tasks) for c in result.scalars().all()]


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(
        client_id=client.id,
        name=data.name,
        city=data.city.strip(),
        category=data.category,
        description=data.description,
        price_per_task=data.price_per_task,
        status=CampaignStatus.draft,
    )
    db.add(campaign)
    await db.flush()

    tasks = []
    for address in data.addresses:
        address = address.strip()
        if not address:
            continue
        coords = await geocode_address(address, city=data.city.strip())
        task = Task(
            campaign_id=campaign.id,
            address=address,
            lat=coords["lat"] if coords else None,
            lng=coords["lng"] if coords else None,
            status=TaskStatus.available,
        )
        db.add(task)
        tasks.append(task)

    await db.commit()
    await db.refresh(campaign)
    return _campaign_out(campaign, tasks)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.client_id == client.id)
        .options(selectinload(Campaign.tasks))
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    return _campaign_out(campaign, campaign.tasks)


@router.post("/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: int,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.client_id == client.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if campaign.status != CampaignStatus.draft:
        raise HTTPException(status_code=400, detail="Кампания уже опубликована")

    campaign.status = CampaignStatus.active
    campaign.published_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}
