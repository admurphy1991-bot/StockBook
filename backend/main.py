from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncpg, os, json, csv, io
from datetime import date, datetime
from zoneinfo import ZoneInfo
from openai import OpenAI

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
NZ_TZ = ZoneInfo("Pacific/Auckland")

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
                    gl_code TEXT,
                    worker_name TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_entries (
                    id SERIAL PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    entry_date DATE NOT NULL,
                    job TEXT NOT NULL,
                    worker_name TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            # Migrate: rename comments -> worker_name if old schema exists
            try:
                await conn.execute("""
                    ALTER TABLE stock_entries
                    RENAME COLUMN comments TO worker_name
                """)
                print("Migrated: renamed comments -> worker_name")
            except Exception:
                pass  # Column already renamed or doesn't exist
            await conn.close()
            print("Database ready.")
            return
        except Exception as e:
            print(f"DB not ready ({attempt+1}/10): {e}")
            time.sleep(3)

HAND_TOOLS = [
    "Tajima knife","Hammer","Hand saw","Spirit level","Crescent spanner",
    "Pliers","Chalk line","Hack saw","Tin snips","SINTEX R26:1 MS Cartridge Gun",
    "Trowel","Crack patch tool","Pinch bar","Crow bar","Pop riveter",
    "Spatula","Measuring tape","Metal file","Wire brush","Wood chisel",
    "Allen keys","Linbide scraper","Rubber mallet","Scissors","Window scraper",
    "Socket set","Hand spade","Hand shovel","Hand mallet","Hand pick","Digging bar",
]

# ── In-memory product/job store (seeded from DB config or defaults) ──────────

DEFAULT_PRODUCTS = [
    {"code": "060255A02R", "description": "BITUTHENE 5000 - ROLL", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "bitu five thousand, bituthene roll, bitu roll"},
    {"code": "AQUAKEM10", "description": "Aquakem 10L Pail", "supplier": "DGL", "unit": "LTR", "gl": "2000", "alias": "aquakem kit, aquakem ten litre, AK kit"},
    {"code": "067485A14R01", "description": "CSM E20 EMULSION 300g/sm JUSHI - ROL", "supplier": "DGL", "unit": "KG", "gl": "2000", "alias": "CSM emulsion roll, chopped strand mat roll, fibre emulsion roll"},
    {"code": "AQUAKEM8", "description": "Aquakem 8l kit", "supplier": "DGL", "unit": "KIT", "gl": "2000", "alias": "aquakem eight litre, AK eight litre kit, aquakem small kit"},
    {"code": "10543", "description": "WPM3000X 20M X 1.0M X 1.5MM ROLL", "supplier": "ARDEX", "unit": "ea", "gl": "2000", "alias": "WPM roll, waterproof membrane roll, three thousand roll"},
    {"code": "114665", "description": "Sika - Primer 3N (250ml)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika primer, sika three N, primer three N"},
    {"code": "130020", "description": "Xypex Concentrate 20kg", "supplier": "DEMDEN", "unit": "PAIL", "gl": "2000", "alias": "xipex concentrate, zypex concentrate, xypex twenty kilo"},
    {"code": "153729", "description": "Sika - Sikaflex AT Facade (600ml sausage)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex facade sausage, sika facade, sikaflex AT facade"},
    {"code": "153730", "description": "Sikaflex AT Facade 600ml White", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex facade white, sika facade white, AT facade white"},
    {"code": "153731", "description": "Sikaflex AT Facade 600ml Black", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex facade black, sika facade black, AT facade black"},
    {"code": "160020", "description": "Xypex Patch n Plug", "supplier": "DEMDEN", "unit": "KG", "gl": "2000", "alias": "xipex patch plug, zypex patch, xypex plug, patch and plug"},
    {"code": "185041", "description": "Sikalastic-152 (Part A 8kg) (Part B 25kg) KIT", "supplier": "SIKA", "unit": "KIT", "gl": "2000", "alias": "sikalastic one fifty two, sika liquid membrane kit, sika elastic membrane"},
    {"code": "20101", "description": "Soudal Soudaseal 240FC MS Adhesive 600ml Grey", "supplier": "MERZLTD", "unit": "ea", "gl": "2000", "alias": "soudal adhesive grey, soudaseal grey, soudal MS grey"},
    {"code": "24560", "description": "WPM117 Shelterstick 15m x 1m x 2mm - roll", "supplier": "ARDEX", "unit": "ea", "gl": "2000", "alias": "shelterstick roll, WPM one seventeen, ardex shelterstick"},
    {"code": "24954", "description": "K900BF 20kg bag", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "K nine hundred bag, ardex K900, K nine hundred BF"},
    {"code": "35538", "description": "BLACK PLASTIC ROLL 5m x 50m x 80 roll", "supplier": "TRADE", "unit": "EA", "gl": "2000", "alias": "black poly roll, black plastic roll, polythene roll, DPC roll"},
    {"code": "35933C", "description": "Tradextra S361 Silver Cloth Tape 48mm x 30m", "supplier": "TRADE", "unit": "ROLL", "gl": "2000", "alias": "silver cloth tape, tradextra silver tape, duct tape silver"},
    {"code": "405BOOM", "description": "Sika Boom 750ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika boom, expanding foam, sika expanding foam"},
    {"code": "435005", "description": "Sikadur Injectokit-TH 250g", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikadur inject kit, injection kit TH, sika inject"},
    {"code": "440627", "description": "Sika Blackseal Plus Elastic 20L", "supplier": "SIKA", "unit": "PAIL", "gl": "2000", "alias": "sika blackseal elastic, blackseal plus, sika black seal twenty litre"},
    {"code": "444906", "description": "Sika Thinner C Lt (20L)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika thinner twenty litre, sika C thinner large, thinner C big"},
    {"code": "444908", "description": "Sika Thinner C Lt (4 ltr)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika thinner four litre, sika C thinner small, thinner C small"},
    {"code": "452396", "description": "Sikadur UA 8L", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikadur UA eight litre, sika UA large, sikadur urethane eight litre"},
    {"code": "452399", "description": "Sika - Sikadur U.A 4 Lt", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikadur UA four litre, sika UA small, sikadur urethane four litre"},
    {"code": "497964", "description": "Sika AnchorFix-1 300ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika anchor fix, anchor fix one, sika anchor bolt"},
    {"code": "520310", "description": "Sikaflex 11 FC 310ml Black", "supplier": "SIKA", "unit": "ML", "gl": "2000", "alias": "sikaflex eleven FC black, sika eleven FC, sikaflex black cartridge"},
    {"code": "520472", "description": "Nailbond Premium 600ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "nailbond premium, nail bond sausage, construction adhesive sausage"},
    {"code": "536973", "description": "Sikaflex - 400¬†Fire¬†Grey¬†600ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex four hundred fire, sika fire sealant grey, fire rated sealant"},
    {"code": "551349", "description": "SikaTop Seal-107 Dryseal 5kg", "supplier": "SIKA", "unit": "KG", "gl": "2000", "alias": "sika top seal, dryseal, sika top one oh seven"},
    {"code": "551940", "description": "Sika MonoTop-438 R (25kg)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika monotop four thirty eight, monotop repair mortar, sika repair mortar"},
    {"code": "565413", "description": "Sikadur-52 Injection Normal 0.9l/kg", "supplier": "SIKA", "unit": "KIT", "gl": "2000", "alias": "sikadur fifty two, sika injection resin, crack injection resin"},
    {"code": "591755", "description": "Sikaflex MS 600ml White", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikaflex MS white, sika MS white sausage, sikaflex white six hundred"},
    {"code": "59300074", "description": "BluRez CS150 20kg", "supplier": "MBP", "unit": "ea", "gl": "2000", "alias": "bluerez CS one fifty, blurez powder, bluerez base"},
    {"code": "617759", "description": "Sikaflex PRO-3 Purform 600ml", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikaflex pro three, sika pro three purform, sikaflex PRO sausage"},
    {"code": "80151200", "description": "Turbo wave diamond blade dry/wet cured concrete", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "diamond blade, turbo wave blade, concrete cutting blade"},
    {"code": "82151204", "description": "125mm Disc. (diamond saw blade)", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "one twenty five diamond disc, small diamond blade, angle grinder blade"},
    {"code": "85681206", "description": "√∏5 turbo cup grinding wheel 12 segments", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "turbo cup wheel, grinding wheel, cup grinder wheel"},
    {"code": "92541", "description": "Sikaplug 5KG", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaplug, sika plug, hydraulic plug"},
    {"code": "ACE.5", "description": "ACETONE - 5L", "supplier": "NZFIBRE", "unit": "PAIL", "gl": "2000", "alias": "acetone five litre, acetone, solvent cleaner"},
    {"code": "ADCOR500T", "description": "ADCOR 500T WATERSTOP 6x5m CTN - CTN", "supplier": "ALLNEX", "unit": "ea", "gl": "2000", "alias": "adcor waterstop, adcor five hundred, waterstop strip"},
    {"code": "ALLAQ15", "description": "Aquadrain 15 18.9M¬≤ VAQUA15X", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "aquadrain, drainage mat, aquadrain fifteen"},
    {"code": "ALLBESA", "description": "Allco - Bentoseal 15kg", "supplier": "ALLCOWATER", "unit": "PAIL", "gl": "2000", "alias": "bentoseal, bento seal, bentonite seal"},
    {"code": "ALLBETG", "description": "Allco - Bentogrout 25kg", "supplier": "ALLCOWATER", "unit": "BAG", "gl": "2000", "alias": "bentogrout, bentonite grout, bento grout"},
    {"code": "ALLCET", "description": "Allco - Cetcoat 15kg", "supplier": "ALLCOWATER", "unit": "PAIL", "gl": "2000", "alias": "cetcoat, cet coat, allco cet"},
    {"code": "ALLDE4", "description": "Dermabit Extra - 4mm thick Polypropylene one side", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "dermabit extra, dermabit four mil, polyprop membrane"},
    {"code": "ALLRX101", "description": "RX101T Waterstop 6.1lm per roll", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh one waterstop, swelling waterstop, hydrophilic strip"},
    {"code": "ALLRX101DH", "description": "RX101DH waterstop delayed Hydration 5m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh one delayed hydration, delayed hydration waterstop"},
    {"code": "ALLSWTB", "description": "Allco - Swelltite Termination Bar Lm", "supplier": "ALLCOWATER", "unit": "LM", "gl": "2000", "alias": "swelltite bar, termination bar, swelltite termination"},
    {"code": "ALLVOCR", "description": "Allco - Voltex CR (5.4sqm roll)", "supplier": "ALLCOWATER", "unit": "M2", "gl": "2000", "alias": "voltex CR, voltex roll, bentonite membrane roll"},
    {"code": "ALLVODS", "description": "Allco - Voltex Super 66.6 DS", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "voltex super, voltex DS, bentonite super sheet"},
    {"code": "ALLVOLT", "description": "Voltex Roll (5.5m¬≤per roll) m¬≤", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "voltex, voltex sheet, bentonite sheet roll, carpet"},
    {"code": "ALLWSTG", "description": "Allco - Waterstoppage 25kg bag", "supplier": "ALLCOWATER", "unit": "BAG", "gl": "2000", "alias": "waterstoppage, water stoppage bag, allco grout, chicken shit"},
    {"code": "ALSANMASTIC/2200", "description": "ALSAN MASTIC 2200 SEALANT (310ML/CARTRIDGE)", "supplier": "EQUUS", "unit": "ea", "gl": "2000", "alias": "alsan mastic, alsan two two hundred, alsan sealant cartridge"},
    {"code": "ARD100FT", "description": "Ardex - Flashing Tape 4.7m x 100mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "ardex flashing tape, flashing tape one hundred, ardex tape roll"},
    {"code": "ARD150DT", "description": "Ardex - Uncured Detail Tape 30.4m x 150mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "ardex detail tape, uncured detail tape, ardex one fifty tape"},
    {"code": "ARD15DG", "description": "Ardex - Butynol Dv Grey 17.86m x1.4m x1.5mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "butynol grey, ardex butynol grey, grey rubber membrane roll"},
    {"code": "ARD15MB", "description": "Ardex - Butynol Black 17.86m x 1.4m x 1.5mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "butynol black, ardex butynol black, black rubber membrane roll"},
    {"code": "ARD50ST", "description": "Ardex - Butynol Seam Tape 30.4m x 50mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "butynol seam tape, ardex seam tape, rubber seam tape"},
    {"code": "ARDA38", "description": "Ardex - A38 20kg bag (Aust)", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "ardex A thirty eight, A38 bag, ardex patch mortar"},
    {"code": "ARDA46", "description": "Ardex - A46 20kg bag", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "ardex A forty six, A46 bag, ardex leveller"},
    {"code": "ARDAD", "description": "Ardex - WA98 Adhesive 20L pail", "supplier": "ARDEX", "unit": "PAIL", "gl": "2000", "alias": "ardex WA ninety eight adhesive, ardex adhesive pail, WA98 glue"},
    {"code": "ARDOPT", "description": "Ardex - Optima 40kg", "supplier": "ARDEX", "unit": "KIT", "gl": "2000", "alias": "ardex optima, optima forty kilo, ardex flexible membrane"},
    {"code": "ARDP51", "description": "Ardex - P51 5L bottle", "supplier": "ARDEX", "unit": "PAIL", "gl": "2000", "alias": "ardex P fifty one, P51 primer, ardex primer bottle"},
    {"code": "ARDSAND", "description": "Ardex - ARDEX Engineered Sand 20kg Bag", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "ardex sand, engineered sand, ardex aggregate"},
    {"code": "ARDST", "description": "Ardex - Substrate Joint Tape 50mx25mm 36roll/ctn", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "ardex joint tape, substrate tape, ardex seam tape roll"},
    {"code": "ATDUCT", "description": "Attwoods - Silver Cloth Tape per roll", "supplier": "ATTWOOD", "unit": "ROLL", "gl": "2000", "alias": "attwoods duct tape, silver cloth tape, attwoods tape"},
    {"code": "B10019A01R01", "description": "REINFORCING TAPE 100mm Roll", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "reinforcing tape, mesh tape, hundred mil tape roll"},
    {"code": "B1BTB2P", "description": "BITUTHENE B2 PRIMER (1.00 x 25 Lt)", "supplier": "ALLNEX", "unit": "PAIL", "gl": "2000", "alias": "bituthene B2 primer, bitu primer, bituthene primer twenty five litre"},
    {"code": "B1BTLQM", "description": "BITUTHENE LIQUID MEMBRANE LM3000 (5.7LT)", "supplier": "ALLNEX", "unit": "ea", "gl": "2000", "alias": "bituthene liquid membrane, bitu liquid membrane, LM three thousand"},
    {"code": "B1BTM", "description": "BITUTHENE MASTIC (12.00 x 300 ml tube)", "supplier": "ALLNEX", "unit": "ea", "gl": "2000", "alias": "bituthene mastic, bitu mastic, bituthene tube"},
    {"code": "B1BTSSM", "description": "Swellseal Mastic WA (12 per box)", "supplier": "ALLNEX", "unit": "ea", "gl": "2000", "alias": "swellseal mastic, swell seal mastic, hydrophilic mastic"},
    {"code": "B1SOGJ", "description": "Soprema Granules 1kg", "supplier": "ALLNEX", "unit": "KG", "gl": "2000", "alias": "soprema granules, bitumen granules, roofing granules"},
    {"code": "BIBT3000", "description": "Bituthene 3000 (1.00 x 20m Roll)", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "bituthene three thousand, bitu three thousand, bitu roll twenty metre"},
    {"code": "CA20P", "description": "CA20P Black - Cartridge 310 ML", "supplier": "ARDEX", "unit": "ea", "gl": "2000", "alias": "CA twenty P black, black cartridge, allco black cartridge"},
    {"code": "CBFIL30", "description": "Bitumen Fillet 30mm x 30mm x 1100mm", "supplier": "ALLCOWATER", "unit": "ea", "gl": "2000", "alias": "bitumen fillet thirty mil, small bitu fillet, bitu corner fillet"},
    {"code": "CBW426157", "description": "IMPRABOARD¬†¬Æ¬†WHITE¬†680GSM 1200 x 4mm (10 sheets per bag)", "supplier": "MULF", "unit": "SHEET", "gl": "2000", "alias": "impraboard white, protection board white, white foam board"},
    {"code": "COREFL18", "description": "Allguard Coreflute 1800 x 1150 x 4mm", "supplier": "ALLCOWATER", "unit": "SHEET", "gl": "2000", "alias": "coreflute, protection board, allguard coreflute"},
    {"code": "CSW", "description": "BluRez CWS Base 20kg Drum", "supplier": "BLUEYNZ", "unit": "ea", "gl": "2000", "alias": "bluerez base, CWS base drum, blurez drum"},
    {"code": "D1", "description": "Newton Basedrain - 2m Length", "supplier": "NEWSYSLTD", "unit": "M", "gl": "2000", "alias": "newton basedrain, newton drain two metre, newton channel"},
    {"code": "D21", "description": "Newton Basedrain - Sump Connector", "supplier": "NEWSYSLTD", "unit": "ea", "gl": "2000", "alias": "newton sump connector, basedrain sump, newton sump"},
    {"code": "D30", "description": "Newton Basedrain - Inspection PortBase - 204 mm x 60 mm opening", "supplier": "NEWSYSLTD", "unit": "ea", "gl": "2000", "alias": "newton inspection port, basedrain inspection, newton port"},
    {"code": "D6", "description": "Newton Basedrain - Swept Corner", "supplier": "NEWSYSLTD", "unit": "ea", "gl": "2000", "alias": "newton swept corner, basedrain corner, newton corner piece"},
    {"code": "DDR314200", "description": "R SERIES CARBIDE 14MMX200MM 01260", "supplier": "RAMSET", "unit": "ea", "gl": "2000", "alias": "carbide bit fourteen mil, ramset carbide, masonry drill bit"},
    {"code": "DEXX/GR/15", "description": "Chevaline Dexx", "supplier": "EQUUS", "unit": "ea", "gl": "2000", "alias": "chevaline dexx, dexx primer, dexx treatment"},
    {"code": "EXPOLY", "description": "Expol - Polystyrene Sheet 1.8x1.2", "supplier": "", "unit": "EA", "gl": "2000", "alias": "polystyrene sheet, expol sheet, poly insulation board"},
    {"code": "GELG4", "description": "Gel G4", "supplier": "CASH", "unit": "ea", "gl": "2000", "alias": "gel G four, G4 gel, glue gel"},
    {"code": "GLASS/300", "description": "Fibreglass Mat 300 GSM", "supplier": "EQUUS", "unit": "M", "gl": "2000", "alias": "fibreglass mat, chop strand mat, three hundred fibre mat, CSM"},
    {"code": "HAP19520", "description": "AQUENCE BG P195 Adhesive 21kg Pail", "supplier": "GLUE", "unit": "ea", "gl": "2000", "alias": "aquence adhesive, BG P195 glue, contact adhesive pail"},
    {"code": "M1000035", "description": "Bitumen Sealant 300ml", "supplier": "MERZLTD", "unit": "ea", "gl": "2000", "alias": "bitumen sealant, bitu sealant cartridge, black sealant"},
    {"code": "NUA101", "description": "Aquaguard 101 (A & B, 10ltr Kit) per ltr", "supplier": "DGL", "unit": "LTR", "gl": "2000", "alias": "aquaguard one oh one, AG one oh one per litre, aquaguard litre"},
    {"code": "NUR3PM", "description": "Nuraply Slate Cap Sheet", "supplier": "NURA", "unit": "EA", "gl": "2000", "alias": "nuraply slate cap, cap sheet slate, nuraply cap roll"},
    {"code": "NURA3PC", "description": "Nuraply 3PC", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "nuraply three PC, three ply cap sheet, nuraply cap"},
    {"code": "NURFIL", "description": "Bitumen Fillet 1.2m length", "supplier": "EQUUS", "unit": "ea", "gl": "2000", "alias": "bitumen fillet, bitu fillet, nura fillet"},
    {"code": "NURVB", "description": "Nuraply Alu Vapour Barrier", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "nuraply vapour barrier, alu vapour barrier, foil vapour barrier"},
    {"code": "PE751", "description": "TERMINATION BAR 2.4M(FOLDED)", "supplier": "NURA", "unit": "M", "gl": "2000", "alias": "termination bar, term bar, folded term bar"},
    {"code": "PFRO002", "description": "PFROD 06mm dia. 50m Coil", "supplier": "KARSTEN", "unit": "ROLL", "gl": "2000", "alias": "backing rod six mil, PF rod six, foam backer rod small"},
    {"code": "PFRO005", "description": "PF Rod 8mm 50m Coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod eight mil, PF rod eight, foam backer rod eight"},
    {"code": "PFRO008", "description": "PF Rod 10mm 50m Coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod ten mil, PF rod ten, foam backer rod ten"},
    {"code": "PFRO014", "description": "PF Rod 15mm 50m Coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod fifteen mil, PF rod fifteen, backer rod fifteen"},
    {"code": "PFRO015", "description": "PF Rod 15mm 100m coil (per roll)", "supplier": "KARSTEN", "unit": "ROLL", "gl": "2000", "alias": "backing rod fifteen large roll, PF rod fifteen hundred, backer fifteen roll"},
    {"code": "PFRO016", "description": "PF Rod 20mm dia 20m coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod twenty mil, PF rod twenty, foam backer twenty"},
    {"code": "PFRO017", "description": "PF Rod 20mm 60m coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod twenty long roll, PF rod twenty sixty, backer twenty roll"},
    {"code": "PFRO018", "description": "PF Rod 25mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod twenty five, PF rod twenty five, backer twenty five"},
    {"code": "PFRO019", "description": "PF Rod 25mm 25m length (per roll)", "supplier": "KARSTEN", "unit": "ROLL", "gl": "2000", "alias": "backing rod twenty five roll, PF rod twenty five coil, backer twenty five roll"},
    {"code": "PFRO020", "description": "PF Rod 30mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod thirty, PF rod thirty, backer rod thirty"},
    {"code": "PFRO021", "description": "PF Rod 30mm 25m length (per roll)", "supplier": "KARSTEN", "unit": "ROLL", "gl": "2000", "alias": "backing rod thirty roll, PF rod thirty coil, backer thirty roll"},
    {"code": "PFRO022", "description": "PF Rod 40mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod forty, PF rod forty, backer rod forty"},
    {"code": "PFRO023", "description": "PF Rod 50mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod fifty, PF rod fifty, backer rod fifty"},
    {"code": "PREPRUFE30", "description": "PREPRUFE 300R PLUS - ROL 1.2 x 30m", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "preprufe three hundred, preprufe roll, pre-applied waterproofing roll"},
    {"code": "RF124", "description": "Nuraply 3PB Basesheet (10 m x 1m x 3mm roll) 25/p", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "nuraply basesheet, three PB basesheet, nura base roll"},
    {"code": "RF169", "description": "IKOprotect MS DETAIL 1LT (1.5KG)", "supplier": "NURA", "unit": "LTR", "gl": "2000", "alias": "IKO protect, MS detail liquid, iko one litre"},
    {"code": "RF170", "description": "KO hybrytech MS DETAIL 1LT [BLACK]", "supplier": "NURA", "unit": "LTR", "gl": "2000", "alias": "KO hybrytech black, MS detail black, hybrytech liquid"},
    {"code": "RF751", "description": "MS SEALANT 415gm BLACK FIXALL 220", "supplier": "NURA", "unit": "ea", "gl": "2000", "alias": "MS sealant black, fixall sealant, black MS sealant"},
    {"code": "SDM06030SS", "description": "SHURE DRIVE SS 6X30MM 01380", "supplier": "RAMSET", "unit": "ea", "gl": "2000", "alias": "shure drive screw, stainless screw six by thirty, SS timber screw, suredrive, shore drive, shore drive screw, sure drive, shure drive stainless, shore drive stainless"},
    {"code": "SI11FC", "description": "Sika - Sikaflex11 FC purform", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex eleven FC, sika eleven FC purform, sikaflex joint sealant"},
    {"code": "SI212", "description": "Sika - 212 Grout 25kg", "supplier": "SIKA", "unit": "BAG", "gl": "2000", "alias": "sika two twelve grout, sika grout, two twelve bag"},
    {"code": "SI31", "description": "Sikadur-31 CF Normal kg", "supplier": "SIKA", "unit": "KG", "gl": "2000", "alias": "sikadur thirty one, sika thirty one, epoxy adhesive sikadur"},
    {"code": "SI412", "description": "Sika - Monotop 412 bag", "supplier": "SIKA", "unit": "BAG", "gl": "2000", "alias": "sika monotop four twelve, monotop four twelve, sika repair bag"},
    {"code": "SI42", "description": "Sikadur-42 (15KG KIT)", "supplier": "SIKA", "unit": "KIT", "gl": "2000", "alias": "sikadur forty two, sika forty two kit, epoxy grout kit"},
    {"code": "SI910", "description": "Sika Monotop 910N Primer 4kg", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika monotop nine ten, monotop primer, nine ten primer"},
    {"code": "SIBS", "description": "Sika Blackseal cartridge", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika blackseal cartridge, blackseal small, sika black seal tube"},
    {"code": "SIINLV250", "description": "Sikadur Injectokit- LV 250", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikadur inject LV, low viscosity inject kit, sika LV inject"},
    {"code": "SISW53", "description": "Sika Swell A 2005 20nn x 5mm x 20m", "supplier": "SIKA", "unit": "ROLL", "gl": "2000", "alias": "sika swell A, swell strip twenty by five, hydrophilic strip sika"},
    {"code": "SISWP", "description": "SikaSwell-P 2010H 20mm x 10mm x 10m", "supplier": "SIKA", "unit": "ROLL", "gl": "2000", "alias": "sika swell P, swell profile twenty by ten, sika swellable profile"},
    {"code": "SISWS2", "description": "Sika Swell S2 600ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika swell S2, swell sausage, hydrophilic sausage"},
    {"code": "SXR121S", "description": "Professional Sausage Gun", "supplier": "GLUE", "unit": "ea", "gl": "2000", "alias": "sausage gun, twelve to one gun, small sausage gun"},
    {"code": "SXR261S", "description": "SINTEX R26:1S MS Sausage Gun", "supplier": "GLUE", "unit": "ea", "gl": "2000", "alias": "sintex sausage gun, big sausage gun, twenty six to one gun"},
    {"code": "TK102", "description": "NURAFLUX PRIMER (QD) 25l", "supplier": "NURA", "unit": "PAIL", "gl": "2000", "alias": "nuraflux primer, QD primer, quick dry primer twenty five litre"},
    {"code": "TK109", "description": "Bitumen Trianglular Fillet 1.2m", "supplier": "NURA", "unit": "EA", "gl": "2000", "alias": "triangular bitu fillet, bitu triangle fillet, corner fillet"},
    {"code": "TK115B", "description": "NURADRAIN GF (2m X 20m)", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "nuradrain, drainage board, nuradrain roll"},
    {"code": "TK151", "description": "Bituthene Liquid Membrane (Kit)", "supplier": "NURA", "unit": "ea", "gl": "2000", "alias": "bituthene liquid membrane kit, bitu LM kit, liquid membrane kit"},
    {"code": "TK153", "description": "PREPRUFE 300R PLUS (31.15M)", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "preprufe three hundred plus, preprufe thirty metre, preprufe roll"},
    {"code": "TK157", "description": "PREPRUFE LT TAPE 100mm (15M)", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "preprufe LT tape hundred mil, preprufe flashing tape, LT tape"},
    {"code": "TK160", "description": "PREPURFE LT DETAIL TAPE 50mm (15M)", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "preprufe detail tape fifty, LT detail tape, preprufe small tape"},
    {"code": "TRAXX2000/20", "description": "TRAXX 2000", "supplier": "EQUUS", "unit": "M", "gl": "2000", "alias": "traxx two thousand, traxx drainage, dimple membrane traxx"},
    {"code": "VCS600", "description": "Cetseal (20oz) 600mls Sausage - Polymeric Sealant/Adhesive", "supplier": "ALLCOWATER", "unit": "600ML", "gl": "2000", "alias": "cetseal sausage, polymeric sealant sausage, cet seal"},
    {"code": "VCTX", "description": "Volclay Coretex (9.29m¬≤) roll", "supplier": "", "unit": "ROLL", "gl": "2000", "alias": "volclay coretex, voltex coretex, coretex roll"},
    {"code": "VRX10210", "description": "Allco - RX102 Waterstop 10.2m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh two waterstop, RX102 strip, allco waterstop ten metre"},
    {"code": "VST50", "description": "DPM Tape Allsheet 48mm x 30 m Red", "supplier": "ALLCOWATER", "unit": "M", "gl": "2000", "alias": "DPM tape red, allsheet tape red, red DPC tape"},
    {"code": "VSTPOL10.2", "description": "Swelltite Polish 3000 10.2m Roll", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "swelltite polish, polish three thousand, swelltite roll"},
    {"code": "VVS500", "description": "Allsheet 500 micron non hydrostatic DPM PE 4x25m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "allsheet DPM, five hundred micron DPM, damp proof membrane sheet"},
    {"code": "WLPERMATAC21", "description": "WOODLOK PERMATAC 21KG", "supplier": "GLUE", "unit": "ea", "gl": "2000", "alias": "woodlok permatac, permatac adhesive, woodlok glue"},
    {"code": "11204", "description": "Pulsa washer containers (box of 1,000)", "supplier": "RAMSET", "unit": "Bag", "gl": "2000", "alias": "pulsa washer, washer containers, ramset washers"},
    {"code": "P8C630", "description": "30 mm nails (box of 500)", "supplier": "RAMSET", "unit": "Bag", "gl": "2000", "alias": "thirty mil nails, P8C630, ramset thirty nails"},
    {"code": "P8HC627", "description": "27 mm nails (box of 500)", "supplier": "RAMSET", "unit": "Bag", "gl": "2000", "alias": "twenty seven mil nails, P8HC627, ramset twenty seven nails"},
]

DEFAULT_JOBS = [
    "2306 - Warranty Work - Sansom Construction Systems Ltd",
    "2309 - Athens Road 1/59, Onehunga",
    "2310 - Riddell Rd 283, Glendowie",
    "2311 - Speights Rd 8, Kohimarama",
    "2312 - Glendowie Road 12a",
    "2313 - ILD Australia Pty",
    "17221 - WTJO Gt Nth Rd 1405 Waterview",
    "19239 - Sansom Concrete Repairs",
    "R9999 - Pre-Investigation / Quote / Admin Time",
    "R200 - Stock - Concrete Repairs",
    "21148 - CRL Mined Tunnels *",
    "R344 - Concrete Staff Training / Health & Safety / Meetings",
    "22168 - Manukau Health Park Redevelopment",
    "22196 - CRL Aotea - Facade & Seismic",
    "R444 - Parkwood Apartments",
    "23113 - Hapua Project 15A - Warm Roof",
    "R502 - Mercy Ascot Road Phase 1",
    "23159 - AIAL - WP1 - Terminal Integration",
    "S34000 - Sansom Construction Systems LTD",
    "S9000 - Admin Time - Sansom Ltd",
    "S34042 - Half Moon Bay , 25 Thurston Place - Waterproofing",
    "23300 - Newton Systems",
    "S34055 - Rehab Plus, C03, Pt Chev - R0561132",
    "S34065 - Auckland Airport Domestic Processor Pier & FLB Tanking Works",
    "23245 - AATH Facade Package",
    "R579 - Starship Atrium SP3 - Grafton Rd,125 Unit 1 : Composite Strengthening",
    "S34131 - Lorne Street - Student Accommodation",
    "S34160 - Precinct Apartments - 6-8 Lorne Street Auckland CBD",
    "S34162 - Westpoint Drive 32, HV1 (Ext) Hobsonville Data Centre",
    "S34182 - AIAL Domestic Processor - Headhouse",
    "S34183 - Waitakere Hospital - Tanking",
    "S34194 - Project Waka - Stage 2 Waterproofing",
    "S34197 - Te Puaruruhau L3, 99 Grafton Road",
    "R626 - Mt Eden 101, Concrete Office / Yard",
    "S34228 - JTFJ Costs Mt Eden Road 101",
    "S34248 - Mayfair Retirement Village - Oteha Valley 14",
    "S34266 - Maintenance / Membrane and Admininistration",
    "R680 - IKEA Sealant Works",
    "S34323 - Staff Appreciation",
    "S2301 - Pre-Investigation / Quotes",
    "R692 - Hangar 4 - Sikagard 62 to Flame Trap",
    "S34354 - Drury / Paerātā Rail Station Main Works – Seismic Joints",
    "S34359 - Pipe Penetration Works",
    "S34360 - Mt Eden Road 101 -Building Maintenance",
    "S34371 - Newton Systems Limited",
    "S34443 - Fisher & Paykel Headquarters",
    "S34444 - UoA B505, Park Road 85 - Basement Carkpark Leaks",
    "S34466 - Queen Street 256 Student Accommodation",
    "S34467 - Albert Street 99",
    "S34477 - Summerset St Johns - Building G - Excavation, Inground Plumbing and Tanking",
    "R776 - Arthurs Pass, Kiwirail Tunnel Repairs",
    "S34482 - Orams Commercial Buildings B1A & B1B",
    "S34490 - Marine Parade 13 - Tanking",
    "S34496 - HV.2 Hobsonville Data Centre - Joint Sealant",
    "R784 - ADHB, Park Road 2 -  Concrete Remediation Works",
    "101 - Rates",
    "S34528 - Murphy House Stage 2 - Tara Iti",
    "S200STOCK - Sansom Ltd Stock Purchases",
    "S34539 - The Hill Ellerslie - Warm Roof",
    "S34543 - Fisher & Paykel - Garage Building",
    "S34545 - MPI PHEC- Southbase Construction",
    "S34555 - AAG Wellesley Street East, Auckland CBD - Storage Room Water Ingress",
    "24110 - AIAL WP1 - Tanking",
    "S34577 - Carlaw Park Student Village 4",
    "S34578 - Zone 23 - Edwin Street 23",
    "S34582 - Orams Marine Carpark Refurbishment",
    "S34591 - The Hill - Building B",
    "S34593 - Civic Theatre - Basement Remedial Waterproofing",
    "S34611 - Tools & PPE",
    "S19239 - Sansom Concrete Repairs Ltd",
    "S2314 - ILD (NZ) LTD",
    "S34623 - Facade/Jointing - Small Sales",
    "S34624 - Membrane - Small Sales",
    "S34625 - Maintenance - Small Sales",
    "S34626 - Tanking - Small Sales",
    "S2302 - Staff Training / Health & Safety / Meetings",
    "S34631 - University of Auckland B230 Project",
    "R878 - Les Mills Victoria Street West Concrete Investigation",
    "S34648 - Hobsonville Road 98 - Project 2",
    "S34672 - Site 6 - Basement Inspection",
    "S34673 - Ireland Street 44",
    "S34683 - FPH B5.1 - Tanking",
    "S34688 - Auckland City Mission - Shade Sail post detailing",
    "R937 - The Hill - Belvedere, Screeding",
    "R938 - Hockey Centre, Rosedale, Albany - Remedial Works",
    "S34729 - Rockstar Warehouse Rebuild",
    "R0001NOJOB - Sansom Concrete Repairs - NONJOBRELEATED",
    "R967 - Fort Street, Auckland - Facade Concrete Remedial Project",
    "R980 - 33 Federal Sansom Crack injection",
    "S34754 - Sansom Maintenance - Investigation Costs",
    "S34763 - Jervois Road 41",
    "S34766 - Alberton Avenue 57",
    "R1001 - Gorst Lane  - Wall and Carpark Pillar Remedials",
    "S34772 - Sarsfied, 81 -  Waterproofing",
    "S34774 - H47 Apartments - Exterior Main Roof Top Entrance area & Stair works",
    "R1008 - Orams Marine Footpath Saw Cut",
    "S34808 - 147 Captain Springs Road  -  Aquakem Coating to walls",
    "S34820 - Parnell Road 339 - Tanking Design",
    "S34822 - Fisher & Paykel Healthcare B5.1 - Seismic Joint",
    "S34823 - Faulder Avenue 21",
    "R1028 - 22 Fleet Street Structural Investigation",
    "R1034 - Horizon Apartment Basement Repair Works",
    "R1036 - FNDC Kaitaia Awaroa Road Repairs to Bridges D42 & D47",
    "S34846 - 74 - 76 Grafton Road - Grafton Meditel Hotel",
    "R1046 - Carbodur NSM BC12 Rods for St Lukes Gardens",
    "R1048 - Remuera Road, 3/452 - Concrete Repairs",
    "S34868 - ADHB - Waterproofing 91 Pipes",
    "S34870 - MPI PHEC - Membrane Roofing and Emseal Package",
    "S34872 - Snells Beach Waste Water Treatment Plant Injection",
    "S34874 - Air NZ Hangar 4 (JFC) - Flame Trap 4",
    "S34884 - Remuera Road 454 - Deck Waterproofing",
    "S34889 - 985 Mount Eden Road - Kingsway Connection (A01/A02) Lift",
    "S34897 - Glen Innes, Te Mahia & Takanini Station - Pedestrian Crossings Waterproofing",
    "S34902 - AIAL TH01 – Remedial Works",
    "S34903 - Glanville Terrace 42 - Remedial Work",
    "R1073 - Air NZ Hangar 2 Re-life",
    "S34910 - Broadway 255, Newmarket, Auckland -  Canopy Remediation works",
    "S34914 - Waitemata (Britomart) Train Station Escalators",
    "R1090 - Locarno Avenue, Sandringham, 23 -  Retaining Wall Repair",
    "S34931 - Starship Childrens Hospital - PC3 Atrium Infill, duct Extract",
    "R1103 - 454 Remuera - Concrete cut nib, screed and core drill",
    "R1104 - Stanmore Watercare Pump Station Investigation",
    "S34950 - Painton Road,5, Silverdale -  Install Membrane Plinths",
    "R1112 - Bridge 43 MSL 96.765km. - Impact Beam Replacement",
    "S34956 - Beresford Square 16-18",
    "R1137 - Kauri Drive, 21, Waiuku - Maintenance",
    "S34972 - Orams Existing Carpark - Sealant Works",
    "S34975 - Station M - 21 Manapau Street, Meadowbank - Precast Sealant",
    "S34981 - Murray Halberg Retirement Village - Remedial Waterproofinga",
    "R1149 - Gabador Place, 34 - Concrete Repairs and Coating",
    "R1150 - Holcim, Onehunga Harbour Road, 57 -  Concrete Repairs",
    "R1152 - Laminex  - Centennial Drive, 177, Taupo – Concrete Repairs",
    "R1155 - Concrete Repairs - Small Sales",
    "S34990 - Tamaki Drive 256 - Tanking Design",
    "R1159 - Middlemore Hospital,Hospital Road 100 , Otahuhu, Auckland–Concrete Repairs",
    "S34996 - Three Kings - Maintenance Annual inspections",
    "R1172 - Kirkpatrick Building, Patiki Road - Floor Repairs",
    "S35013 - CDC HV2.2 - Roofing",
    "S35015 - Skycity Membrane Remedial Works",
    "S35021 - PaknSave Albany",
    "R1184 - Waterview Tunnel Southern Vent Building Topping Slab",
    "R1186 - Northridge Apartments, Stanwell Street Parnell , 28",
    "R1194 - Stanbeth Building, Commerce Street,6 - Crack Repairs",
    "R1195 - Jarden House Comm Bay B3 Ramp Repair",
    "S35035 - BEKS2025 Limited",
    "S35036 - Bledisloe Cruise Terminal - Tanking",
    "R1206 - Fort Street Wilson Car Park 34 Shortland Street",
    "R1211 - Waka - Post Contract Works",
    "S35047 - 308-310 Great North Road – Seismic Joints",
    "S35048 - Racecourse Parade, 26  -  Sansom Annual Maintenance Inspection",
    "S35049 - Greenside Rd, 101 - Annual Maintenance Inspection",
    "R1213 - Saint Paul Street, 47, Auckland Central -  Northern Façade Concrete Wall Repair",
    "S35053 - TVNZ - Membrane Repairs",
    "S35054 - 13-15 College Hill Police Station",
    "S35055 - 60E Sentinel Road, Herne Bay - Roof Waterproofing",
    "R1218 - TVNZ - Concrete Repairs",
    "S35061 - AON Centre, Custom Street 21-29 - Waterproofing detailing",
    "S35067 - Northridge Apartments - 28 Stanwell Street",
    "S35068 - Warranty Work - Sansom Ltd",
    "S35074 - Pipe Penetrations",
    "S35077 - Ascot Office Park - 93-95 Ascot Ave, Greenlane",
    "S35078 - Gibbons Road, 8B -  Membrane Remedial Works",
    "S35079 - 22 Viaduct Harbour Avenue, Auckland CBD - 22VHA B2 Carpark Investigation",
    "S35086 - College Hill Police Station - Leak Investigation",
    "R1247 - Massey Univeristy - Drossbach Infill",
    "S35087 - 6 Pekapeka Place, Raglan - Tanking Remediation Consultant",
    "R1248 - Bledisloe Cruise Terminal",
    "S35088 - 19 Ngaiwi St, Orakei - Roof Membrane",
    "S35089 - Walmer Road, 9, Point Chevalier, Auckland -  Roof membrane remedial works",
    "R1270 - Kawakawa Tank Repairs",
    "S35106 - 109 Seaview Road, Remuera",
    "S35107 - St Cuthberts College Information Centre - Maintenance Remedial Works",
    "R1271 - Kaitaia Hospital Stage 2 Crack Repair",
    "R1274 - Tunnel 18 Porootaroa NIMT Ham Sth",
    "R1275 - 161 Ocean Beach Road Mt Maunganui - CombiFlex",
    "S35110 - Gould Street 9 - Russell (Beach House)",
    "S35111 - Gould Street 7 - Russell (Boat House)",
    "S35113 - 8 Shiperds Avenue, Epsom - Remedial roof works",
    "S35114 - 41C Sandpiper Ave- TPO Roof Membrane",
    "R1279 - Sentinel Road, 60E, Herne Bay - Screeding",
    "S35120 - SkyCity I Group Roof -  Membrane Remedial Works",
    "S35121 - Grand Hotel, Federal Street, L6 - Exterior Canopy Membrane Remedial Works",
]
# In-memory store — overwritten by webhook sync
_products = list(DEFAULT_PRODUCTS)
_jobs = list(DEFAULT_JOBS)

# ── Webhook: sync products & jobs from Google Sheets (published CSV) ─────────

class WebhookSync(BaseModel):
    products_csv_url: Optional[str] = None
    jobs_csv_url: Optional[str] = None
    # OR post inline data directly
    products: Optional[list] = None
    jobs: Optional[list] = None

@app.post("/api/webhook/sync")
async def webhook_sync(payload: WebhookSync):
    """
    Sync product list and/or job list from external source.

    Two modes:
    A) Google Sheets published-as-CSV URLs:
       { "products_csv_url": "https://docs.google.com/...", "jobs_csv_url": "..." }

    B) Inline JSON arrays (useful for manual pushes or other integrations):
       { "products": [...], "jobs": [...] }

    Products CSV must have columns: code, description, supplier, unit, gl, alias
    Jobs CSV must have a single column: job
    VOs CSV must have columns: Job Number, Variation Order Number
    """
    global _products, _jobs
    import httpx

    updated = []

    # ── Products ──
    if payload.products_csv_url:
        async with httpx.AsyncClient() as client:
            r = await client.get(payload.products_csv_url, timeout=15)
            r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        new_products = []
        for row in reader:
            if row.get("code"):
                new_products.append({
                    "code": row.get("code", "").strip(),
                    "description": row.get("description", "").strip(),
                    "supplier": row.get("supplier", "").strip(),
                    "unit": row.get("unit", "").strip(),
                    "gl": row.get("gl", "").strip(),
                    "alias": row.get("alias", "").strip(),
                })
        if new_products:
            _products = new_products
            updated.append(f"products: {len(_products)} loaded from CSV")
    elif payload.products:
        _products = payload.products
        updated.append(f"products: {len(_products)} loaded inline")

    # ── Jobs ──
    if payload.jobs_csv_url:
        async with httpx.AsyncClient() as client:
            r = await client.get(payload.jobs_csv_url, timeout=15)
            r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        new_jobs = []
        for row in reader:
            val = row.get("job") or row.get("Job") or next(iter(row.values()), "")
            if val.strip():
                new_jobs.append(val.strip())
        if new_jobs:
            _jobs = new_jobs
            updated.append(f"jobs: {len(_jobs)} loaded from CSV")
    elif payload.jobs:
        _jobs = [str(j).strip() for j in payload.jobs if str(j).strip()]
        updated.append(f"jobs: {len(_jobs)} loaded inline")


    if not updated:
        return {"ok": False, "message": "Nothing to update — supply products_csv_url, jobs_csv_url, products, or jobs"}

    return {"ok": True, "updated": updated}

@app.get("/api/webhook/status")
async def webhook_status():
    """Returns how many products and jobs are currently loaded."""
    return {
        "products_count": len(_products),
        "jobs_count": len(_jobs),
        "source": "live (last synced via webhook)" if _products is not DEFAULT_PRODUCTS else "default (hardcoded)"
    }

# ── Standard data endpoints ───────────────────────────────────────────────────

class MatchRequest(BaseModel):
    transcript: str

class EntryCreate(BaseModel):
    item_code: str
    job: str
    supplier: str
    description: str
    cost_quantity: float
    unit: str
    gl_code: Optional[str] = None
    worker_name: Optional[str] = None

@app.get("/api/products")
async def get_products():
    return _products

@app.get("/api/jobs")
async def get_jobs():
    return _jobs


@app.post("/api/match")
async def match_product(req: MatchRequest):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    products_json = json.dumps(_products)
    jobs_json = json.dumps(_jobs)
    tools_json = json.dumps(HAND_TOOLS)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a stock management assistant for a NZ construction company. Always respond with valid JSON only."},
            {"role": "user", "content": f"""A worker said: "{req.transcript}"

PRODUCTS (match by description, code, or alias):
{products_json}

JOBS (match job number or name):
{jobs_json}

HAND TOOLS (match by name, allow for misspellings and abbreviations):
{tools_json}

Extract everything mentioned:
1. Stock products - match against PRODUCTS list using description, code, or alias. Each product gets its own entry with quantity.
2. Tools - match any tools mentioned against the HAND TOOLS list. A "blade" could match "Hack saw" or a cutting tool - use best judgement.
3. Job - match closest from job list by number or name
4. Worker name (who took the items)

Return JSON:
{{
  "matches": [{{"code":"...","description":"...","supplier":"...","unit":"...","gl":"...","quantity":null}}],
  "tools": ["exact name from HAND TOOLS list"],
  "job": "exact match from job list or null",
  "job_suggestions": ["up to 3 close matches if ambiguous"],
  "worker_name": "...",
  "ambiguous": false,
  "missing": []
}}

- If multiple stock products mentioned, include all in matches array, each with their own quantity
- If no quantity stated for a product, set quantity to null and add "quantity" to missing
- Put null and add to missing[] for job or worker_name if not in transcript
- Only include tools that are a clear match to the HAND TOOLS list
- If ONLY tools are mentioned (no stock products), return matches: [] and do NOT add "product" or "quantity" to missing[]
"""}
        ]
    )
    return json.loads(response.choices[0].message.content.strip())

@app.post("/api/entries")
async def create_entry(entry: EntryCreate):
    import datetime
    conn = await get_db()
    try:
        nz_today = datetime.datetime.now(NZ_TZ).date()
        row = await conn.fetchrow("""
            INSERT INTO stock_entries (item_code, entry_date, job, supplier, description, cost_quantity, unit, gl_code, worker_name)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *
        """, entry.item_code, nz_today, entry.job, entry.supplier,
            entry.description, entry.cost_quantity, entry.unit, entry.gl_code, entry.worker_name)
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
async def export_csv(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    conn = await get_db()
    try:
        conditions = []
        params = []
        if date_from:
            try:
                params.append(datetime.strptime(date_from, "%Y-%m-%d").date())
            except ValueError:
                params.append(date_from)
            conditions.append(f"entry_date >= ${len(params)}")
        if date_to:
            try:
                params.append(datetime.strptime(date_to, "%Y-%m-%d").date())
            except ValueError:
                params.append(date_to)
            conditions.append(f"entry_date <= ${len(params)}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = await conn.fetch(
            f"SELECT item_code, entry_date, job, cost_quantity, unit, gl_code, worker_name FROM stock_entries {where} ORDER BY entry_date ASC, created_at ASC",
            *params
        )
    finally:
        await conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Item Code", "Date", "Job Number", "Subcategory", "Cost Quantity", "GL Code", "Comments"])
    for r in rows:
        job_full = r["job"] or ""
        job_number = job_full.split(" - ")[0].strip() if " - " in job_full else job_full
        writer.writerow([
            r["item_code"],
            str(r["entry_date"].strftime("%d-%m-%Y")),
            job_number,
            "",  # Subcategory — reserved column, left blank
            r["cost_quantity"],
            r["gl_code"] or "",
            r["worker_name"] or "",  # Worker name goes into Comments column
        ])
    output.seek(0)

    suffix = ""
    if date_from or date_to:
        suffix = f"_{date_from or 'start'}_to_{date_to or 'end'}"
    filename = f"stock_export{suffix}_{date.today()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

class EntryUpdate(BaseModel):
    job: Optional[str] = None
    cost_quantity: Optional[float] = None
    worker_name: Optional[str] = None

@app.patch("/api/entries/{entry_id}")
async def update_entry(entry_id: int, update: EntryUpdate):
    conn = await get_db()
    try:
        fields = []
        params = []
        if update.job is not None:
            params.append(update.job); fields.append(f"job=${len(params)}")
        if update.cost_quantity is not None:
            params.append(update.cost_quantity); fields.append(f"cost_quantity=${len(params)}")
        if update.worker_name is not None:
            params.append(update.worker_name); fields.append(f"worker_name=${len(params)}")
        if not fields:
            return {"ok": False, "message": "Nothing to update"}
        params.append(entry_id)
        await conn.execute(
            f"UPDATE stock_entries SET {', '.join(fields)} WHERE id=${len(params)}",
            *params
        )
        return {"ok": True}
    finally:
        await conn.close()

@app.delete("/api/entries/{entry_id}")
async def delete_entry(entry_id: int):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM stock_entries WHERE id = $1", entry_id)
        return {"ok": True}
    finally:
        await conn.close()

# ── Tool entries ──────────────────────────────────────────────────────────────

class ToolEntryCreate(BaseModel):
    tool_name: str
    job: str
    worker_name: Optional[str] = None

@app.post("/api/tool-entries")
async def create_tool_entry(entry: ToolEntryCreate):
    import datetime
    conn = await get_db()
    try:
        nz_today = datetime.datetime.now(NZ_TZ).date()
        row = await conn.fetchrow("""
            INSERT INTO tool_entries (tool_name, entry_date, job, worker_name)
            VALUES ($1,$2,$3,$4) RETURNING *
        """, entry.tool_name, nz_today, entry.job, entry.worker_name)
        return dict(row)
    finally:
        await conn.close()

@app.get("/api/tool-entries")
async def list_tool_entries():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT * FROM tool_entries ORDER BY created_at DESC")
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.delete("/api/tool-entries/{entry_id}")
async def delete_tool_entry(entry_id: int):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM tool_entries WHERE id = $1", entry_id)
        return {"ok": True}
    finally:
        await conn.close()

class ToolEntryUpdate(BaseModel):
    job: Optional[str] = None
    worker_name: Optional[str] = None

@app.patch("/api/tool-entries/{entry_id}")
async def update_tool_entry(entry_id: int, update: ToolEntryUpdate):
    conn = await get_db()
    try:
        fields = []
        params = []
        if update.job is not None:
            params.append(update.job); fields.append(f"job=${len(params)}")
        if update.worker_name is not None:
            params.append(update.worker_name); fields.append(f"worker_name=${len(params)}")
        if not fields:
            return {"ok": False, "message": "Nothing to update"}
        params.append(entry_id)
        await conn.execute(
            f"UPDATE tool_entries SET {', '.join(fields)} WHERE id=${len(params)}",
            *params
        )
        return {"ok": True}
    finally:
        await conn.close()

@app.get("/api/tool-entries/export")
async def export_tool_csv(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    conn = await get_db()
    try:
        conditions = []
        params = []
        if date_from:
            try:
                params.append(datetime.strptime(date_from, "%Y-%m-%d").date())
            except ValueError:
                params.append(date_from)
            conditions.append(f"entry_date >= ${len(params)}")
        if date_to:
            try:
                params.append(datetime.strptime(date_to, "%Y-%m-%d").date())
            except ValueError:
                params.append(date_to)
            conditions.append(f"entry_date <= ${len(params)}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = await conn.fetch(
            f"SELECT tool_name, entry_date, job, worker_name FROM tool_entries {where} ORDER BY entry_date ASC, created_at ASC",
            *params
        )
    finally:
        await conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tool", "Date", "Job Number", "Worker"])
    for r in rows:
        job_full = r["job"] or ""
        job_number = job_full.split(" - ")[0].strip() if " - " in job_full else job_full
        writer.writerow([
            r["tool_name"],
            str(r["entry_date"].strftime("%d-%m-%Y")),
            job_number,
            r["worker_name"] or "",
        ])
    output.seek(0)

    suffix = f"_{date_from or 'start'}_to_{date_to or 'end'}" if (date_from or date_to) else ""
    filename = f"tools_export{suffix}_{date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
