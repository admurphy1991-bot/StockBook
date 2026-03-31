from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncpg
import os
import json
import csv
import io
from datetime import date
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB ──────────────────────────────────────────────────────────────────────

async def get_db():
    return await asyncpg.connect(os.environ["DATABASE_URL"])

@app.on_event("startup")
async def startup():
    import time
    for attempt in range(10):
        try:
            conn = await get_db()
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_entries (
                    id SERIAL PRIMARY KEY,
                    item_code TEXT NOT NULL,
                    entry_date DATE NOT NULL,
                    job TEXT NOT NULL,
                    supplier TEXT,
                    description TEXT NOT NULL,
                    cost_quantity NUMERIC NOT NULL,
                    unit TEXT,
                    comments TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.close()
            print("Database ready.")
            return
        except Exception as e:
            print(f"DB not ready (attempt {attempt+1}/10): {e}")
            time.sleep(3)
    print("WARNING: Could not connect to database on startup.")

# ── Products (embedded from CSV) ─────────────────────────────────────────────

PRODUCTS = [
    {"code":"060255A02R","description":"BITUTHENE 5000 - ROLL","supplier":"ALLNEX","unit":"ROLL"},
    {"code":"061403A01P","description":"AQUAGUARD (101A) + (101B) 10ltr Kit","supplier":"DGL","unit":"KIT"},
    {"code":"067485A14R01","description":"CSM E20 EMULSION 300g/sm JUSHI - ROL","supplier":"DGL","unit":"KG"},
    {"code":"067533A01E01","description":"Aquaguard 101 8lt kit","supplier":"DGL","unit":"LTR"},
    {"code":"10543","description":"WPM3000X 20M X 1.0M X 1.5MM ROLL","supplier":"ARDEX","unit":"ea"},
    {"code":"114665","description":"Sika - Primer 3N (250ml)","supplier":"SIKA","unit":"EA"},
    {"code":"130020","description":"Xypex Concentrate 20kg","supplier":"DEMDEN","unit":"PAIL"},
    {"code":"153729","description":"Sika - Sikaflex AT Facade (600ml sausage)","supplier":"SIKA","unit":"EA"},
    {"code":"153730","description":"Sikaflex AT Facade 600ml White","supplier":"SIKA","unit":"EA"},
    {"code":"153731","description":"Sikaflex AT Facade 600ml Black","supplier":"SIKA","unit":"EA"},
    {"code":"160020","description":"Xypex Patch n Plug","supplier":"DEMDEN","unit":"KG"},
    {"code":"185041","description":"Sikalastic-152 (Part A 8kg) (Part B 25kg) KIT","supplier":"SIKA","unit":"KIT"},
    {"code":"20101","description":"Soudal Soudaseal 240FC MS Adhesive 600ml Grey","supplier":"MERZLTD","unit":"ea"},
    {"code":"24560","description":"WPM117 Shelterstick 15m x 1m x 2mm - roll","supplier":"ARDEX","unit":"ea"},
    {"code":"24954","description":"K900BF 20kg bag","supplier":"ARDEX","unit":"BAG"},
    {"code":"35538","description":"BLACK PLASTIC ROLL 5m x 50m x 80 roll","supplier":"TRADE","unit":"EA"},
    {"code":"35933C","description":"Tradextra S361 Silver Cloth Tape 48mm x 30m","supplier":"TRADE","unit":"ROLL"},
    {"code":"405BOOM","description":"Sika Boom 750ml","supplier":"SIKA","unit":"EA"},
    {"code":"435005","description":"Sikadur Injectokit-TH 250g","supplier":"SIKA","unit":"EA"},
    {"code":"440627","description":"Sika Blackseal Plus Elastic 20L","supplier":"SIKA","unit":"PAIL"},
    {"code":"444906","description":"Sika Thinner C Lt (20L)","supplier":"SIKA","unit":"EA"},
    {"code":"444908","description":"Sika Thinner C Lt (4 ltr)","supplier":"SIKA","unit":"EA"},
    {"code":"452396","description":"Sikadur UA 8L","supplier":"SIKA","unit":"ea"},
    {"code":"452399","description":"Sika - Sikadur U.A 4 Lt","supplier":"SIKA","unit":"EA"},
    {"code":"497964","description":"Sika AnchorFix-1 300ml","supplier":"SIKA","unit":"EA"},
    {"code":"520310","description":"Sikaflex 11 FC 310ml Black","supplier":"SIKA","unit":"ML"},
    {"code":"520472","description":"Nailbond Premium 600ml","supplier":"SIKA","unit":"EA"},
    {"code":"536973","description":"Sikaflex - 400 Fire Grey 600ml","supplier":"SIKA","unit":"EA"},
    {"code":"551349","description":"SikaTop Seal-107 Dryseal 5kg","supplier":"SIKA","unit":"KG"},
    {"code":"551940","description":"Sika MonoTop-438 R (25kg)","supplier":"SIKA","unit":"EA"},
    {"code":"565413","description":"Sikadur-52 Injection Normal 0.9l/kg","supplier":"SIKA","unit":"KIT"},
    {"code":"591755","description":"Sikaflex MS 600ml White","supplier":"SIKA","unit":"ea"},
    {"code":"59300074","description":"BluRez CS150 20kg","supplier":"MB Solutions","unit":"ea"},
    {"code":"617759","description":"Sikaflex PRO-3 Purform 600ml","supplier":"SIKA","unit":"ea"},
    {"code":"80151200","description":"Turbo wave diamond blade dry/wet cured concrete","supplier":"Chelsea Diamond Tools","unit":"ea"},
    {"code":"82151204","description":"125mm Disc. (diamond saw blade)","supplier":"Chelsea Diamond Tools","unit":"ea"},
    {"code":"85681206","description":"5 turbo cup grinding wheel 12 segments","supplier":"Chelsea Diamond Tools","unit":"ea"},
    {"code":"92541","description":"Sikaplug 5KG","supplier":"SIKA","unit":"EA"},
    {"code":"ACE.5","description":"ACETONE - 5L","supplier":"NZ Fibreglass Supplies","unit":"PAIL"},
    {"code":"ADCOR500T","description":"ADCOR 500T WATERSTOP 6x5m CTN - CTN","supplier":"ALLNEX","unit":"ea"},
    {"code":"ALLAQ15","description":"Aquadrain 15 18.9M2 VAQUA15X","supplier":"ALLCO","unit":"ROLL"},
    {"code":"ALLBESA","description":"Allco - Bentoseal 15kg","supplier":"ALLCO","unit":"PAIL"},
    {"code":"ALLBETG","description":"Allco - Bentogrout 25kg","supplier":"ALLCO","unit":"BAG"},
    {"code":"ALLCET","description":"Allco - Cetcoat 15kg","supplier":"ALLCO","unit":"PAIL"},
    {"code":"ALLDE4","description":"Dermabit Extra - 4mm thick Polypropylene one side","supplier":"ALLCO","unit":"ROLL"},
    {"code":"ALLRX101","description":"RX101T Waterstop 6.1lm per roll","supplier":"ALLCO","unit":"ROLL"},
    {"code":"ALLRX101DH","description":"RX101DH waterstop delayed Hydration 5m","supplier":"ALLCO","unit":"ROLL"},
    {"code":"ALLSWTB","description":"Allco - Swelltite Termination Bar Lm","supplier":"ALLCO","unit":"LM"},
    {"code":"ALLVOCR","description":"Allco - Voltex CR (5.4sqm roll)","supplier":"ALLCO","unit":"M2"},
    {"code":"ALLVODS","description":"Allco - Voltex Super 66.6 DS","supplier":"ALLCO","unit":"ROLL"},
    {"code":"ALLVOLT","description":"Voltex Roll (5.5m2 per roll) m2","supplier":"ALLCO","unit":"ROLL"},
    {"code":"ALLWSTG","description":"Allco - Waterstoppage 25kg bag","supplier":"ALLCO","unit":"BAG"},
    {"code":"ALSANMASTIC/2200","description":"ALSAN MASTIC 2200 SEALANT (310ML/CARTRIDGE)","supplier":"Equus Industries Limited","unit":"ea"},
    {"code":"ARD100FT","description":"Ardex - Flashing Tape 4.7m x 100mm roll","supplier":"ARDEX","unit":"ROLL"},
    {"code":"ARD150DT","description":"Ardex - Uncured Detail Tape 30.4m x 150mm roll","supplier":"ARDEX","unit":"ROLL"},
    {"code":"ARD15DG","description":"Ardex - Butynol Dv Grey 17.86m x1.4m x1.5mm roll","supplier":"ARDEX","unit":"ROLL"},
    {"code":"ARD15MB","description":"Ardex - Butynol Black 17.86m x 1.4m x 1.5mm roll","supplier":"ARDEX","unit":"ROLL"},
    {"code":"ARD50ST","description":"Ardex - Butynol Seam Tape 30.4m x 50mm roll","supplier":"ARDEX","unit":"ROLL"},
    {"code":"ARDA38","description":"Ardex - A38 20kg bag (Aust)","supplier":"ARDEX","unit":"BAG"},
    {"code":"ARDA46","description":"Ardex - A46 20kg bag","supplier":"ARDEX","unit":"BAG"},
    {"code":"ARDAD","description":"Ardex - WA98 Adhesive 20L pail","supplier":"ARDEX","unit":"PAIL"},
    {"code":"ARDOPT","description":"Ardex - Optima 40kg","supplier":"ARDEX","unit":"KIT"},
    {"code":"ARDP51","description":"Ardex - P51 5L bottle","supplier":"ARDEX","unit":"PAIL"},
    {"code":"ARDSAND","description":"Ardex - ARDEX Engineered Sand 20kg Bag","supplier":"ARDEX","unit":"BAG"},
    {"code":"ARDST","description":"Ardex - Substrate Joint Tape 50mx25mm 36roll/ctn","supplier":"ARDEX","unit":"ROLL"},
    {"code":"ATDUCT","description":"Attwoods - Silver Cloth Tape per roll","supplier":"ATTWOODS I","unit":"ROLL"},
    {"code":"B10019A01R01","description":"REINFORCING TAPE 100mm Roll","supplier":"DGL","unit":"ROLL"},
    {"code":"B1BTB2P","description":"BITUTHENE B2 PRIMER (1.00 x 25 Lt)","supplier":"ALLNEX","unit":"PAIL"},
    {"code":"B1BTLQM","description":"BITUTHENE LIQUID MEMBRANE LM3000 (5.7LT)","supplier":"ALLNEX","unit":"ea"},
    {"code":"B1BTM","description":"BITUTHENE MASTIC (12.00 x 300 ml tube)","supplier":"ALLNEX","unit":"ea"},
    {"code":"B1BTSSM","description":"Swellseal Mastic WA (12 per box)","supplier":"ALLNEX","unit":"ea"},
    {"code":"B1SOGJ","description":"Soprema Granules 1kg","supplier":"ALLNEX","unit":"KG"},
    {"code":"BIBT3000","description":"Bituthene 3000 (1.00 x 20m Roll)","supplier":"ALLNEX","unit":"ROLL"},
    {"code":"CA20P","description":"CA20P Black - Cartridge 310 ML","supplier":"ARDEX","unit":"ea"},
    {"code":"CBFIL30","description":"Bitumen Fillet 30mm x 30mm x 1100mm","supplier":"ALLCO","unit":"ea"},
    {"code":"CBW426157","description":"IMPRABOARD WHITE 680GSM 1200 x 4mm (10 sheets per bag)","supplier":"MULFORD PLASTICS","unit":"SHEET"},
    {"code":"COREFL18","description":"Allguard Coreflute 1800 x 1150 x 4mm","supplier":"ALLCO","unit":"SHEET"},
    {"code":"CSW","description":"BluRez CWS Base 20kg Drum","supplier":"MB Solutions","unit":"ea"},
    {"code":"D1","description":"Newton Basedrain - 2m Length","supplier":"Newtons Systems Ltd","unit":"M"},
    {"code":"D21","description":"Newton Basedrain - Sump Connector","supplier":"Newtons Systems Ltd","unit":"ea"},
    {"code":"D30","description":"Newton Basedrain - Inspection PortBase - 204 mm x 60 mm opening","supplier":"Newtons Systems Ltd","unit":"ea"},
    {"code":"D6","description":"Newton Basedrain - Swept Corner","supplier":"Newtons Systems Ltd","unit":"ea"},
    {"code":"DDR314200","description":"R SERIES CARBIDE 14MMX200MM","supplier":"RAMSET","unit":"ea"},
    {"code":"DEXX/GR/15","description":"Chevaline Dexx","supplier":"Equus Industries Limited","unit":"ea"},
    {"code":"EXPOLY","description":"Expol - Polystyrene Sheet 1.8x1.2","supplier":"EXPOL","unit":"EA"},
    {"code":"GELG4","description":"Gel G4","supplier":"Glue Guru Industrial Products","unit":"ea"},
    {"code":"GLASS/300","description":"Fibreglass Mat 300 GSM","supplier":"Equus Industries Limited","unit":"M"},
    {"code":"HAP19520","description":"AQUENCE BG P195 Adhesive 21kg Pail","supplier":"Glue Guru Industrial Products","unit":"ea"},
    {"code":"M1000035","description":"Bitumen Sealant 300ml","supplier":"Merz Construction Products Ltd","unit":"ea"},
    {"code":"NUA101","description":"Aquaguard 101 (A & B, 10ltr Kit) per ltr","supplier":"ALLNEX","unit":"LTR"},
    {"code":"NUR3PM","description":"Nuraply Slate Cap Sheet","supplier":"Nuralite","unit":"EA"},
    {"code":"NURA3PC","description":"Nuraply 3PC","supplier":"Nuralite","unit":"ROLL"},
    {"code":"NURFIL","description":"Bitumen Fillet 1.2m length","supplier":"Equus Industries Limited","unit":"ea"},
    {"code":"NURVB","description":"Nuraply Alu Vapour Barrier","supplier":"Nuralite","unit":"ROLL"},
    {"code":"PE751","description":"TERMINATION BAR 2.4M(FOLDED)","supplier":"Nuralite","unit":"M"},
    {"code":"PFRO002","description":"PFROD 06mm dia. 50m Coil","supplier":"A&E Karsten","unit":"ROLL"},
    {"code":"PFRO005","description":"PF Rod 8mm 50m Coil (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO008","description":"PF Rod 10mm 50m Coil (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO014","description":"PF Rod 15mm 50m Coil (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO015","description":"PF Rod 15mm 100m coil (per roll)","supplier":"A&E Karsten","unit":"ROLL"},
    {"code":"PFRO016","description":"PF Rod 20mm dia 20m coil (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO017","description":"PF Rod 20mm 60m coil (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO018","description":"PF Rod 25mm 2m length (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO019","description":"PF Rod 25mm 25m length (per roll)","supplier":"A&E Karsten","unit":"ROLL"},
    {"code":"PFRO020","description":"PF Rod 30mm 2m length (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO021","description":"PF Rod 30mm 25m length (per roll)","supplier":"A&E Karsten","unit":"ROLL"},
    {"code":"PFRO022","description":"PF Rod 40mm 2m length (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PFRO023","description":"PF Rod 50mm 2m length (per mtr)","supplier":"A&E Karsten","unit":"M"},
    {"code":"PREPRUFE30","description":"PREPRUFE 300R PLUS - ROL 1.2 x 30m","supplier":"ALLNEX","unit":"ROLL"},
    {"code":"RF124","description":"Nuraply 3PB Basesheet (10 m x 1m x 3mm roll)","supplier":"Nuralite","unit":"ROLL"},
    {"code":"RF169","description":"IKOprotect MS DETAIL 1LT (1.5KG)","supplier":"Nuralite","unit":"LTR"},
    {"code":"RF170","description":"KO hybrytech MS DETAIL 1LT [BLACK]","supplier":"Nuralite","unit":"LTR"},
    {"code":"RF751","description":"MS SEALANT 415gm BLACK FIXALL 220","supplier":"Nuralite","unit":"ea"},
    {"code":"SDM06030SS","description":"SHURE DRIVE SS 6X30MM","supplier":"RAMSET","unit":"ea"},
    {"code":"SI11FC","description":"Sika - Sikaflex11 FC purform","supplier":"SIKA","unit":"EA"},
    {"code":"SI212","description":"Sika - 212 Grout 25kg","supplier":"SIKA","unit":"BAG"},
    {"code":"SI31","description":"Sikadur-31 CF Normal kg","supplier":"SIKA","unit":"KG"},
    {"code":"SI412","description":"Sika - Monotop 412 bag","supplier":"SIKA","unit":"BAG"},
    {"code":"SI42","description":"Sikadur-42 (15KG KIT)","supplier":"SIKA","unit":"KIT"},
    {"code":"SI910","description":"Sika Monotop 910N Primer 4kg","supplier":"SIKA","unit":"EA"},
    {"code":"SIBS","description":"Sika Blackseal cartridge","supplier":"SIKA","unit":"EA"},
    {"code":"SIINLV250","description":"Sikadur Injectokit- LV 250","supplier":"SIKA","unit":"EA"},
    {"code":"SISW53","description":"Sika Swell A 2005 20mm x 5mm x 20m","supplier":"SIKA","unit":"ROLL"},
    {"code":"SISWP","description":"SikaSwell-P 2010H 20mm x 10mm x 10m","supplier":"SIKA","unit":"ROLL"},
    {"code":"SISWS2","description":"Sika Swell S2 600ml","supplier":"SIKA","unit":"EA"},
    {"code":"SXR121S","description":"Professional Sausage Gun","supplier":"Glue Guru Industrial Products","unit":"ea"},
    {"code":"SXR261S","description":"SINTEX R26:1S MS Sausage Gun","supplier":"Glue Guru Industrial Products","unit":"ea"},
    {"code":"TK102","description":"NURAFLUX PRIMER (QD) 25l","supplier":"Nuralite","unit":"PAIL"},
    {"code":"TK109","description":"Bitumen Trianglular Fillet 1.2m","supplier":"Nuralite","unit":"EA"},
    {"code":"TK115B","description":"NURADRAIN GF (2m X 20m)","supplier":"Nuralite","unit":"ROLL"},
    {"code":"TK151","description":"Bituthene Liquid Membrane (Kit)","supplier":"Nuralite","unit":"ea"},
    {"code":"TK153","description":"PREPRUFE 300R PLUS (31.15M)","supplier":"Nuralite","unit":"ROLL"},
    {"code":"TK157","description":"PREPRUFE LT TAPE 100mm (15M)","supplier":"Nuralite","unit":"ROLL"},
    {"code":"TK160","description":"PREPURFE LT DETAIL TAPE 50mm (15M)","supplier":"ALLNEX","unit":"ROLL"},
    {"code":"TRAXX2000/20","description":"TRAXX 2000","supplier":"Equus Industries Limited","unit":"M"},
    {"code":"VCS600","description":"Cetseal (20oz) 600mls Sausage - Polymeric Sealant/Adhesive","supplier":"ALLCO","unit":"600ML"},
    {"code":"VCTX","description":"Volclay Coretex (9.29m2) roll","supplier":"ALLCO","unit":"ROLL"},
    {"code":"VRX10210","description":"Allco - RX102 Waterstop 10.2m","supplier":"ALLCO","unit":"ROLL"},
    {"code":"VST50","description":"DPM Tape Allsheet 48mm x 30 m Red","supplier":"ALLCO","unit":"M"},
    {"code":"VSTPOL10.2","description":"Swelltite Polish 3000 10.2m Roll","supplier":"ALLCO","unit":"ROLL"},
    {"code":"VVS500","description":"Allsheet 500 micron non hydrostatic DPM PE 4x25m","supplier":"ALLCO","unit":"ROLL"},
    {"code":"WLPERMATAC21","description":"WOODLOK PERMATAC 21KG","supplier":"Glue Guru Industrial Products","unit":"ea"},
]

# ── Pydantic models ──────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    transcript: str

class EntryCreate(BaseModel):
    item_code: str
    job: str
    supplier: str
    description: str
    cost_quantity: float
    unit: str
    comments: Optional[str] = None

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/products")
async def get_products():
    return PRODUCTS

@app.post("/api/match")
async def match_product(req: MatchRequest):
    """Use Claude to match voice transcript to product(s)."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    products_json = json.dumps(PRODUCTS)

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1000,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a stock management assistant for a construction company. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": f"""A worker has spoken this transcript: "{req.transcript}"

Here is the product catalogue (JSON):
{products_json}

Your job is to extract from the transcript:
1. The product(s) being referred to (match by name, partial name, or common nickname)
2. Job number (usually a number like "2847" or "job 123")
3. Quantity taken (a number)
4. Person's name (who took the goods) - this goes in comments

If the product is ambiguous (multiple matches), return all matches so the user can choose.

Respond ONLY with valid JSON in this exact format:
{{
  "matches": [
    {{"code": "...", "description": "...", "supplier": "...", "unit": "..."}}
  ],
  "job": "...",
  "quantity": null or number,
  "comments": "...",
  "ambiguous": true or false,
  "missing": ["list of fields not found in transcript, e.g. job, quantity, comments"]
}}

If a field is not mentioned in the transcript, set it to null and add it to missing[].
"""
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


@app.post("/api/entries")
async def create_entry(entry: EntryCreate):
    conn = await get_db()
    try:
        row = await conn.fetchrow("""
            INSERT INTO stock_entries (item_code, entry_date, job, supplier, description, cost_quantity, unit, comments)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """, entry.item_code, date.today(), entry.job, entry.supplier,
            entry.description, entry.cost_quantity, entry.unit, entry.comments)
        return dict(row)
    finally:
        await conn.close()


@app.get("/api/entries")
async def list_entries():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT * FROM stock_entries ORDER BY created_at DESC")
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@app.get("/api/export")
async def export_csv():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT item_code, entry_date, job, supplier, description, cost_quantity, unit, comments FROM stock_entries ORDER BY created_at ASC")
    finally:
        await conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Item Code", "Date", "Job", "Supplier", "Description", "Cost Quantity", "Unit", "Comments"])
    for r in rows:
        writer.writerow([r["item_code"], r["entry_date"], r["job"], r["supplier"],
                         r["description"], r["cost_quantity"], r["unit"], r["comments"] or ""])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=stock_export_{date.today()}.csv"}
    )

@app.delete("/api/entries/{entry_id}")
async def delete_entry(entry_id: int):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM stock_entries WHERE id = $1", entry_id)
        return {"ok": True}
    finally:
        await conn.close()

# Serve React frontend for all non-API routes
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
