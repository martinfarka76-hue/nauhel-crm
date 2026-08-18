import enum


class DealStatus(str, enum.Enum):
    LEAD = "Lead"
    KVALIFIKOVANY_LEAD = "Kvalifikovaný lead"
    NABIDKA = "Nabídka"
    OBJEDNAVKA = "Objednávka"
    ZALOHOVA_FAKTURA = "Zálohová faktura"
    VYROBENO = "Vyrobeno"
    FAKTUROVANO = "Fakturováno"
    ZTRACENO = "Ztraceno"


class DocumentType(str, enum.Enum):
    NABIDKA = "Nabídka"
    OBJEDNAVKA = "Objednávka"
    ZALOHOVA_FAKTURA = "Zálohová faktura"
    DODACI_LIST = "Dodací list"
    FINALNI_FAKTURA = "Finální faktura"
