"""Промпты извлечения. Наполни few-shot примерами по домену."""

EXTRACTION_SYSTEM = """
TODO(кандидат): системный промпт извлекателя.
Требования к выводу — строгий JSON: value, unit, confidence (high|medium|low),
source_quote (ДОСЛОВНАЯ цитата из текста, откуда взято значение). Если значения в
тексте нет — value=null. Не выдумывай.
""".strip()

# TODO(кандидат): 1-2 few-shot примера (арматура/трубопровод): вход-текст + эталонный JSON.
FEW_SHOT_EXAMPLES: list[dict] = []
