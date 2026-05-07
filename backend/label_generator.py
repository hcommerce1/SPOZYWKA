"""Generuje etykietę A6 PDF (premium B&W) zgodną z UE 1169/2011."""
import io, json, base64
from pathlib import Path

try:
    import barcode
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False

FONT_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="{font_url}">
<style>
  @page {{
    size: 105mm 148mm;
    margin: 5mm;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', sans-serif;
    font-size: 7pt;
    color: #000;
    border: 0.5pt solid #000;
    padding: 3mm;
    width: 95mm;
    min-height: 138mm;
  }}
  .product-name {{
    font-size: 14pt;
    font-weight: 700;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    padding-bottom: 2mm;
    border-bottom: 1.5pt solid #000;
    margin-bottom: 2mm;
  }}
  .section {{
    margin-bottom: 1.5mm;
    padding-bottom: 1.5mm;
    border-bottom: 0.3pt solid #555;
  }}
  .section:last-child {{ border-bottom: none; }}
  .label {{ font-weight: 600; font-size: 6.5pt; text-transform: uppercase; }}
  .dates-section {{
    background: #f0f0f0;
    padding: 1.5mm;
    margin-bottom: 2mm;
    border: 0.5pt solid #000;
  }}
  .dates-section .date-row {{
    font-weight: 700;
    font-size: 7.5pt;
    margin-bottom: 0.8mm;
  }}
  .bbf {{ font-size: 8pt; font-weight: 700; }}
  table.nutrition {{
    width: 100%;
    border-collapse: collapse;
    font-size: 6.5pt;
    margin-top: 1mm;
  }}
  table.nutrition th {{
    background: #d0d0d0;
    padding: 0.8mm 1mm;
    text-align: center;
    font-weight: 700;
    border: 0.3pt solid #000;
  }}
  table.nutrition td {{
    padding: 0.6mm 1mm;
    border: 0.3pt solid #555;
  }}
  table.nutrition tr:first-child td {{ border-top: 0.3pt solid #000; }}
  .barcode-section {{
    text-align: center;
    margin-top: 2mm;
  }}
  .barcode-section img {{ max-width: 55mm; height: auto; }}
  .certs {{
    font-size: 6pt;
    font-style: italic;
    margin-top: 1mm;
  }}
</style>
</head>
<body>

<div class="product-name">{product_name}</div>

<div class="section">
  <span class="label">Skład:</span> {ingredients}
</div>

<div class="dates-section">
  <div class="date-row bbf">NALEŻY SPOŻYĆ PRZED: {bbf}</div>
  <div class="date-row">DATA PRODUKCJI: {production_date}</div>
  <div class="date-row">NUMER PARTII (LOT): {lot_number}</div>
</div>

<div class="section">
  <span class="label">Wartości odżywcze (w 100ml / w porcji {serving}ml):</span>
  <table class="nutrition">
    <tr>
      <th>Składnik</th><th>100ml</th><th>Porcja {serving}ml</th>
    </tr>
    {nutrition_rows}
  </table>
</div>

<div class="section">
  <span class="label">Kraj/region pochodzenia:</span> {origin}<br>
  <span class="label">Importer/dystrybutor:</span> {importer}<br>
  <span class="label">Warunki przechowywania:</span> {storage}<br>
  <span class="label">Masa netto:</span> {net_weight}
</div>

<div class="section certs">{certs}</div>

<div class="barcode-section">
  {barcode_img}
  <div style="font-size:6pt; margin-top:0.5mm;">{ean}</div>
</div>

</body>
</html>"""


def _nutrition_rows(data: dict, serving: int) -> str:
    rows = []
    factor = serving / 100
    for name, val_100 in data.items():
        try:
            val_serving = f"{float(val_100) * factor:.1f}".rstrip("0").rstrip(".")
        except (ValueError, TypeError):
            val_serving = "—"
        rows.append(f"<tr><td>{name}</td><td>{val_100}</td><td>{val_serving}</td></tr>")
    return "\n    ".join(rows)


def _barcode_b64(ean: str) -> str:
    if not HAS_BARCODE or not ean or len(ean) != 13:
        return f"<span style='font-size:8pt;font-weight:700'>{ean}</span>"
    try:
        buf = io.BytesIO()
        barcode.get("ean13", ean, writer=ImageWriter()).write(buf, options={"write_text": False, "module_height": 10})
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="{ean}">'
    except Exception:
        return f"<span style='font-size:8pt;font-weight:700'>{ean}</span>"


def generate_label(meta: dict) -> bytes:
    """meta = dict zapisany przez Claude przez /mcp/session/{id}/meta"""
    from weasyprint import HTML

    serving = meta.get("serving_ml", 15)
    nutrition = meta.get("nutrition", {
        "Wartość energetyczna": "3700 kJ / 900 kcal",
        "Tłuszcz": "100 g",
        "w tym kwasy nasycone": "14 g",
        "Węglowodany": "0 g",
        "Białko": "0 g",
        "Sól": "0 g",
    })

    html = TEMPLATE.format(
        font_url=FONT_URL,
        product_name=meta.get("product_name", ""),
        ingredients=meta.get("ingredients", ""),
        bbf=meta.get("bbf", "—"),
        production_date=meta.get("production_date", "—"),
        lot_number=meta.get("lot_number", "—"),
        serving=serving,
        nutrition_rows=_nutrition_rows(nutrition, serving),
        origin=meta.get("origin", ""),
        importer=meta.get("importer", ""),
        storage=meta.get("storage", ""),
        net_weight=meta.get("net_weight", ""),
        certs=meta.get("certs", ""),
        barcode_img=_barcode_b64(meta.get("ean", "")),
        ean=meta.get("ean", ""),
    )

    return HTML(string=html).write_pdf()
