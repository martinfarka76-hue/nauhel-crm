path = "app/routers/calculation.py"
with open(path) as f:
    content = f.read()

old = '''@router.get("/calculations/{calculation_id}", response_model=CalculationOut)
def get_calculation(
    calculation_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _get_calculation_or_404(db, calculation_id)'''
new = '''@router.get("/calculations/{calculation_id}", response_model=CalculationOut)
def get_calculation(
    calculation_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _get_calculation_or_404(db, calculation_id)


@router.post("/calculations/{calculation_id}/activate", response_model=CalculationOut)
def activate_calculation(
    calculation_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Znovu nastaví jiz existujici (drive vytvorenou, ted neaktivni)
    kalkulaci jako aktivni - pro pripad, kdy zakaznik nakonec vybere
    drivejsi variantu, ne tu naposledy vytvorenou. Nevytvari novou
    kalkulaci, jen prehodi priznak is_active (stejna logika jako pri
    vytvoreni nove - vzdy jen jedna aktivni na Deal).
    """
    calculation = _get_calculation_or_404(db, calculation_id)

    db.query(Calculation).filter(
        Calculation.deal_id == calculation.deal_id, Calculation.is_active.is_(True)
    ).update({"is_active": False})

    calculation.is_active = True
    db.commit()
    db.refresh(calculation)
    return calculation'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Endpoint pridan uspesne")
