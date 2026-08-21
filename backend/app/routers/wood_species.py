import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.wood_species import WoodSpecies
from app.models.user import User
from app.schemas.wood_species import WoodSpeciesCreate, WoodSpeciesUpdate, WoodSpeciesOut

router = APIRouter(prefix="/wood-species", tags=["wood-species"])


@router.get("", response_model=list[WoodSpeciesOut])
def list_wood_species(db: Session = Depends(get_db)):
    return db.query(WoodSpecies).order_by(WoodSpecies.name).all()


@router.post("", response_model=WoodSpeciesOut, status_code=201)
def create_wood_species(
    payload: WoodSpeciesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    species = WoodSpecies(**payload.model_dump())
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


@router.put("/{species_id}", response_model=WoodSpeciesOut)
def update_wood_species(
    species_id: uuid.UUID,
    payload: WoodSpeciesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    species = db.query(WoodSpecies).filter(WoodSpecies.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Wood species not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(species, field, value)
    db.commit()
    db.refresh(species)
    return species


@router.delete("/{species_id}", status_code=204)
def delete_wood_species(
    species_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    species = db.query(WoodSpecies).filter(WoodSpecies.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Wood species not found")
    db.delete(species)
    db.commit()
