# 1) Model
path1 = "app/models/calculation_item.py"
with open(path1) as f:
    content1 = f.read()

old1 = '''    category = Column(Enum(ItemCategory), nullable=False)
    name = Column(String(255), nullable=False)
    unit = Column(String(20), nullable=True)  # m², bm, ks, kpl, zakázka...
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    display_order = Column(Integer, nullable=False, default=0)

    calculation = relationship("Calculation", back_populates="items")'''
new1 = '''    category = Column(Enum(ItemCategory), nullable=False)
    name = Column(String(255), nullable=False)
    unit = Column(String(20), nullable=True)  # m², bm, ks, kpl, zakázka...
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    display_order = Column(Integer, nullable=False, default=0)
    # Pokud polozka vznikla z "Predvyplnit z drevin", ulozi se sem ID te
    # dreviny - umoznuje pozdejsi "Prepocitat podle aktualni produktove
    # rady" bez nutnosti hadat, z ceho polozka vznikla. Rucne pridane
    # polozky (a polozky z cenikuu partnera) toto pole nemaji.
    wood_species_id = Column(UUID(as_uuid=True), ForeignKey("wood_species.id"), nullable=True)

    calculation = relationship("Calculation", back_populates="items")'''

count1 = content1.count(old1)
if count1 != 1:
    print(f"CHYBA model: nalezeno {count1}x")
else:
    content1 = content1.replace(old1, new1)
    with open(path1, 'w') as f:
        f.write(content1)
    print("Model opraven")

# 2) Schema
path2 = "app/schemas/calculation_item.py"
with open(path2) as f:
    content2 = f.read()

patches2 = [
    (
        '''class CalculationItemCreate(BaseModel):
    category: ItemCategory
    name: str
    unit: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    display_order: int = 0''',
        '''class CalculationItemCreate(BaseModel):
    category: ItemCategory
    name: str
    unit: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    display_order: int = 0
    wood_species_id: Optional[uuid.UUID] = None'''
    ),
    (
        '''class CalculationItemUpdate(BaseModel):
    category: Optional[ItemCategory] = None
    name: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    display_order: Optional[int] = None''',
        '''class CalculationItemUpdate(BaseModel):
    category: Optional[ItemCategory] = None
    name: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    display_order: Optional[int] = None
    wood_species_id: Optional[uuid.UUID] = None'''
    ),
    (
        '''    quantity: Decimal
    unit_price: Decimal
    display_order: int''',
        '''    quantity: Decimal
    unit_price: Decimal
    display_order: int
    wood_species_id: Optional[uuid.UUID] = None'''
    ),
]

ok2 = True
for i, (old, new) in enumerate(patches2):
    count = content2.count(old)
    if count != 1:
        print(f"CHYBA schema patch {i+1}: nalezeno {count}x")
        ok2 = False
    else:
        content2 = content2.replace(old, new)

if ok2:
    with open(path2, 'w') as f:
        f.write(content2)
    print("Schema opraveno")
else:
    print("Schema NEBYLO zapsano kvuli chybe")
