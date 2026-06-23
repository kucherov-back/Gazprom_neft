"""Мини-реестр атрибутов."""
from pydantic import BaseModel


class AttributeDefinition(BaseModel):
    code: str
    display_name: str
    unit: str | None = None
    synonyms: list[str] = []


_ATTRS = {
    "DN": AttributeDefinition(code="DN", display_name="Номинальный диаметр", unit="мм",
                              synonyms=["условный проход", "Ду", "DN", "DY"]),
    "PN": AttributeDefinition(code="PN", display_name="Условное давление", unit="МПа",
                              synonyms=["рабочее давление", "Ру", "PN"]),
    "MATERIAL": AttributeDefinition(code="MATERIAL", display_name="Материал корпуса",
                                    synonyms=["материал", "исполнение", "сталь"]),
}


def get_attribute(code: str) -> AttributeDefinition:
    return _ATTRS[code]
