from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncpg, os, json, csv, io, base64, re, secrets
from datetime import date, datetime
from zoneinfo import ZoneInfo
from openai import AsyncOpenAI
import httpx
from dayworks_pdf import render_dayworks_pdf

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
NZ_TZ = ZoneInfo("Pacific/Auckland")

async def get_db():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog', format='text')
    return conn

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
                    source TEXT,
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
                    quantity INTEGER NOT NULL DEFAULT 1,
                    source TEXT,
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
            # Migrate: add quantity column to tool_entries if missing
            try:
                await conn.execute("""
                    ALTER TABLE tool_entries ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1
                """)
                print("Migrated: added quantity to tool_entries")
            except Exception:
                pass  # Column already exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dayworks_entries (
                    id SERIAL PRIMARY KEY,
                    job TEXT NOT NULL,
                    entry_date DATE NOT NULL,
                    variation TEXT NOT NULL,
                    vo_number TEXT,
                    location TEXT,
                    labour_rows JSONB NOT NULL DEFAULT '[]',
                    material_rows JSONB NOT NULL DEFAULT '[]',
                    comments TEXT,
                    photos JSONB NOT NULL DEFAULT '[]',
                    signoff_mode TEXT NOT NULL,
                    client_name TEXT,
                    client_email TEXT,
                    signature_data_url TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            # Migrate: add source column (voice/text) to both tables if missing
            try:
                await conn.execute("ALTER TABLE stock_entries ADD COLUMN source TEXT")
                print("Migrated: added source to stock_entries")
            except Exception:
                pass  # Column already exists
            try:
                await conn.execute("ALTER TABLE tool_entries ADD COLUMN source TEXT")
                print("Migrated: added source to tool_entries")
            except Exception:
                pass  # Column already exists
            try:
                await conn.execute("ALTER TABLE dayworks_entries ADD COLUMN sign_token TEXT")
                print("Migrated: added sign_token to dayworks_entries")
            except Exception:
                pass  # Column already exists
            try:
                await conn.execute("ALTER TABLE dayworks_entries ADD COLUMN webhook_url TEXT")
                print("Migrated: added webhook_url to dayworks_entries")
            except Exception:
                pass  # Column already exists
            await conn.close()
            print("Database ready.")
            return
        except Exception as e:
            print(f"DB not ready ({attempt+1}/10): {e}")
            time.sleep(3)

HAND_TOOLS = [
    {"name": "Tajima knife", "cost": 18},
    {"name": "Hammer", "cost": 26},
    {"name": "Hand saw", "cost": 16},
    {"name": "Spirit level", "cost": 15},
    {"name": "Crescent spanner", "cost": 29},
    {"name": "Pilers", "cost": 12},
    {"name": "Chalk line", "cost": 24},
    {"name": "Hack saw", "cost": 6},
    {"name": "Aviation tin snips", "cost": 29},
    {"name": "SINTEX R26:1 MS Cartridge Gun", "cost": 53},
    {"name": "Trowell", "cost": 12},
    {"name": "Crack patch tool", "cost": 19},
    {"name": "Pinch bar", "cost": 29},
    {"name": "Crow bar", "cost": 30},
    {"name": "Pop riveter", "cost": 75},
    {"name": "Spatula", "cost": 10},
    {"name": "Measuring tape", "cost": 20},
    {"name": "Metal file", "cost": 13},
    {"name": "Bull nose trowell", "cost": 8},
    {"name": "Wire brush", "cost": 7},
    {"name": "Wood chisel", "cost": 23},
    {"name": "Allen keys", "cost": 25},
    {"name": "Linbide scraper", "cost": 15},
    {"name": "Rubber mallet", "cost": 13},
    {"name": "Scissors", "cost": 20},
    {"name": "Window scraper", "cost": 9},
    {"name": "Socket set", "cost": 80},
    {"name": "Hand spade", "cost": 37},
    {"name": "Hand shovel", "cost": 70},
    {"name": "Sledge hammer", "cost": 70},
    {"name": "Hand pick", "cost": 50},
    {"name": "Digging bar", "cost": 66},
    {"name": "Builders set square", "cost": 24},
    {"name": "Penny roller", "cost": 51},
    {"name": "Large Membrane roller - 90 mm", "cost": 132},
    {"name": "Medium Membrane roller - 40 mm", "cost": 49},
    {"name": "SIEVERT EASYJET PLUS Lighter", "cost": 131},
    {"name": "steel club hammer", "cost": 32},
    {"name": "Sterling knife", "cost": 9},
    {"name": "Small torch lighter", "cost": 131},
    {"name": "Wire nipper cutters", "cost": 15},
    {"name": "Hand mallet", "cost": None},
    {"name": "Striker", "cost": 12},
    {"name": "Broom", "cost": 40},
    {"name": "Garden hose", "cost": 50},
    {"name": "Garden hose fittings", "cost": 4},
    {"name": "Tool Bag", "cost": 60},
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
    {"code": "536973", "description": "Sikaflex - 400 Fire Grey 600ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex four hundred fire, sika fire sealant grey, fire rated sealant"},
    {"code": "551349", "description": "SikaTop Seal-107 Dryseal 5kg", "supplier": "SIKA", "unit": "KG", "gl": "2000", "alias": "sika top seal, dryseal, sika top one oh seven"},
    {"code": "551940", "description": "Sika MonoTop-438 R (25kg)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika monotop four thirty eight, monotop repair mortar, sika repair mortar"},
    {"code": "565413", "description": "Sikadur-52 Injection Normal 0.9l/kg", "supplier": "SIKA", "unit": "KIT", "gl": "2000", "alias": "sikadur fifty two, sika injection resin, crack injection resin"},
    {"code": "591755", "description": "Sikaflex MS 600ml White", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikaflex MS white, sika MS white sausage, sikaflex white six hundred"},
    {"code": "59300074", "description": "BluRez CS150 20kg", "supplier": "MBP", "unit": "ea", "gl": "2000", "alias": "bluerez CS one fifty, blurez powder, bluerez base"},
    {"code": "617759", "description": "Sikaflex PRO-3 Purform 600ml", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikaflex pro three, sika pro three purform, sikaflex PRO sausage"},
    {"code": "80151200", "description": "Turbo wave diamond blade dry/wet cured concrete", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "diamond blade, turbo wave blade, concrete cutting blade"},
    {"code": "82151204", "description": "125mm Disc. (diamond saw blade)", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "one twenty five diamond disc, small diamond blade, angle grinder blade"},
    {"code": "85681206", "description": "105 turbo cup grinding wheel 12 segments", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "turbo cup wheel, grinding wheel, cup grinder wheel"},
    {"code": "92541", "description": "Sikaplug 5KG", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaplug, sika plug, hydraulic plug"},
    {"code": "ACE.5", "description": "ACETONE - 5L", "supplier": "NZFIBRE", "unit": "PAIL", "gl": "2000", "alias": "acetone five litre, acetone, solvent cleaner"},
    {"code": "ADCOR500T", "description": "ADCOR 500T WATERSTOP 6x5m CTN - CTN", "supplier": "ALLNEX", "unit": "ea", "gl": "2000", "alias": "adcor waterstop, adcor five hundred, waterstop strip"},
    {"code": "ALLAQ15", "description": "Aquadrain 15 18.9m2 VAQUA15X", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "aquadrain, drainage mat, aquadrain fifteen"},
    {"code": "ALLBESA", "description": "Allco - Bentoseal 15kg", "supplier": "ALLCOWATER", "unit": "PAIL", "gl": "2000", "alias": "bentoseal, bento seal, bentonite seal"},
    {"code": "ALLBETG", "description": "Allco - Bentogrout 25kg", "supplier": "ALLCOWATER", "unit": "BAG", "gl": "2000", "alias": "bentogrout, bentonite grout, bento grout"},
    {"code": "ALLCET", "description": "Allco - Cetcoat 15kg", "supplier": "ALLCOWATER", "unit": "PAIL", "gl": "2000", "alias": "cetcoat, cet coat, allco cet"},
    {"code": "ALLDE4", "description": "Dermabit Extra - 4mm thick Polypropylene one side", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "dermabit extra, dermabit four mil, polyprop membrane"},
    {"code": "ALLRX101", "description": "RX101T Waterstop 6.1lm per roll", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh one waterstop, swelling waterstop, hydrophilic strip"},
    {"code": "ALLRX101DH", "description": "RX101DH waterstop delayed Hydration 5m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh one delayed hydration, delayed hydration waterstop"},
    {"code": "ALLSWTB", "description": "Allco - Swelltite Termination Bar Lm", "supplier": "ALLCOWATER", "unit": "LM", "gl": "2000", "alias": "swelltite, sweltite, swelltite bar, termination bar, swelltite termination, sweltite bar"},
    {"code": "ALLVOCR", "description": "Allco - Voltex CR (5.4sqm roll)", "supplier": "ALLCOWATER", "unit": "M2", "gl": "2000", "alias": "voltex CR, voltex roll, bentonite membrane roll"},
    {"code": "ALLVODS", "description": "Allco - Voltex Super 66.6 DS", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "voltex super, voltex DS, bentonite super sheet"},
    {"code": "ALLVOLT", "description": "Voltex Roll (5.5m2 per roll) m2", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "voltex, voltex sheet, bentonite sheet roll, carpet"},
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
    {"code": "COREFL18", "description": "Allguard Coreflute 1800 x 1150 x 4mm", "supplier": "ALLCOWATER", "unit": "SHEET", "gl": "2000", "alias": "coreflute, protection board, allguard coreflute, allco coreflute"},
    {"code": "COREFL18", "description": "Mulfords Coreflute 1800 x 1150 x 4mm", "supplier": "MULFORDS", "unit": "SHEET", "gl": "2000", "alias": "mulfords coreflute, mulford coreflute, coreflute mulfords"},
    {"code": "COREFL18", "description": "Recycled Coreflute 1800 x 1150 x 4mm", "supplier": "", "unit": "SHEET", "gl": "2000", "alias": "recycled coreflute, recycled protection board, eco coreflute"},
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
    {"code": "VCTX", "description": "Volclay Coretex (9.29m2) roll", "supplier": "", "unit": "ROLL", "gl": "2000", "alias": "volclay coretex, voltex coretex, coretex roll"},
    {"code": "VRX10210", "description": "Allco - RX102 Waterstop 10.2m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh two waterstop, RX102 strip, allco waterstop ten metre"},
    {"code": "VST50", "description": "DPM Tape Allsheet 48mm x 30 m Red", "supplier": "ALLCOWATER", "unit": "M", "gl": "2000", "alias": "DPM tape red, allsheet tape red, red DPC tape"},
    {"code": "VSTPOL10.2", "description": "Swelltite Polish 3000 10.2m Roll", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "swelltite, sweltite, swelltite polish, polish three thousand, swelltite roll, sweltite polish, sweltite roll"},
    {"code": "VVS500", "description": "Allsheet 500 micron non hydrostatic DPM PE 4x25m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "allsheet DPM, five hundred micron DPM, damp proof membrane sheet"},
    {"code": "WLPERMATAC21", "description": "WOODLOK PERMATAC 21KG", "supplier": "GLUE", "unit": "ea", "gl": "2000", "alias": "woodlok permatac, permatac adhesive, woodlok glue"},
    {"code": "11204", "description": "Pulsa washer containers (box of 1,000)", "supplier": "RAMSET", "unit": "Bag", "gl": "2000", "alias": "pulsa washer, washer containers, ramset washers"},
    {"code": "P8C630", "description": "30 mm nails (box of 500)", "supplier": "RAMSET", "unit": "Bag", "gl": "2000", "alias": "thirty mil nails, P8C630, ramset thirty nails"},
    {"code": "P8HC627", "description": "27 mm nails (box of 500)", "supplier": "RAMSET", "unit": "Bag", "gl": "2000", "alias": "twenty seven mil nails, P8HC627, ramset twenty seven nails"},
]

DEFAULT_JOBS = [
    "2306 - Warranty Work - Sansom Construction Systems Ltd",
    "0001NOJOB - NONJOBRELATED",
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
    "23159 - AIAL - WP1 - Terminal Integration",
    "S34000 - Sansom Construction Systems LTD",
    "S9000 - Admin Time - Sansom Ltd",
    "S34042 - Half Moon Bay , 25 Thurston Place - Waterproofing",
    "23300 - Newton Systems",
    "S34065 - Auckland Airport Domestic Processor Pier & FLB Tanking Works",
    "S34086 - H47 - Gorst Lane Membrane Works",
    "23245 - AATH Facade Package",
    "S34131 - Lorne Street - Student Accommodation",
    "S34182 - AIAL Domestic Processor - Headhouse",
    "S34183 - Waitakere Hospital - Tanking",
    "S34194 - Project Waka - Stage 2 Waterproofing",
    "R626 - Mt Eden 101, Concrete Office / Yard",
    "S34228 - JTFJ Costs Mt Eden Road 101",
    "S34248 - Mayfair Retirement Village - Oteha Valley 14",
    "S34266 - Maintenance / Membrane and Admininistration",
    "S34323 - Staff Appreciation",
    "S2301 - Pre-Investigation / Quotes",
    "S34345 - Auckland Art Gallery - East Terrace",
    "S34354 - Drury / Paerātā Rail Station Main Works – Seismic Joints",
    "S34360 - Mt Eden Road 101 -Building Maintenance",
    "S34371 - Newton Systems Limited",
    "R747 - Brighton Road 6  Screeding",
    "S34443 - Fisher & Paykel Headquarters",
    "S34444 - UoA B505, Park Road 85 - Basement Carkpark Leaks",
    "R765 - Diocesan School Aquatics Centre Panel Remediation",
    "S34466 - Queen Street 256 Student Accommodation",
    "S34467 - Albert Street 99",
    "S34477 - Summerset St Johns - Building G - Excavation, Inground Plumbing and Tanking",
    "R776 - Arthurs Pass, Kiwirail Tunnel Repairs",
    "S34482 - Orams Commercial Buildings B1A & B1B",
    "S34490 - Marine Parade 13 - Tanking",
    "101 - Rates",
    "S34528 - Murphy House Stage 2 - Tara Iti",
    "S200STOCK - Sansom Ltd Stock Purchases",
    "S34539 - The Hill Ellerslie - Warm Roof",
    "S34543 - Fisher & Paykel - Garage Building",
    "S34545 - MPI PHEC- Southbase Construction",
    "24110 - AIAL WP1 - Tanking",
    "S34577 - Carlaw Park Student Village 4",
    "S34578 - Zone 23 - Edwin Street 23",
    "S34582 - Orams Marine Carpark Refurbishment",
    "S34591 - The Hill - Building B",
    "S34593 - Civic Theatre - Basement Remedial Waterproofing",
    "S34611 - Tools & PPE",
    "S19239 - Sansom Concrete Repairs Ltd",
    "S34618 - Mid Central DHB Substation 1, Palmerston North",
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
    "S34673 - 44 Ireland Street, Freemans Bay - Tanking",
    "S34683 - FPH B5.1 - Tanking",
    "S34688 - Auckland City Mission - Shade Sail post detailing",
    "R937 - The Hill - Belvedere, Screeding",
    "R0001NOJOB - Sansom Concrete Repairs - NONJOBRELEATED",
    "R967 - Fort Street, Auckland - Facade Concrete Remedial Project",
    "R980 - 33 Federal Sansom Crack injection",
    "S34754 - Sansom Maintenance - Investigation Costs",
    "S34763 - Jervois Road 41",
    "S34766 - Alberton Avenue 57",
    "R1001 - Gorst Lane  - Wall and Carpark Pillar Remedials",
    "S34772 - Sarsfied, 81 -  Waterproofing",
    "R1008 - Orams Marine Footpath Saw Cut",
    "S34808 - 147 Captain Springs Road  -  Aquakem Coating to walls",
    "S34822 - Fisher & Paykel Healthcare B5.1 - Seismic Joint",
    "R1028 - 22 Fleet Street Structural Investigation",
    "S34832 - Barfoot & Thompson Remerua - 367 Remuera Road",
    "S34846 - 74 - 76 Grafton Road - Grafton Meditel Hotel",
    "S34854 - ARWCF Gate House - Roof Gutters Works",
    "R1046 - Carbodur NSM BC12 Rods for St Lukes Gardens",
    "S34870 - MPI PHEC - Membrane Roofing and Emseal Package",
    "S34872 - Snells Beach Waste Water Treatment Plant Injection",
    "S34874 - Air NZ Hangar 4 (JFC) - Flame Trap 4",
    "S34884 - Remuera Road 454 - Deck Waterproofing",
    "R1059 - UOA B503.B41C - Autoclaves Replacement, Floor Repalcement",
    "S34889 - 985 Mount Eden Road - Kingsway Connection (A01/A02) Lift",
    "S34897 - Glen Innes, Te Mahia & Takanini Station - Pedestrian Crossings Waterproofing",
    "S34902 - AIAL TH01 – Remedial Works",
    "R1073 - Air NZ Hangar 2 Re-life",
    "S34910 - Broadway 255, Newmarket, Auckland -  Canopy Remediation works",
    "S34914 - Waitemata (Britomart) Train Station Escalators",
    "R1090 - Locarno Avenue, Sandringham, 23 -  Retaining Wall Repair",
    "S34931 - Starship Childrens Hospital - PC3 Atrium Infill, duct Extract",
    "R1103 - 454 Remuera - Concrete cut nib, screed and core drill",
    "R1104 - Stanmore Watercare Pump Station Investigation",
    "S34947 - Rosedale Bus Station and Corridor - Tanking",
    "S34950 - Painton Road,5, Silverdale -  Install Membrane Plinths",
    "R1112 - Bridge 43 MSL 96.765km. - Impact Beam Replacement",
    "S34956 - Beresford Square 16-18",
    "S34966 - East Coast Bays Community Centre Refurbishment",
    "R1138 - MANGERE WASTEWATER TREATMENT PLANT PREAERATION & SEDIMENTATION TANK 3&4 PR",
    "S34972 - Orams Existing Carpark - Sealant Works",
    "S34975 - Station M - 21 Manapau Street, Meadowbank - Precast Sealant",
    "S34981 - Murray Halberg Retirement Village - Remedial Waterproofinga",
    "R1149 - Gabador Place, 34 - Concrete Repairs and Coating",
    "R1150 - Holcim, Onehunga Harbour Road, 57 -  Concrete Repairs",
    "S34982 - Henderson Station - Platform Joint Seal",
    "S34984 - 7 Winn Road, Freemans Bay - Waterproofing Works",
    "R1155 - Concrete Repairs - Small Sales",
    "S34993 - Auckland Airport WP3 Main Works 2.13 Roofing (Membrane)",
    "S34996 - Three Kings - Maintenance Annual inspections",
    "S34999 - 101 Mt Eden Road, Mt Eden - Rear Deck and Lower Roof Membrane Replacement",
    "S35010 - ADHB A01 Entrance Area Coating Works",
    "S35013 - CDC HV2.2 - Roofing",
    "S35021 - PaknSave Albany",
    "S35023 - Manawaora Road 285",
    "R1186 - Northridge Apartments, Stanwell Street Parnell , 28",
    "R1194 - Stanbeth Building, Commerce Street,6 - Crack Repairs",
    "S35035 - BEKS2025 Limited",
    "S35036 - Bledisloe Cruise Terminal - Tanking",
    "S35042 - AUT, Wakefield Street, 56 -  Roof Repairs",
    "R1206 - Fort Street Wilson Car Park 34 Shortland Street",
    "S35048 - Racecourse Parade, 26  -  Sansom Annual Maintenance Inspection",
    "S35049 - Greenside Rd, 101 - Annual Maintenance Inspection",
    "R1213 - Saint Paul Street, 47, Auckland Central -  Northern Façade Concrete Wall Repair",
    "S35054 - 13-15 College Hill Police Station",
    "S35055 - 60E Sentinel Road, Herne Bay - Roof Waterproofing",
    "R1218 - TVNZ - Concrete Repairs",
    "S35067 - Northridge Apartments - 28 Stanwell Street",
    "S35068 - Warranty Work - Sansom Ltd",
    "S35070 - Aon Centre, Custom Street West, 29 -  AHU Drains L22 Air Handling Units",
    "S35074 - Pipe Penetrations",
    "S35077 - Ascot Office Park - 93-95 Ascot Ave, Greenlane",
    "S35078 - Gibbons Road, 8B -  Membrane Remedial Works",
    "R1241 - Waikeria, Ngaio Prison  - Stage 2 A&B",
    "S35085 - Remuera Road, 464, Auckland - Roof membrane Maintenance Remedial Works",
    "S35087 - 6 Pekapeka Street, Raglan - Tanking Remediation Consultant",
    "S35088 - 19 Ngaiwi St, Orakei - Roof Membrane",
    "S35092 - Medlands Beach GBI - Hays",
    "S35099 - Island View Drive 47, Gulf Harbour - Newtons",
    "S35103 - 107 Carlton Gore Road  - Drainage Improvement",
    "R1271 - Kaitaia Hospital Stage 2 Crack Repair",
    "S35110 - Gould Street 9 - Russell (Beach House)",
    "S35111 - Gould Street 7 - Russell (Boat House)",
    "S35114 - 41C Sandpiper Ave- TPO Roof Membrane",
    "S35123 - 34 Rawene Avenue, Westmere - Membrane Replacement",
    "S35135 - Mt Wellington Estate Warehouse 1  -  2 Monahan Road, Mt Wellington - Tanking",
    "R1290 - Warranty Repair work - Concrete Repairs",
    "R1294 - Cliff Rd, Torbay, 76 -  Concrete Restoration",
    "S35141 - Vulcan Lane 10",
    "S35142 - TVNZ - 100 Victoria Street West - Membrane Re-roof Works",
    "S35150 - MIT Manukau Campus - Interior Plant Room Works",
    "R1300 - Westgate  Bus Station -  Fire Doors Grouting",
    "S35153 - 1625 Howick Pakuranga Community Sport Centre",
    "S35154 - Grey Ave 139  Auckland - Annual Maintenance Investigation",
    "R1303 - Mt  Messenger Pier - Concrete Repair",
    "S35155 - Greenlane Hospital, Greenlane West  214 - G04 Investigation and Remedial Works",
    "S35156 - Auckland Hospital - A08 Level 6 , Oncology Remedial Works",
    "R1306 - McLaughlins Road, Building 2, 69 -  Concrete Repairs",
    "S35158 - Epsom Retirement Village - Membrane Works",
    "S35168 - UoA, Waiparuru Hall, B441 and B442 - Membrane Roof Report",
    "S35169 - 78 View Road - Newtons",
    "R1311 - Spark Arena - Concrete Cuts",
    "S2309 - Athens Road 1/59, Onehunga",
    "S2310 - Riddell Rd 283, Glendowie",
    "S2311 - Speights Rd 8, Kohimararama",
    "S2312 - Glendowie Road 12a",
    "S2313 - ILD Australia PTY",
    "R1315 - Block 10 St Lukes Gardens Crack Repairs",
    "S35173 - Woolworths Ponsonby - B2 Carpark Storage Room",
    "S10001 - Tanking Tenders",
    "S11002 - Membrane Tenders",
    "S17003 - Facade Tenders",
    "S19004 - Maintenance Tenders",
    "S35185 - 18 Taurarua Terrace, Parnell - Balcony Remedial",
    "S35187 - Pitt Street, 21 - Membrane Works",
    "S35190 - Bledisloe Cruise Terminal  - Sikalastic to Columns",
    "R1329 - Britomart Station Core Drilling and PH Testing",
    "S35197 - Long Bay High School - Temporary Waterproofing",
    "R1338 - WSL Mangere WWTP - Splitter Box 1",
    "S35198 - 4B/15 Fleet Street - Podium Deck Water Ingress",
    "S35199 - Site 6 - Annual Maintenance Inspection",
    "S35200 - Greys Ave, 139 -  Maintenance Remedial Works",
    "S35201 - 30 York Street, Parnell - Membrane Waterproofing",
    "S35202 - 66a Grafton Road, Grafton - Garage Slab Leaks",
    "S35206 - Auckland Art Gallery - Storage Room Water Ingress",
    "R1339 - Central Police Station - Helibar",
    "R1343 - Rosedale WWTP - Concrete Repairs",
    "S35208 - Greenlane Hospital G15 Building - Membrane Investigation Works",
    "S35209 - University of Auckland B315 - Kate Edgar Building",
]

# ── Job Variation Orders (VOs) ────────────────────────────────────────────────
# Hardcoded from the latest CSV extract emailed from the job-costing system (no API available).
# To refresh: replace this block with a new CSV export (Job Number, Variation Order Number,
# Description, Customer Order Number). VOs whose job number no longer appears in DEFAULT_JOBS
# are automatically dropped, so retiring a job also retires its VOs.
DEFAULT_VOS_CSV = """Job Number,Variation Order Number,Description,Customer Order Number
21148,VO001,Internal VO Project Establishment Costs ,Email/0608
21148,VO002,Internal VO Blueys Management Costs ,Email/0608
21148,VO003,KRD Air Freight Costs for MC30 Kickers,
21148,VO004,Beresford Square Station Box Injections Works,LKASI00908
21148,VO006,KRD Air Freight Geotextile & PVC Membrane for Adit A2 & A5 ,Email/2110
21148,VO007,Mercury Lane PU Injection Works ,LKARFI2109
21148,VO008,KRD - Sika alternative membrane,
21148,VO009,KRD - RX101T and Cetseal supply only,PUR27963
21148,VO010,KRD -Freight for Additional OBV Membrane & Roundels ,
21148,VO011,Mercury Lane Station Box Terminations,SI-001057
21148,VO013,TBM Segmented Tunnel Concrete & Injection Repairs ,SI001292
21148,VO014,KRD - Adit A3 Remedials ,SI001295
21148,VO015,KTN - MC20/50 HeadWall Tie Back Bar Supply & Detailing ,Email/1603
21148,VO016,KTN – 40mm Injection Hose Supply & Install ,Email/2103
21148,VO017,KRD - Additional Heat Gun Purchase to Assist with Power Issues,Email/0104
21148,VO018,KRD - Night shift works,Email/0104
21148,VO019,KRD - Remobilisation & Lack of Access Installation in Adit A5 ,Email/2104
21148,VO020,KTN – Remediation Work at MC20/50 Headwall Waterbar ,SI-001502
21148,VO021,Sea Freight Differential Cost for Additional Waterbar,SI001368
21148,VO022,KRD – H&S Stand down Time,Email/2107
21148,VO023,KTN – Stand down Time at MC50 Isolation Joint ,Email/2507
22196,VO001,Temporary waterproofing in Superstructure,SI-001893
22196,VO002,Grout Fill Vertical Lifting Eyes,SI-001956
21148,VO024,KRD: Supply of Bluey Injection Hose ,SI-001972
22196,VO003,Application of Sika Blackseal on precast elements,SI-001985
21148,VO025,"KTN - Concrete Crack Injection Repairs ",
22196,VO004,AOT - Joint sealant to southern panels - chase cutting,SI-002108
22196,VO005,Application of Sikalastic 152 for WST facade glazing envelope,SI-002164
21148,VO026,KRD - Substrate prep for the TBM termination,Email/1309
21148,VO027,KRD Labour to move services,Email/1309
22196,VO006,Wellesley Structure - North facade masking L0-L1,SI-002230
21148,VO028,Mercury Lane Waterproofing,22253
21148,VO029,KRD – Additional Injection Hose to Pressure Terminations ,Email/1010
21148,VO030,KTN – Patching Works to MC30/60 Formwork Anchors ,Email/1010
21148,VO031,KRD - Dyna Drill Supply to LKA ,Email/1310
21148,VO032,KRD – Patching Works to MC30 Tunnel ,Email/1310
21148,VO033,KRD Additional BA Anchors over MC30 Allowance,
22196,VO007,Aotea - EWS402 Glazing Waterproofing works,SI-002370
21148,VO034,KRD – RX101(T) & Cetseal Supply 2022,Email/1710
22196,VO008,AOT - WST Precast Facade panel connection flashing,SI-002401
22196,VO009,AOT - Facade Closure for Eastern Retail Unit L0,SI-002413
21148,VO036,KRD - Supply of Butyl Tape to Mercury Lane and Beresford Lane Stations,Email/1611
21148,VO037,"KRD - Concrete Crack Injection Repairs ",
21148,VO038,KRD - Supply of 75mm Butyl Tape ,Email/2411
22196,VO010,Aotea - EWS402 Glazing Waterproofing works - East fixes,SI-002556
21148,VO039,KTN – Southern Headwall Remedial Works ,Email/1612
22196,VO011,Aotea - CSX10 Tape and AT Facade about GL32/E,SI-002703
22196,V001,Sika Coating to Transformer Bund,Email/1502
21148,VO040,KTN – MC20/50 Patching Works ,
21148,VO041,Application of Blackseal Elastic to the precast panels,SI-001282
22196,VO012,AOT - WST South Elevation RyanRock retention,SI-002969
22196,VO013,Panel open joint/150mm Seismic Shoe Detail/Nib Alteration,SI-002962
22196,VO014,B2 Foul water sump coating and screed works,SI-002849
22196,VO015,Supply & install flashing to close the envelope in EWS402 N&W,SI-002973
22196,VO016,Façade Baffle Remedial Work,SI-002940
22196,VO017,Application of Sika 910N Primer to the seismic joint substrate,SI-003046
22196,VO018,Pipe Penetration temporary waterproofing,SI-003019
22196,VO019,membrane installation area Zone 3/4 remove water from roof 20/03,SI-003037
21148,VO042,"KRD- RX101 (T) & Cetseal Supply 2023",SI-003042
21148,VO043,"MCL - Mapei Planiseal Coating ",
21148,VO044,"MCL - Pipe Penetration Detailing ",
21148,VO045,MCL - Peel n Stick membrate to PVC Waterbar,
21148,VO046,"MCL - Torch on Membrane Patch Works ",
21148,VO047,"KRD  - Bluey Hose Connector Supply ",
21148,VO048,"KTN - MC20/50 Patching Works ",
21148,VO049,Mercury Lane Facade,
22196,VO020,Roof Waterproofing,7/09/2022
21148,VO050,Application of Sikalastic 152,SI-003050
21148,VO051,KRD – MC21 Headwall Repairs ,Email/2403
22196,VO021,Additional Roof Substrate,
22196,VO022,AOT - SUMP H00 Ceiling / Roof Crack injection works,SI-003140
22196,VO023,Concrete Grinding and panel upstand repair,SI-003142
21148,VO052,"KTN - MC20/50 Patching Works ",
21148,VO053,Temporary Sealant on Level 3,SI-003150
22196,VO024,Wellesley Roof - RAB board temporary sealant,SI-003181
22196,VO025,Separation Flashing,SI-003183
23113,VO001,Extra warm roof to gutter and membrane extension to fascia board,SW-SI0001
22196,VO026,L0 internal air seal works,SI-003243
22196,VO027,WST Application of Dowsil Firestop for L3/L4 Joints,SI-003276
21148,VO054,Air freight,
22196,VO028,AOT - WST - Installation or Gorter Access Hatch on Roof,SI-003339
22168,VO001,Stegowrap Penetration Detailing,
22168,VO002,MHP - Reinstallation of DPM due to Incorrect Setout of Formwork,SI-000022
22196,VO029,North L1 air seal,SI-003353
22196,VO030,WST Façade Structural Cover Plates,SI-003277
22196,VO031,Temporary Waterproofing to the Deck on L2 East,SI-003377
23113,VO002,Extend the roof membrane to cover the timber block,SW-SI0002
22196,VO032,Wellesley roof - substrate drying,SI-003394
21148,VO056,MC20/50 Dry Crack Repairs ,
21148,VO057,Mercury Lane Grouting Works ,
22168,VO003,East Building Footings Pre Pour Assistance & Re Tape ,
23159,VO001,Canopy Waterproofing Works,COR-000021
22168,VO004,West Building Stegowrap Remedials ,Email/0507
22196,VO033,GL32/E Dowsil sealant in 30-50mm gap from L1 to L4,SI-003498
22168,VO005,Patch Repairs Zone West Building Footings ,Email/2107
22168,VO006,Pipe penetrations to the North Building  ,Email/2107
22196,VO034,AOT-VST SI for nib waterproofing,SI-003649
22196,VO035,AOT - WST - 600mm long rainsheilf flashing,SI-003687
22196,VO036,AOT - Sealing of scuppers through facade panels,SI-003678
21148,VO058,"Double Sided Tapes for Adit A1 Waterbar ",
21148,VO059,"Cross Passage Investigation & Injection Works ",
22168,VO007,East Building Underslab Membrane Remedials & Cleaning of Laps,
22168,VO008,"East Building Underslab Penetrations ",SITEDIR-97
22196,VO037,AOT - Closure of L1 Western Moisture Barrier,SI-003842
22196,VO038,Exhaust Flue penetration waterproofing,SI-003870
22168,VO009,North Building Underslab Service Penetrations Detail ,IR-000123
21148,VO060,Adit A1 Shaft Downtime ,
21148,VO061,Mercury Lane Seismic Joints ,
21148,VO062,KRD - Cavity drainage holes at joint intersections ,
22196,VO039,AOT - Flashing for Electrical covers,SI-003924
22168,VO010,West Building - Bituthene to Internal Blockwork Wall ,Email/2209
22196,VO040,AOT - Sikalastic Application for EWS502 - East Elevation,
22196,VO041,AOT - WST Skirt flashings for Penthouse Louvres,SI-004022
22168,VO011,"BEPL-SITEDIR-000147 North Building Preprufe Repairs ",000147
23159,VO002,Supply and install of temporary wind break to protect Tapered board.,SI-001383
22196,VO042,Sealant for under parapet buildersworks,SI-004071
22196,VO043,Repair works Gutter overflow Western side.,SI-004067
S34131,VO001,"Replacement of Waterbar around L2 Capping beam (Grid 11 & 12) ",SI-000041
21148,VO063,"MTE - 10FT  Container Repair ",7/9 email
22168,VO012,North Building - Revised Preprufe Terminations,
22168,VO013,"East Building - Detailing Pipework with LM3000",
22168,VO014,"East Building - Stainless Steel Flashings ",
22168,VO015,"West Building - Slab Penetrations ",
22196,VO044,Proclima solitex to VST soffit,SI-004108
22168,VO016,North Building Lift Pit 3 Adcor 500 Replacement ,SI-000188
23245,VO001,Freight costs for the materials from Sika,251023
23159,VO003,Additional freight cost due to on-site logistics issues (Reimbursement only),
S34131,VO002,Surface Prep to Grid F Existing Structure ,RFI-000132
22196,VO045,AOT - Base flashing and overflashing and detailing for MEFH Penetrations through roof,SI-004111
22168,VO017,West Building Underslab Step Remedials ,TBA
23245,VO002,Sika MonoTop-352 N fillet and the sealant,Email14/11
S34131,VO003,Remedial works to damaged waterproofing ,SI-000054
22196,VO046,Facade Flashings at Gutter level,SI-004211
S9000,VO001,HSEQ - Admin,
22168,VO018,Remedials to Loading Bay Slab ,SITEDIR256
22168,VO019,North Building Stegowrap Remedials ,
22168,VO020,North Building PC Panel Flashings ,GCOR000409
22168,VO021,Stegowrap to PolyRock Infills ,
21148,VO064,MCL – B3 Waler Beam Injection,Email27/11
22168,VO022,Cardiology - Emseal QuietJoint SHG - New wall to existing window detail,SITEDIR163
21148,VO065,Temporary PEF Rod Panel Seismic Joint Weatherproofing Supply and Install,SI-004249
22168,VO023,North Building Lift Pit 1 Preprufe Remedials ,DIR-000267
22196,VO047,AOT - Sikalastic and Tremco Detailing for TCL Gutter and Fascia,SI-004109
21148,VO066,Additional Sealant to Louvre Openings,SI-003300
22168,VO024,North Building Lift Pit 2 & 3 Preprufe Repairs ,SITEDIR270
21148,VO067,K Rd Crack Injection MC30 ,SI-004258
22168,VO025,North Building Stegowrap Remedials,Email12/12
22168,VO026,North Building - Detailing Pipework with LM3000,Email12/12
22168,VO027,Sealant to Nibs and Precast Panels,
21148,VO068,Temporary sealant - L3 to Precast,FCR047574
S34131,VO004,Epoxy Injection for Ground Water,SI-000061
23245,VO003,Groutfill the baffle rebate using Sika Monotop 412,SI-001411
21148,VO069,Temporary torch-on Waterpprofing for rain water pipe at MNL roof Level L3,SI-004400
23159,VO004,Waterproofing - EBH L2 slab edge to existing building,SI-001773
22168,VO028,Loading Dock Waterproofing Remedials ,BEPL-SITED
22168,VO029,"Surface Preparation to Link Building Nibs ",GCOR000045
22168,VO030,Stegowrap Repairs to Column Slab Pockets,SI: 000383
23245,VO004,Precast Panel Concrete repairs,SI-001715
23245,VO005,Supply and install Sika EMSEAL 150mm to East Concourse Riser,SI-001617
23159,VO005,Slab repairs to Make Substrate Suitable for Warm Roof,SI-001852
21148,VO070,Beresford Square Torch On,
22168,VO031,Lift Pit 2 Preprufe Remedials ,SI-000446
22196,VO048,Southern Parapet Cap Flashing,SI-004056
22168,VO032,Additional extra over cost for East building sealant works due to differences in quantities and joint sizes,
S34131,VO005,Grid EJ Surface Preparation ,Email06/03
22196,VO049,Removal and Reinstatement of WST roof membrane around gutter droppers,SI-004580
22168,V001,Lift Pit 1 Waterbar Install ,
23159,VO007,Temporary membrane for scaffold penetrations to the canopy,SI-002042
22196,VO050,Application of Sikalastic 152 to Skylight Upstands,SI-004597
22196,VO051,Application of Sikalastic 152 to Skylight Upstands,SI050090
S34131,VO006,South Core Membrane Repairs ,000179
S34131,VO007,Waterproof Services Through Existing Building Wall,SI-000077
21148,VO071,Planiseal MR Supply to LKA ,PUR59767
21148,VO072,"Supply & Install of Bitumen Fillet ",SI-004631
22168,VO033,Temp Works Engineer Time & Soldier Hire for Lift Pit,
22168,VO034,West Substation Tanking Works ,
22168,VO035,West Substation Pipe Penetrations  ,
23245,VO006,Additional Access costs ,
21148,VO073,Torch On Penetrations to Beresford Square ,
21148,VO074,Beresford Square Mapelastic Smart ,
S34131,VO008,Swellable Waterbar to Existing Columns ,-000179
23245,VO007,Temporary Waterproofing – Comms Room Level 1 - 5,SI002073
21148,VO075,Sealant to the external precast penetrations,LKA-SI-004
21148,VO076,MLA L0 Mapilastic Install,
23159,VO009,Additional Detailing to Plinths L3 Plant room &  to Steel Column over Plinths along Grid EG,SI-001725
23159,VO010,WP1 - L2FS - L1 Fire Door Works,SI-002170
22196,VO052,Weather sealant to facade penetrations for lights,SI-004701
22168,VO036,South Substation ADCOR 500T Replacement ,
21148,VO077,Mercury Lane Additionall Surface Waterproofing,SI-004716
23245,VO008,TH01 - Sealing office barrier panels,SI-002154
23245,VO009,Carpark - Sealing to top of flashing - Lvl1 Gl C4 - E-J,SI-002120
22168,VO037,East Building - Conclusions WUFI study weep holes precast,
S34131,VO009,Koolfoam Poly to Triangular Core ,000248
23245,VO010,Sikalastic 152 coating to Speedramp,SI-002195
R444,VO001,"P&G associated with contract works valued at $3,338.67",1159/173
22168,VO038,North  Substation Tanking Works ,
22168,VO039,North Substation Pipe Penetrations  ,
R444,VO002,Concrete Slab Edge Repair,ATS No 176
23159,VO011,Flood testing to roof ,SI-002209
23245,VO011,PP Grout Fill to C3,SI-002285
23245,VO012,Sealant at Precast Barrier Ends along Concourse GL J,SI-002265
R444,VO003,Concrete Slab Chase Repairs 5E & 7A,CI-170
21148,VO078,Supply and Install of Illmod 600- 30/17- 32,SI-004867
R444,VO004,"BCA-A Approved Documents FC ",CI-171
22168,VO040,North Building Nib Remedials,
S34131,VO010,Plug Former Ground Anchor Locations,SI-000093
23159,VO015,WP1 - L2FS - L1 Fire Door Works,SI-002170
22168,VO041,"Site Direction - Seismic Joint Works",
22168,VO042,North Building EMSEAL Boot Remedials ,
22168,VO043,North Building Nib Bituthene Remedials ,
22196,VO053,Sealant over fixings - Stacker door steel & Canopy beam brackets,SI-004890
S34131,VO011,Grid E9 Surface Preparation ,
23159,VO016,Temporary termination on level 03 ,SI-002333
23159,VO017,Canopy remedial sump outlet adjustments,SI-000006
23245,VO013,Temp Roof WP to Progress Comms Rooms,SI-002436
22168,VO044,NB_Zone 1_Concrete Infill SOG,
S34131,VO012,Waterstop for the stitches on north core (Core 3) from level 2 to 19,SI-000102
23245,VO014,Stair 5 & 6 Precast Penetration Seals Around Steel Stubs,SI-002457
23220,VO001,S34338 - AUT WH Plant room Waterproofing Remedial Works,S34338
21148,VO079,MLA L0 Glazing Structural Opening Waterproofing,SI-004966
23159,VO018,WP1- L3 plinth update to accommodate DP,Email/2006
23245,VO015,Proclima Adhero membrane to speed ramp opening,VPR-000053
21148,VO080,MLA L0 - Roller Door Entrance Flashings,LKA-SI-004
S34131,VO013,Grid F & M1/MB Precast soft Joint Sealant ,
21148,VO081,KRD MLA Additional Emseal Seismic Sealant,SI-004992
22168,VO045,Sealant Remedials Weepholes,
22168,VO046,Supply of Sealant to Services Trades,
23159,VO021,Waterproofing Coating to Level 02,
21148,VO082,KRD MLA Additional Cement Waterproofing,SI-005078
21148,VO083,Additional Western Service Block Waterproofing ,
22168,VO047,Travel VO from yard to site and site to yard,
S34131,VO016,Grid F Internal Capping Beam Plastering ,
22168,VO048,Application of sealant to the flashing,
23159,VO022,PC69 sealant,SI-002676
23159,VO023,Decarb 2 - Detailed Design,COR-000850
23159,VO024,Additional matacryl work to plinths on level 03 roof,CAN508
22168,VO049,Removal & Reinstatement of Link Bridge Flashings ,
22168,VO050,Additional seismic joints to East Building,
S34131,VO014,Micheral Chip to Exposed Membrane ,GCOR-00369
21148,VO084,"LinkSeal Installation to BSQ",SI-005130
21148,VO085,KRD MLA Precast Cored Hole Repairs,SI-005114
23245,VO016,Tender to IFC credit,56787542-3
R444,VO005, Concrete Slab Edge Repairs (curve),CI 219
23245,VO017,Tender to IFC ICONCO-VARPS-000,56788190-7
23245,VO018,Prov Sum Extra value works,56788484-8
23245,VO019,Provisional Sum for Detailing,56788484-8
23245,VO020,IFC freight Costs,56788492-9
21148,VO086,KRD MLA West 200mm Seicmic Joint SI,SI-005175
23245,VO021,"TH01 - Level 4 Stair 1,2 & 3 - Wall Closer Details",SI-002748
22196,VO054,WST Roof - remedials to waterproofing membrane,SI-005189
S34131,VO015,Facade & Seismic Joint Works,
22168,VO051,Grid N3/NG Flashing Remedials,
22168,VO052,Grid N5 Door Threshold Flashings ,
23245,VO022,Extra value weep holes to junction of soakers,46
23245,VO023,Top Soaker to terminate baffle on top of panel joints,47
21148,VO087,Freight Costs - Emseal WFR2,
S34131,VO017,Waterproofing Roofing Works,SI-000135
R444,VO006,Holes through balcony from exiting balustrades,CI223
23245,VO024,ACO Drain Sealant application,
22168,VO053,Northern Breakthrough Waterproofing ,
23245,VO025,Plywood Joints,SI-002839
23245,VO026,Sikalastic 152 to Sump and Upstand,SI-002840
23245,VO030,Air Freight Charges ,SI-002748
23159,VO025,SP2B/Canopy-  Temporary Membrane / Waterproof around Scaffold Pipe / Removal,SI-003200
S34183,VO001, MH - Volclay to Ground Beams Gridline DY1,SI-324
23245,VO027,Seal the timber frame on L3 GL J/17-18,SI-002673
22168,VO054,Sika Floor 400N Coating L1 Stair Landing ,
S34131,VO018,M-03 - Supply and Install of VaproShield Vapro-SS Flashing Tape Over Nuraply System,SI-000148
23245,VO028,Speedramp - Crack Repair,SI-002921
23159,VO026,Waterproofing for tx rooms,SI-003278
S34131,VO019,Precast Joint at window opening - waterproofing,SI-000150
23245,VO029,Concourse East & West stairs landing finishes,SI-002947
23159,VO027,Substrate Repairs prior to Coating Works,Email/2009
S34131,VO020,"L0 Waterbar Replacement ",SI-000153
22168,VO055, Grid NA-N6-N9 Flashing Remedials,
22168,VO056,Balco Seismic Joints,
22168,VO057,Balco Seismic Joints - Air Freight Charges (East Building),
S34490,VO001,Tanking Penetrations,
23245,VO031,"Sea freight Cost- Not Included in $512,506.75 Credit",
S34183,VO002,Pipe Penetrations,
S34183,VO003,RX101DH to Construction Joints,
22196,VO055,Application of sealant and sikalastic 152 on blockwall,SI-005300
S34131,VO021,Temporary Torch On Level 3,SI-000156
S34131,VO022,Additional cost for spotter,
23159,VO028,Waterproofing Coating to All other levels,
S34131,VO023,CR - Grouting Baseplates & Lintel Remedial Works,Email/0210
23245,VO032,Sea Freight - incl Tender to IFC,56788740
21148,VO088,MLA East facade sealant colour matching,SI-005384
S34131,VO024,Supply and install saddle flashing for the termination of the Nuralite system interfacing to the Permatec system,SI-000159
R444,VO007,Concrete column repairs ,CI-259
S34443,VO001,Supply of ALU Vapour Barrier & Primer,SI-737
22168,VO058,North Building Nib Flashing Remedials ,
22168,VO059,Campus Wide- Sealing Precast Panel penetrations,
22168,VO060,Breakout Slab Stegowrap Remedials,
23159,VO029,WP1 - Temporary waterproofing protection,SI-003460
22168,VO061,Grid NA Door Threshold Remedials ,
S34131,VO025,L4 Nib Waterproofing Above Glazed Roof,GCOR-00448
S34131,VO026,Supply and Install of VaproShield Vapro-SS Flashing Tape,SI-000148
S34183,VO004,Waterbar installation to top of Ground beams,SI-426
23159,VO030,WP1 Level 2 CHW Plant Room- Fixing of Internia Base into Waterproofed Plinths,SI-003385
21148,VO090,L3 Mercury Lane Station Waterproofing ,
22168,VO062,MESH Stage 1 Waterproofing ,
22168,VO063,Loading Dock Stegowrap DPM,
S34443,VO002,Nuralite Fixing Plate (Order quantities as per Luke's email #01),SI-850
22168,VO064,WB/Hallmark - Shop Drawing Review,
S34443,VO003,Home Building - Gooseneck Order,SI-911
24110,VO001,Additional waterbar and Sika tape to transformer room polythene,SI-002675
24110,VO002,Sika bentonite installation to slab cutouts,SI-002741
24110,VO003,Tanking penetrations as per Sansom Proposal,email23/10
S34443,VO004,HOME Building - Zone D Pipe Boot Flashings,SI-1008
R444,VO008,Balcony Joint Infill,CI-182
22168,VO065,West Building Courtyard Slab DPM,
S34131,VO027,Install Ryanspan Pro 50- 30mm Thick,SI-000197
S34183,VO005,Lift Pit Rectifications,
23159,VO032,Waterproofing to CLT service penetration,
R747,VO001,Crack & Substrate Injection,Email20/11
23159,VO033,WP1 - SP2B/Carousel - Gas Enclosure - Screed to Fall,SI-003592
22168,VO066,North Building Weep Holes,
S34182,VO001,Early Tanking Works -ATP ,
21148,VO091,"Additional EFVM Visits ",
21148,VO093,B6 Sump Injection & Coating Remedials ,
21148,VO094,Materials Off Site,
S34194,VO001,Level 2 Deck waterproofing - Plinth and Infill Details,R710VO026
S34131,VO029,CR: Grouting to Base Plates,SI-000170
S34131,VO030,CR: Concrete repairs,SI-000170
S34131,VO031,CR: Structural Columns (Columns to Wall Interface),SI-000170
S34131,VO032,CR: Grouting of Plates (Plates to Walll Interface),SI-000170
S34131,VO033,CR: PFC Grouting,SI-000170
S34131,VO034,CR: Supply Electric Scissor Lift,Email 20/1
S34183,VO006,MH - Volclay Lift Pit & Ground Beams,
S34131,VO035,Sika AT Façade to the joints between the Precast lids,SI-000239
S34131,VO036,Temporary Waterproofing,SI-005695
23159,VO035,PC68 HV Rooms: Temporary bunding and torch on (URGENT),
S34490,VO002,Aquaron Coating to Upper Concrete Slab ,
S34490,VO003,Additional Preprufe 300R to Upperslab,
22168,VO067,Additional Pipe Detailing to Laid Slabs ,
22168,VO068,Balco Seismic Joints - Air Freight Charges (West Building),
23159,VO036,"L1 Temp waterproofing. GL 35, IA, 36A",
S34248,VO001,"Penetration Detailing to Apartments 301,303,305 & 307 ",
21148,VO095,BSQ Dwall Waterproofing Injection ,SI-005640
S34131,VO037,Materials Off Site,
R444,VO009,Concrete slab chase repairs - Apartment 5E and 7A ,CAN 85
22196,VO056,Aotea Station Façade Works,
S34131,VO038,GL-M1 Replace damaged Ryanspan ,SI-0002602
22168,VO069,Seal doors in south substation,
22168,VO070,West – Loading Dock Ramp Bituthene Remedials ,
R444,VO010,New concrete nib - Ground floor,CI-272
S34593,VO001,Additional Works B2-141 - Dressing room 9,
S34183,VO007,Sealant works on isolation joints,
22196,VO057,Waterproofing strip to seismic nib,
S34131,VO039,Level 3 column dry packing,SI-000273
S34528,VO001,Nuratrim termination detail – Stage 2,email14/01
22168,VO072,Install QuietJoint to joint at Room G38,
S34131,VO040,Volclay Waterstop and Seismic Cover Flashing,SI-000285
S34443,VO007,Shed - plantroom roof TPO goosenecks,SI-1492
22168,VO073,Seal gaps between wall and BALCO seismic,
S34131,VO042,Goose neck for lightning cable,SI-000292
21148,VO096,Additional ILD Visit South Western Corner ,SI-005771
21148,VO097,"Additional Protection Sheets to West Elevation Membrane ",SI-005792
S34131,VO043,Mayoral Drive Entry Waterproofing,SI-000291
22196,VO058,Crowne Plaza Airbridge Waterproof Membrane,SI-005811
S34443,VO008,Nuratrim to Edge Termination of Aux Roof,SI-1589
S34443,VO009,Membrane to Aux Roof,SI-1400
21148,VO098,BSQ precast panel,SI-005809
S34443,VO010,HOME Building - Warm Roof,SI-1646
S34131,VO045,Pipe Boot Flashing,SI-000326
S34443,VO011,Shed Building - Additional Works to Roof,SI- AAN 32
S34182,VO002,Credit Early Tanking Works - ATP,
22168,VO074,East Building - Splicing Cabinet 03 Junction Box,
23159,VO038,Remove existing chevaline dexx ,SI-004215
21148,VO099,Additional ILD Visit to SW Corner ,
21148,VO100,BSQ Access Hatch Waterproofing Works ,SI-005809
S34194,VO002,Hiab for Vertical Lifts,VDRCT 311
S34248,VO002,"Penetration Detailing for Apartments 300,302,304 & 306 ",-022016
S34131,VO046,Temporary Waterproofing to Roof ,
22196,VO059,Crowne Plaza Airbridge Waterproof Membrane-Repair at the northeast corner,SI-005892
S34131,VO047,L1 Grid E9/EA-EB Wall Surface Prep ,
S34248,VO003,SP1 Stand Down Time ,
R444,VO011,Concrete Slab Chase  Repairs Unit 7A,CI382
S34528,VO002,Membrane works,EMAIL2/3
S34183,VO008,Sikalastic 152 to Window Sill,SI-720
S34131,VO048,L2 Sealant Joint Against Column ,SI-000291
21148,VO101,KRD MLA roof chiller plantroom weatherproofing,FCR-060505
S34248,VO004,"Link Seals to SP3 ",SI-373
S34490,VO004,Chevaline Dexx to Northern Deck ,
S34490,VO005,Ardex to Entrance porch ,
S34528,VO003,Transformer Roof Variation Proposal,Email12/3
S34443,VO013,Chaveline Dexx to Shed Building L2 LMR room,AAN471
R344,VO003,Monthly H&S Meeting,
R344,VO004,Staff Training,
R344,VO005,HR Meeting,
S2302,VO001,Monthly H&S Meeting,
S2302,VO002,Staff Training,
S2302,VO003,HR Meeting,
S2302,VO004,H&S Committee,
R344,VO006,H&S Committee,
S34131,VO049,Vaproshield Tape to Lift Overun ,SI-000377
23159,VO039,WPM Sealant for Economech VSD Fixings,SI-004393
S34182,VO003,Pipe Penetrations to Tanked Pits ,VR-000001
S34578,VO001, Air Freight Charge,
21148,VO102,Mapelastic to Eastern Upstand & Matwell Area,
21148,VO103,Pipe Penetrations,
22196,VO060,Roof Remedial Works,
S34183,VO009,Joint Sealant Works,
S34490,VO006,Pool Services Penetration Detailing ,
S34323,VO003,Long Service Prezzy cards,
S34443,VO014,Warm Roof Zone D PIR design issues,Email/2503
S34443,VO015,Warm Roof Zone D PIR design issues,CAN-451
S34443,VO016,Nuralite Fixing Plate (Order quantities as per Luke's email #02),SI-2264
S34443,VO017,DELETION OF NURALITE VAPOUR BARRIER TO HOME BUILDING ROOF – CREDIT,Email/2503
S34131,VO050,Screed Credit,SI-286
S34443,VO018,HOME Building - Membrane Patching ,SI-2077
23159,VO040,Supply and install of Monkey toe foot pads ,SI-004508
22196,VO061,Sikafloor Multidur EB-31 Coating ,003544
S34194,VO003,L4 Parapet separation flashing,VDRCT-0004
23159,VO041,Seal as directed areas on pc68 roof,SI-004597
R444,VO012,Slab Infill for Wastes CMBND,CI425
23159,VO043,Rain Preperation - Temporary Waterproofing works,SI 4657
S34182,VO004,EBS Pit - Sikaproof to EBS 125 Credit ,
S34131,VO051,Roof -Sika Hyflex Facade Sealant,SI-000421
S34593,VO002,Basement Level 2 Kitchen - Remedial Waterproofing,
S34131,VO052,Supply of collars for copper pipe on level 4 roof,SI-000439
S34182,VO005,Re Detailing of Pipe at Service Pit (Grid D5/H10) ,SI-000708
S34131,VO053,Transformer Room Trench Injection,SI-000468
S34482,VO001,Lift Pit B1B Structural Toe Changes  ,SI-000112
S34490,VO007,Additional Torch on Works,
S34490,VO008,Additional Works to Pool side/Garden box,
21148,VO104,BSQ - Station Perimeter Mapelastic Remedials ,
22196,VO062,Supply of Sikafloor 377 to Air Bridge ,
S34131,VO054,Level 2 Sealant,SI-000462
22168,VO075,West - SIKAFloor Coating to Trolley Wash ,
S34323,VO004,H&S meeting Woolworths vouchers,
S34131,VO055,L4 Mechanical Louver Details ,SI-000327
S34131,VO056,Supply & Installation of Bitumen Fillets ,SI-000476
S34131,VO057,Heritage Roof Revised Details ,VPR-000073
S34248,VO005,Post Applied Bentonite Detailing,SI-420
23113,VO003,"Roof upstanding penetration, repair, concrete wall and gutter",SW-SI0003
22168,VO076,North Link Base Bituthene  Remedials,NCR-000172
22168,VO077,WB - Metcom 7 cladded wall door sealant,
S34443,VO019,L2 open deck missing penetration,SI-2401
S34443,VO020,HOME Building - Supply of Allco Barrier Tape,SI-2418
S34443,VO021,HOME Building - Boot / Gooseneck / Sleeve Order (ROOF),SI-2407
22196,VO063,Sikafloor Car Park Deck System to Crown Plaza Airbridge,
22168,VO078,Application of Dowsil 688 to Penetrations ,
22168,VO079,Application of sealant around door joints,
S34131,VO058, Level 4 Diesel Exhaust Flashing,SI-000503
23159,VO045,"AIAL WP1- Terminal Integration  - Flood testing to remaining gutters",CAN414
S34131,VO059,Main Entry Canopy Remedial Works to Upstand,SI-000505
S34131,VO060,Additional Sika Hyflex Sealant - Level 2-5,SI-000504
S34183,VO010,Sika EMSEAL boot flashing,SI-954
23113,VO004,Existing Membrane and Exterior Concrete Deck Waterproofing,SI0004
S34248,VO006,CC Laundry & Pool Room Existing Penetrations Remedials ,SI-530
S34131,VO061,Sealant to Grid M2 - Abseiling,
22196,VO064,Additional Waterproofing & Flashings over Exposed Foundations ,
S34131,VO062,Damage to Nuraply Membrane on Heritage Roof,SI-000512
S34182,VO006,Sprinkler Valve and SW Chamber to EBS Pit Waterproofing ,
22168,VO080,WB/Loading Ramp Base Flashing Remedials ,
21148,VO105,L2 bolts waterproofing,SI-006157
21148,VO107,Additional Sealant to Lourve Openings,SI-003300
22168,VO081,NB zone 4 waterproofing and flashing over foundations,
S34131,VO063,Waterproofing Pipe Penetrations to Vector Ducts ,
S34194,VO004,CPRW Waterproofing CANS - Combined,VDRCT 421
S34490,VO009,Powder Room and Storage – Newtons,
R444,VO013,New Concrete Nib Extension & Concrete Topping,CI-464
S34182,VO007,Additional Works for Sprinkler and Sewer Chamber,SI-000866
21148,VO108,Waterproofing HDPE Pipes,SI-006215
S34443,VO022,Seal base plate,SI-2833
21148,VO109,Northern elevation cores sealant,SI-006220
S34443,VO023,Seal pre-cast stairs,SI-2298
S34360,VO001,L2 Meeting room & Office,
22168,VO082,Sealant around doors using Dowsil 688,
S34754,VO001,MMH building C88 Manawanui meeting house,WO55351
S34754,VO002,"Carrington Site  -C03 Rehab Plus, Pt Chev / Ground Floor ",WO55557
22168,VO083,Sealant to exposed Screws under windows ,
S34754,VO003,101 Sarsfield Street - Deck leak investigation (Urgent),Email12/06
S34754,VO004,"Auckland Hospital - Building A01, Support Building AK / 16th Floor",WO #55763
S34754,VO005,Auckland Hospital - Building A08 Oncology AK,W/O #55896
S34183,VO011,Sikafloor 2510W to Lower Ground Floor Plant Room Plinths,
S34183,VO012,"Waterbar installation in Energy Pit - concrete wall and slab joint , pipe penetrations",SI-1121
R444,VO014,Repair Concrete Nib wall and Saddle flashings aligning to cladding,CI 453
S34754,VO006,"Greenlane Hospital Building G16 Related work from WO #55612 and WO #55492",WO #56080
22196,VO065,Planiseal MR Green Concrete Coating ,
21148,VO110,Beresford Square Mapelastic Smart ,
S34772,VO001,Temp and final detailing for posts to deck,Email 2306
S34754,VO007,"56123/ 55007 - Greenlane Hopsital - Building GO4, 6th Floor",WO 56123
S34754,VO008,"Greenlane Hospital, Building G15 Greenlane / 7th Floor relates to w/order 53116 and 56312",WO #56312
21148,VO111,Adit A1 Closure Additional Items ,SI-006279
S34182,VO008,Re-taping of Column Joints,SI-000993
S34131,VO065,Grid EJ Blockwall Wateproofing ,SI-000601
S34490,VO010,Swelltite to Retaining Wall Behind Stairs ,
S34578,VO002,SP1 Level 1 and 2 Grid E+ seismic joint & Emseal,CI#101.20
S34591,VO001,Reprofiling of Piles,
S34754,VO009,Greenalne Hospital Building G01 Greenlane,W/O 56556
22168,VO084,Seal door frames at north substation ,
22168,VO085,WB-W5/W6 Courtyard Remediate to Waterproofing,
23113,VO005,Membrane Roof Termination,
S34754,VO010,"Auckland Hospital AO1, L16 Plant Room - Tank Room (PR0117)",WO #58171
23159,VO047,PC68 MSB-B/TX waterproofing protection,SI 5111
S34131,VO066,Level 2 Courtyard - Exhaust Duct Precast Panel,SI-000657
23159,VO048,Level 2 Grid IA - Seismic Gap - Install Temporary Roof - Waterproof ,SI-005134
S34754,VO011,Auckland Hospital L16 -AO1 Support Building,w/o 83828
S34754,VO012,"Auckland Hospital - Ceiling Leak Investigation A35 - Te Whetu Tawera - Acute Mental Health Unit room 1.156",WOT0084812
S34131,VO067,Site Waterfeed Waterproofing ,SI-000676
S34443,VO025,Torch on membrane remedials,SI-3437
S34131,VO068,L0 Gid EJ Nib Wall Waterstop ,SI-000669
R444,VO015,Prep work for Concrete Beams on North Balconies,AT1159/926
S34591,VO002,Bund site concrete/pile upstand with Sika Plug,SI-80
S34443,VO026,Shed - Canopy Saddle Flashing Detail,SI-3268
S34754,VO013,Auckland City Hospital A21 - Wall Penetration Repairs,
S34624,VO001,Off-Site Storage Cost,
22168,VO086,Additional EPDM on east link verticals ,
S34591,VO003,Pile 26 Additional Work,SI-92
S34591,VO004,Pile 58 Remedial Works,SI-98
23159,VO049,WP1 - SP2C - Level 2 Grid IA - Seismic Gap - Removed Waterproof over the stair plate,SI-005237
23159,VO050,Chevaline Dexx to Hyd Riser – Level 02,
23159,VO051,Additional Waterproofing Coating to Ground and Ground Mezz,
S34183,VO014,Stand By Time,
S34443,VO027,Metal Yellow Cladding Sealant,SI-3661
S34591,VO005,Remedial to Pile 4 edges in Zone 3,SI-104
22168,VO087,WB - Scissor Lift Pit ,
S34443,VO028,Design Change and Temporary Termination Works Due to Staging,
S34443,VO029,Credit for VO008 as per revised Nuratrim rate,
S34528,VO004,Nuraglaze to Stage 1 & 2 Membrane Areas,
S34131,VO069,Level 0 Trench in GF Slab,SI-000634
S34131,VO070,Laundry Services Penetration Waterproofing ,SI-000652
S34131,VO071,Roof Detailing to Threaded Rods & Steel Posts ,SI-000621
22168,VO088,North Substation waterproofing remediation,
R444,VO016,Self levelling credit,Email24/07
23159,VO052,Water-proofing to Temporary UC Prop Penetration at E4 &E5/VVa,SI-005299
S34443,VO030,Home Building - Warm Roof Inspection,SI-3730
S34443,VO031,Torch-on Termination & EPDM Air Seal,SI-3390
S34443,VO032,Home Building - Open Warm Roof to Inspect Chord Plate,SI-3746
23245,VO033,Level 4 Office Plant Waterproofing,SI-003357
S34065,VO001,Z1 - Unbonded Waterproofing Generator Pits,SI-001274
S34443,VO033,Seal pipes penetration through slab,SI-3676
23159,VO053,Prep for Column Top Plates on L2 Mezz,SI-005339
22168,VO089,Nib Remediation to External Doorway Openings,
S34131,VO072,Waterproofing Membrane to Heritage Parapet Capping,SI-000758
S34131,VO073,Grid F External Precast Panel Sealant,GCOR-00896
S34545,VO001,Additional Pile Detailing,SI-000222
S34545,VO002,Supply and Install Sika Blackseal/Fosroc Mulseal,SI-000234
S34772,VO002,Joinery Remedial Waterproofing,
R444,VO017,Slab extension (level 3 and 5) ,CI-546
S34591,VO006,Additional detailing to Pipe penetration,SI115
S34443,VO035,Sealant Between Building and Pavement ,SI-3934
22168,VO090,West Substation Waterproofing Remedials ,
S34443,VO036,L2 Pipe Penetrations Waterproofing,SI-1027
S34545,VO003,Replacement of Waterbars,SI-000286
S34545,VO004,Additional Waterbars,SI-000286
S34443,VO037,Home Building - Gooseneck Order for PV DB's,SI-3891
S34754,VO014,Greenlane Clinical Centre - Head Flashing Repair,WOT0105309
22168,VO091,New Clean Loading Dock Stegowrap ,
22168,VO092,Northern and Western Plantroom - Coating,
S34591,VO007,Pipe Penetration Detailing,
S34591,VO008,Additional for Preprufe Detailing to Pile Setdown,
S34545,VO005,EDS Sump Remedials,SI-000442
S34131,VO074,Level 4 - Oil spill on roof area - Remedial on Contaminated Waterproofing ,SI-000815
S34131,VO075,Chemical Discoloration on Plant Roof Membrane ,SI-000829
S34194,VO005,Level 2 Deck Generator Structure – Plinths (GCOR-000111),R710VO77
S34131,VO076,L2 Egress Stair Seal and Flashing,SI-000816
24110,VO005,H165 insitu concrete HV jointing pit ,SI-4767
S34323,VO006,Cricket Costs,
24110,VO006,SP5 PC68 Trench,SI-5426
S34182,VO009,Waterbars to Level 1,SI-001574
S34443,VO040,Home Building - Lagged Pipe Detailing,SI-4118
S34183,VO015,Low profile water for link bridge LG,SI-1505
S34183,VO016,Waterbars and sealant works in the link bridge pockets and part of the main building,
R444,VO018,Apartment 2B Concrete Column Remediation,CI 461
S34443,VO041,HOME Building - Allco Barrier Tape Order,SI-4137
S34131,VO077,Level 0 Canopy Down Pipe - Tile Penetration Cover Flange,SI000853
22168,VO093,Seismic Joints - Scope Changes for North & West Buildings,
S34131,VO078, T Flashing Trim,SI-000871
23159,VO058,L2 Mezz anchor plate waterproofing  ,SI-005623
S34042,VO001,Temporary termination  to Podium Sumps,SI-V-00025
S34183,VO017,Sikafloor 2510w to Plantroom floor,SI 1262
23159,VO059,L2 grid IA nib waterproofing ,SI-005658
S34467,VO001,Bitumen Fillets to Plywood Substrate,SI 40
23159,VO060,L2 E4M platform WPM remedials/repairs,SI-005673
22168,VO094,Sika QuietJoint SHH - Air Freight Charges ,
R444,VO019,"Floor Levels In Existing Lobby, New Gym, Entrance",CI 579
22168,VO096,Overflashing on Grid N5/NJ+ ,
22168,VO097,West Building Courtyard Flashings,
S34131,VO079,Supply and install stainless steel door thresholds,SI-000917
S34545,VO006,Elect - LV Switchroom - GL11 Additional Electrical Conduits,SI-00044
S34131,VO080,Additional/Change in Scope - Mayoral Drive Entry Waterproofing,SI-000291
S34131,VO081,Void Room Wall Flashings ,SI-000826
S34545,VO007,Waterproofing to lift pit wing wall ,SI000322
S34545,VO008,PVC water bar and additional detailing  ,SI000429
S34482,VO002,Application of Dowsil 790 to Spandrel Panels,
S34131,VO082,Provisional Sum for Future Variation Works,
22168,VO098,Post detail works west plant room,
22196,VO066,Aotea air bridge BAS expansion joint,
22196,VO067,Sea freight for BAS Parking Span 150 expansion joint,
22196,VO068,Supply and apply epoxy grouting to gap between substate and expansion joint,
S34754,VO015,"A02 - Starship Children's Hospital A02 L1 - HDU Lounge",WOT0121636
S34754,VO016,"A01 - Support Building Floor: L4 - Level 4",WOT0118127
S34443,VO043,Home Building - Level 00 Zone 3.3 Fenz Roof,CI 1815
S34443,VO044,Home Building - CLT Stairwell at Roof Level,SI-4365
R344,VO007,KiwiRail medicals / Tunnel operations,
22196,VO069,Aotea foul water sump – Additional Floor Coating (Sikagard 62),SI-006349
R444,VO020,Concrete nib cut on Ground floor,1159/1209
R444,VO021,Level 8 Grinding/ Cleaning of balconies,1159/1206
22168,VO099,Install of compressive foam - loading dock,
S34443,VO045,Home Building - Roof Peno Size Increase,SI-4414
R444,VO022,Seal Drilled Scaffold Holes,1159-1243
R878,VO001,Structural Column Investigation,EMAIL7/10
R444,VO023," Sikafloor Level 30 ",CI 650
R878,VO002,Grinding as advsied - M² allowed for - 60m²,Email8/10
S34545,VO009,GL C Membrane repairs,SI-000493
21148,VO112,Flashing Around BSQ Louvre Fixing Angle ,FCR-065250
S34131,VO083,Sikalastic 152 to Entrance Opening ,SI-000943
22168,VO100,Water Plantroom Floor - Coating,
S34042,VO002,Prep work for water proofing the podium gutter sump,SI-000278
S34754,VO017,"A32 - Auckland City Hospital (Main Building)  Level 9",WOT0130811
22168,VO101,Rectify Waterproofing West Building Loading Dock,
R444,VO024,CI-483 - Ground Floor MV001 APPRVD,CI 483
23159,VO061,CAN - 844- Additional Detail for Concrete around Unistrut supports,SI-005825
S34591,VO009,Replacement of waterbar on stitch joint,SI-255
S34545,VO010,EDS - Removal and reinstatement of water bar,SI-000540
21148,VO113,TVS & ADIT A1 Drained Floor Injection,
23159,VO062,Working outside of Ordinary hours to apply the 2 x Topcoats,SI-005840
S34248,VO007,SP3 Pipe Remedial ,SI-989
22196,VO070,Application of 11FC Black to the station facade,SI-006576
R878,VO003,Beam Demolition,Email 20/1
21148,VO114,SW Mercury Lane Station Corner Reinstatement of Membrane Protection ,
S34065,VO002,Credit - Original Contract Schedule,
S34065,VO003,Auckland Airport Domestic Processor Pier & FLB Tanking Works,
S34042,VO003,Additional Grinding for Podium gutters prep,SI-00028
S34042,VO004,Podium - Gutters Temp Protection Supply,SI-00028
S34545,VO011, New Rebate Zone 1 preprufe detail  ,SI-000286
S34545,VO012,Additional Pipe detailing to LV room,SI-00044
R444,VO025,Column L2 Repair (RFI 269),CI 503
R444,VO026,Repair of 7A chase,CI 649
S34874,VO001,Additional Waterstop,PO 197054
22168,VO102,Credit for West Building Coating Traxx 2000 Coating Removed from Scope ,
22168,VO103,Clean Loading Dock DPM SW10-01 ,
22168,VO104,BALCO Boot Flashings to Breakout Zones ,
S34543,VO001,Pipe penetrations to perimeter of lift pit/underslab interface,
S34874,VO002,Commercial Discount ,
22168,VO105,North Building - Balco Air Freight Charge,
S34194,VO006,New plywood plinths membrane detailing ,R710/VO088
S34194,VO007,Stair 4 Vestibule concrete nib at steel beam ,R710/VO089
S34467,VO002,ILD Testing 2 Additional tests to Upper Gutters ,SI 48
S34248,VO008,Credit VO-005 Allowances ,
S34194,VO008,Stair 4 Vestibule reclad (Level 2 deck level),R710VO090
S34443,VO046,Re-detail around top section of 3qty fan penetration upstands,SI-4578
24110,VO007,Additional tanking work,
S34131,VO084,Credit Adjustment - Facade Sealant,
S34443,VO047,Replace 7 Nuralite Fixing Plates to Level 2 ,SI-4577
23159,VO063,L2 CHW plantroom WPM remedials,SI-005886
S34545,VO013,Detailing to piles,
S34593,VO003,Wintergarden Area Newtons CDM Works ,
23159,VO066,WP1 - SP2C - Level 1 Grid 35 - ED - VVA - Removed Temporary Waterproof,SI-005900
S34443,VO048,Reposition of Duct Peno - L3 Roof,SI-4618
S34443,VO049,Additional Build up to 1qty Roof Fan Upstand,SI-4617
R444,VO027,Concrete column repairs ground floor.,1159/1323
23159,VO068,CAN 958 L2 Roller door gap infill around skirting,SI-005771
22168,VO106,Remove 6GWC-3 Cover Plates & Reinstall,
21148,VO115,Penetration Infill ,SI-002860
S34543,VO002,Sealant to block wall to allow MSB to be installed,
S34545,VO014,Zone 2 repairs due to concrete splatters,
22168,VO107,West Generator Room Door Sealant ,
S34042,VO005,Podium - Gutters Temp protection Supply & Sill Protection ,VO-000047
22168,VO108,Cetcoat to Loading Dock Slab/West Generator Interface ,
S34443,VO050,Lightning Cable Penetration Through Roof,SI-4732
S34545,VO015,Zone 2b pour stop ends – Additional CJ tapes and Replacement of Waterbars,
22168,VO109,Nib Flashing/Window Clash Cuts Works  ,ACXC-00367
S34631,VO001,Early Works,
S34545,VO016,Zone 2 - Hole in waterproofing from formwork removal,
S34591,VO010,Credit: Additional for Preprufe Detailing to Pile Setdown,
R444,VO028,Boxing and pour underside the core,ATS1159/13
S34874,VO003,Additional waterstop to Aco Drain,PO 197057
23159,VO069,3.03 Platform East WPM Remedials,SI-005972
S34623,VO001,Auckland Transport Hub - East & West Concourse chase cutting,SI-003475
22196,VO071,D-Wall Injection at BOL Platform,SI-006729
21148,VO116,UA and sealant application to the fibre glass tank joint,
R444,VO029,Ground Floor Nib GL 5-6/I,CI 728
22168,VO110,NB - Door Flashing Remedial,
S34182,VO010,Sikaproof P to side of beams + Sikaproof A tape termination to DPM ,SI-002415
S34591,VO011,Sealant Waterproofing details,SI-281
21148,VO117,Adjust Flashing,SI-004988
S34482,VO003,HDPE & Termination to Revised Area,
S34482,VO004,Geofabric & Testing to Revised Dragowrap Scope ,SI-420
S34482,VO005,Dragowrap Vapour Barrier to B1A & B1B,
24110,VO008,Sika Seal Tape B & Waterbar to Joints,SI-004692
S34543,VO003,RX-102 Replacement,SI-4590
R1059,VO001,UoA Autoclaves Replacement (Subsequent Visits) – Floor Coating – 143 Park Road (Autoclave 1 Only),MCA-1
S34578,VO003,MV66 Cross Brace Strengthening,
23245,VO034,Leak at stair 2,GCOR-03916
S34482,VO006,Temporary Waterproofing to L3 Columns ,SI-000562
S34443,VO051,Mechanical Penetration Size Increase - Roof Level H15, SI-4865
S34543,VO004,GARAGE Building - Matacryl Detailing,SI 4721
S34482,VO007,Sikadur 42 to Service Pipework ,SI-000550
22168,VO111,Flashing Cut Outs for Damaged Copper Pipework ,
R1112,VO001,RPO Protection cost,Email 4/12
R1112,VO002,Cutting of 400 x 16 SHS Beams,Email4/12
R1112,VO003,Transporting of 400 x 16 SHS Beams,Email 4/12
R1112,VO004,Infill of Wall Pockets,Email 4/12
S34443,VO052,Zone 3 Roof Cowl,SI-4883
21148,VO118,Mercury Lane - Sealing pipe annulus gap between D-wall and pipes,SI-006847
S34578,VO004,Seismic upgrade and weathertightness remediation,
R1112,VO005,Additional Starter Bars in Wing Walls ,Email 5/12
R1112,VO006,Bridge BR43 MSL Impact Beam Replacement - Additional FRP,Email 5/12
R626,VO001,Dead time Dec 25,Dec 25
23159,VO070,Drain Connection to mechanical plant,SI-005616
S34183,VO019,"Credit - VO11, VO13 & VO17",
S34183,VO020,Sika Floor 2510W,
S34545,VO017,Zone 3 - Replacement Preprufe,SI-000688
S34194,VO009,Alsan Flashing Quadro Termination Detail to Stairwell,SI-000658
S34194,VO010,Spotter – Chevaline Coverflexx System ,SI-000655
S34194,VO011,Level 2 Membrane ILD re- testing ,SI-000656
22168,VO112,GF - Slab & Window Flashing - Protection Layer on Flashings,
22168,VO113,Supply of Stegowrap for SC01 Plint & Retaining Wall Foundation ,
22168,VO114,SW Courtyard Channel Drain Changes,
23159,VO071,WP1- SP4-L2 Waterproofing remedials.,SI-006038
R1112,VO007,Sandblasting of Impact Beams,Email 9/12
22196,VO072,Termination of the existing Wabo Expansion Joint at Planter Box,SI-006838
R1112,VO008,Corbel Extension,Email10/12
S34443,VO053,Zone B Roof - CEF2.1 & TEF2.1 Swap,SI-4923
24110,VO009,Tanking to Additional Trench,SI-004692
S34482,VO008,Dragowrap Patching Remedials ,
S34482,VO009,Service Penetrations through Dragowrap & HDPE ,
S34482,VO010,Additional Termination Bar & Sealant to Dragowrap ,SI-000597
S34482,VO011,Additional Detailing to HDPE & Dragowrap due to 500mm and 100mm steps in Prep Level,
S34482,VO012,Membrane repair to slab thickening ,GCOR-01601
R1059,VO002,UoA Autoclave 2 & 3 Replacement Coating (SI-7),SI 7
S34683,VO001,Additional Scope - Tanking,
S34194,VO012,L2 deck - Stair and ladder plinth membranes,SI-000661
S34543,VO005,L3/L4 Damaged Waterbar ,SI 4929
23245,VO035,Chase Cutting East and West Concourse,SI-003475
22196,VO073,Expansion Joint Wet Seal Rework,SI-006892
23159,VO072,Membrane Detailing Works to Seismic Junction,
S34972,VO001,Provisional Sum as Quoted,
S34543,VO006,Aquafin 2K to Nib - Ground Floor G5/GK to G5/GL,SI-5032
R765,VO001,Common Room Balcony,AKL5053389
S34772,VO003,Nuratrim Works,
S34754,VO018,"Greenlane Clinical Centre Building: G16 - Cornwall Complex, - Ground Floor ",WOT0150142
23159,VO073,Additional Line Marking to Level 02,
22168,VO115,NB Over Flashings to Ground Beams ,
S34982,VO001,Concrete fix and remedial works,
S34591,VO012,Membrane Repairs - Damage to waterproofing GL 9,SI-405
S34065,VO004,Supply and installation of Geo textile,SI-002996
S34482,VO013,Supply only 2x Scuppers,SI-000670
S34443,VO054,1m2 Cutout for Lagged Pipe Box,SI-5098
S34065,VO005,Pipe penetrations through membrane,SI-003273
21148,VO119,BSQ Dwall & Pipe Penetration Works ,SI-006932
S34528,VO005,Double Layer Membrane to the Gutter ,EMAIL21/01
S34443,VO055,Nuralite Bracket to Replace,SI-5114
S34897,VO001,Working After Hours,
S34228,VO003,Window Leaks,
S34444,VO001,Detailing of Existing Pipework,Email/2701
S34443,VO056,Roof Fan Peno,SI-5145
S34754,VO020,Auckland City Hospital - A08 - Cancer & Blood Services (Oncology),WOT0176495
S34754,VO021,Greenlane Clinical Centre -G15 - Cornwall Complex,WOT0176393
S34754,VO022,"Auckland City Hospital A02 - Starship Children's Hospital L7 - Level 7",WOT0175655
S34766,VO001,Digging External Pump Chamber ,
22168,VO116,Plantroom Floor Painting Touch-ups Out of Sequence Works,
22168,VO117,Re-install ISWM Balco,
S34042,VO006,Podium - Light Grinding prep for waterproofing,SI-000391
S34772,VO004,Epoxy Infill to Window Rebate,
22168,VO118,Additional Penetrations x3,
R444,VO030,Block wall outside GF west bay window,CI-824
S34482,VO014,Supply Equus Seperation Layer Tape for Box Gutter Detail,SI-000717
S34545,VO018,Waterbar replacement zone 3,SI-000911
S35021,VO001,Supply and installation of Swelltite membrane to exterior garden box,
S34183,VO021,Staff Entry DPM ,SI-1305
22168,VO119,N1 Waterfeed Pipe Waterproofing Remedials ,
S34545,VO019,GL E - Termination Detail,SI-000942
S34982,VO002,Additional costs - long weekend works,
S34543,VO008,Aquafin 2K W/Proofing to face of Nib,SI-5238
23245,VO036,Waterproofing around slab penetrations,SI-003482
22168,VO120,Fabricate and install Balco cover,
23159,VO074,WP1: L3 Roof - Removeable Walkway Drawings - additional waterproofing,SI-006132
R444,VO031,Additional nib adjacent to front entry,CI-856
22168,VO121,NB Stegowrap Protection to Flashings Stage 002 ,GCOR-01709
22196,VO074,V11 Lift Sump Leak Repairs ,SI-006993
S34183,VO022,Replace damaged Balco cover plate,SI-2056
S2302,VO006,Mask fitting,
S34443,VO058,Nuralite Brackets Tender Allowance Credit,
S34545,VO020,Zone 4 L1 Slab Works,SI-000993
S34999,VO001,Supply and Installation of Glass Slider,
S35023,V001,Travel & Away Allowance,
S34543,VO009,Garage Building Roofing,
S34582,VO001,Membrane reinforcement over cracks,
S34582,VO002,Supply and install of bollards,
S34582,VO003,Supply and Install of Wheelstops,
S34582,VO004,Scaffolding and Shrink Wrap,
23159,VO075,WP1 SP4 Waterproofing remedials.,SI-006251
R1046,VO001,Excess Sika Carbodur BC12 NSM Rods First Floor,Email 25/2
R1046,VO002,Sika Carbodur BC12 NSM Rods First Floor Change in slot Dimensions,Email25/2
S34543,VO010,Sealant to Block Walls,SI-5263
S34466,VO001,Boundary Wall Temporary Waterproofing ,
S34981,VO001,Back Up Pump Preparation & Installation ,
22168,VO122,West Generator Remedial Items ,
S34897,VO002,Extra Mobilisation Cost,
S34897,VO003,Takanini Station Swelltite Repairs ,
S34897,VO004,Additional Waterbar to Lift Pit Wall/Slab Interfaces ,
S34194,VO013,Rainwater Leak from L2 Deck into Golf Lounge - Membrane Plinth Works,P0003974
R1028,VO001,Investigation,Email27/02
S34543,VO011,Crash Barrier & Bollard Fixings,SI-5341
R1104,VO001,Medical Vaccinations and Contractor Inductions,Email2/03
R1046,VO003,Remedial for damaged mesh near Grid AU on Level 1,SI-65
R1046,VO004,Remedial penetration works under CAN ST 17 Rev 1.,SI-64
S34545,VO021,Removal of Preprufe,SI-001050
S34443,VO060,Zone A Upstand Resize Works,SI-5436
23159,VO076,L3 Door Sill Flashings,SI-006253
S34477,VO001,Additional Costs,
S34183,VO023,Plant Area Credit,
S34183,VO024,Precast Jointing Variance,
S34631,VO002,B240 Basement Floor Remediation Works,SI-000564
S34631,VO003,Blackseal to UC columns,SI-000549
S34477,VO002,Material Cost Escalation,
R776,VO001,PS 1 Design for Bulge Repair,48974723
R1046,VO005,St Lukes Gardens Crack Repairs,SI-74
R1194,VO001,Concrete repairs to masonry at Stanbeth Building - Helifix,Email 09/3
S34648,VO001,Grid Z/D - Apply Sikadur-32,SI-58
R1001,VO001,H47 wall repair ,Email 10/3
22168,VO123,Procure and install Additional Flashing N-6 ,
S34591,VO013,Adjust waterproofing terminaton on GL:E,SI-535
S34443,VO061,Final Nuralite Fixing Bracket Order,SI-5479
22168,VO124,NB- B3 Breakthrough - Stage 4 MESH- Framing alteration to suit Balco,
17221,VO001,SVB podium works ,PO 10695
S34444,VO002,Credit Planter Box Structural Repair Works ,
S34444,VO003,Revised Planter Box Structural Repairs ,
S34444,VO004,"Investigation, Digging & Remediation of Planter Beside Entrance Ramp ",
22168,VO125,Procure and install sacrificial transition flashings,
22168,VO126,Emseal Gap Filler,
R878,VO005,Stage 1 Column Reinstatement,SI 11
S34981,VO002,Supply and install new probes as the previous probes were missing,Email/2003
22168,VO127,N11 Threshold/Drain Remedials,
22168,VO128,N6 Equatone Ceiling BALCO Flashing ,
22168,VO129,Water Based Proofer/Sealer Coating to all exposed concrete- CO-501,
R937,VO001,Materials  on site,Email23/03
R878,VO006,Men Change Rooms columns,SI 11
S34443,VO062,Staff Canopy Deflection - Remedial,SI-5580
S34443,VO063,5qty Nuralite Brackets,SI-5577
S34539,VO001,Supply and install Scuppers,SI-571
R1001,VO002,H47 addition joints repair,Email24/03
S34763,VO001,Credit Value of works - Aquadrain Deletion,
R1001,VO003,Item 3 - Concrete Repairs,Email25/03
S34545,VO023,Membrane Termination Detailing with Silcor HB Band of 500mm,
S34545,VO024,Membrane Detailing of Membrane with Protection Sheet of NPX Layer,
S34545,VO025,Detailing to Retaining Wall as per Structural Setout,
S34482,VO015,"Credit - Drago Wrap to Ablution, Sprinkler and Pump Room",
S34482,VO016,Balco Seismic Joints,
S34482,VO017,Air Freight - Provisional Sum,
S34482,VO018,Powder Coating - Provisional Sum,
23159,VO077,L3 Door Sill Flashings - Installation,SI-006382
S34582,VO005,Contract/Variation Credits,
R1046,VO006, Excess Carbodur 1030,Email25/03
S34543,VO012,Supply and install Nuralite fixing plates ,SI-5480
S35023,VO001,Additional Negative Panel Detailing,
S34065,VO006,Installation of asphalt protection to nibs ,GCOR-02138
S34999,VO002,Agreed on charge value,
S35070,VO001,Supply Aluminium overflow drain pipe (2x),Email26/3
S34897,VO005,Credit Voltex/Swelltite to Deleted Scope ,
22196,VO075,B1 Ceiling & S23 Corridor Leak Review & Remediation ,
23159,VO078,Air NZ Wedge - Temp Waterproofing,SI-006393
S34539,VO002,Temporary Waterproofing to Risers L2 and L3,SI-580
23159,VO079,SP5 L1 & 2 Water Drainage Control,SI-006396
S34482,VO019,Supply only 2 X 200mm X 75mm Scuppers ,SI-000955
R776,VO002,Otira May 2026  Works - Sample Repair,49033601
S34754,VO023,Auckland Hopsital - A01 Support Building L3 Leak Investigation,WOT0209652
S34183,VO025,Remove seismic cover plates on main link ,SI-2204
R878,VO007,Grid 6 beam remediation,Email31/03
R878,VO008,Les Mills Concrete Repairs ( Beam and columns)  ,Email01/04
S34443,VO064,Slab Waterproofing/membrane Staff ,SI-5676
22168,VO130,Internal Plant Room Builders Works ,
S34539,VO003,Packing sill angles for membrane,SI-605
S34683,VO002,Penetration Detailing and Temporary Waterproofing,
R1008,VO001,VO001 - B1 concrete screed,SI-000950
R344,VO008,2026 Flu Vaccine,
S35088,VO001,1x outlet & 1x overflow,
22168,VO131,PC Flashing Infills around Windows,
22168,VO132,N9/ NF-NE Flashing Extension ,
R1194,VO002,Masonry Review Additional Areas,SI-12
23159,VO080,WP1-SP4 L2 East corridor Hydrant cupboard Waterproofing,
S34591,VO014,Vertical sealant to GL D Precast Panels,SI-609
S34183,VO026,Sika Fillets to Plant Room,
S34482,VO020,Level one carpark substrate repairs as required,
S34477,VO003,Waterbar replacement ,
S34683,VO003,Gridline 33 Recoat Works,
S34354,VO001,Site visit/substrate confirmation,SI-000180
22168,VO133,Northern Plantroom Coating Repairs,
S35070,VO002,Plantroom Liquid Coating Repairs,
22168,VO134,Door Bituthene Reinstatement,
S34443,VO065,Vent Pipe Detailing,SI-5756
R1046,VO007,"Remove 1C, 1D deck leveling for crack repair",SI-105
S34591,VO015,Additional detailing to pipe penetration,Email24/03
S35067,VO001,Site Works,
22168,VO135,Coating Works,
S34183,VO027,Reinstate transition flashing,SI-2283
S34443,VO066,Defect List Works - Zone 5 & 4 Roof,SI-5809
R1001,VO004,Site work on 9th April 2026,Email19/04
23159,VO081,Waterproofing to L2 Lounge south and north façade Nibs,SI-006453
S34183,VO028,Install flashings and seal against existing building - Link 5 & 6,SI 2287
S34539,VO004,Seal All Penetrations L5,SI-642
R878,VO009,,
S34443,VO067,Pipe box and duct upstand remedials (GL20 - Level 3 Roof),SI-5840
23159,VO082,Level 3 Warm Roof - ILD Retest and repairs to defects as per site instruction,SI-006472
S34482,VO021,Concrete Repairs to Slab Edge Grid 4 ,SI-001074
22168,VO136,Loading Dock Roller Door Closure Flashing ,RFI-003525
S34539,VO005,Sample/Mock-up ,
S34763,VO002,Membrane Replacement,SI-17
S34354,VO002,HSE Requirements,
S34482,VO022,B1 Concrete Screed,SI-000950
S34631,VO004,Ground Anchor Penetration Detailing Along Gridline SC Capping Beam ,
S34897,VO006,Glenn Innes Pipe Penetrations to Central Lift Pit ,
17221,VO002,Concrete corner crack repairs,
17221,VO003,Southern Vent Building - Additional Works,
S34982,VO003,Additional Sealant,
S34582,VO006,Additional Cost Value due to Substrate Undulations & Unevenness,
S34443,VO068,Gooseneck Tender Allowance Credit ,
S34443,VO069,LEVEL 00 ZONE 3.3 FENZ ROOF ,CI 1815
S34884,VO001,Tender to IFC,
S34482,VO023,Grid H Aquafin 2KM Pipe Penetration Detailing,SI-001088
S35023,VO002,Sika Guard - Credit ,
23159,VO083,Waterproofing to level 1 hydraulic riser night works,SI-006495
S34482,VO024,B2/B1B Precast Seals – extend sealant by 50mm,SI-001096
S34354,VO003,Additional sealants & adhesives,SI-00185
S35067,VO002,Surface preparation,
S34543,VO013,Main & Secondary Core Roof Penetrations,SI-5837
S34543,VO014,Re-apply matacryl membrane to the top of nib Level 5,SI-5926
S34772,VO005,Tapered PIR Insulation Works to the Level 3 Area ,
S34543,VO015,Levels 4&5 new outlet matacryl application,SI-5927
S34248,VO009,Butynol Gutter Remedials,
S34884,V001,Changes in Glass Heights along Gride e,
S34443,VO070,Home Access Roof Requirements,SI5984
S34884,V002,Pearse Construction - Replacement and additional framing,
R444,VO032,Balcony Scaffold hole Repair/ Infill,1159/1884
R444,VO033,Level 7 Balcony Concrete Repair,CI 941
R1271,VO001,Crack Repair - General Ward Building,Contract
R1186,VO001,Preparation work prior to membrane installation,S04948
23159,VO084,"Level 1 wet,mech riser waterproofing patching",SI6552
S34582,VO007,Credit for Hire of Dehumidifier and Dryer used by Orams,
S34543,VO016,Matacryl LM to Channel Drains,SI 5992
S35135,VO001,Additional supply and installation of Voltex membrane around pad footings,
S34591,VO016,Temporary protection over membrane at GL K 8/K,SI-694
S34443,VO071,Nuraglaze Tender Allowance Credit,
S34982,VO004,Additional sealant to the bracket and slab,
S34624,VO002,UoA - L5 Overflow Works,HA022276
S34884,V003,Portaloo,
R747,VO002,Stage 2 - Screeding,S05044
R747,VO003,Removal of Exisiting Coating,S05044
R747,VO004,Tenant - Moving out Materials on Roof level,Email19/05
S34354,VO004,Installation of EPDM to floor joint,
S34543,VO017,"Reapplication of waterproofing, section of ground to Level 1 ramp",SI-6122
S34539,VO006,Scupper membrane exposed,SI 715
R444,VO034,Entry Ramp Screed,CI 994
23159,VO085,WP1  MKT Platform 1 Hatch Ladder Extra  Layer Membrane,SI 6604
S35036,VO001,Pipe Penetrations Waterbar Installation ,
22196,VO076,Maintenance Inspection - Expansion Joint,
R444,VO035,Ground Floor Bay Window Dry Pack,CI 1000
S35067,VO003,Substrate Preparation (Variation Works) ,
S35067,VO004,Additional Scope (Electrical Works),
S34042,VO007,Detailing to additional plinths,
R1073,VO001,,Email25/5
R1073,VO002,Additional Bracing Steel Underneath for 20 off plates,Email25/05
17221,VO004,Additional Scope - Southern Vent Building,
17221,VO005,Joint Sealer for Expansion Joint in Workshop,
S34482,VO025,Credit B1A Aquafin - No Access ,
R1194,VO003,Northern Facade Crack Repairs,N.Facade
S34897,VO007,Terratuff Coating to Lift Pit Bases ,
S34897,VO008,Te Mahia Crack Repair on Insitu Columns ,
S34086,VO001,Asphalt Works,
S34248,VO010,Lift Pit Repair ,
R878,VO010,Change Room Refurbishment,SI 50
S34884,VO002,Additional work to install firecollars & clamp rings to existing plumbing,
S34582,VO008,Additional cost for stage 3b due to substrate undulations & uneveness,
S34539,VO007,Temp Waterproofing  Podium Penetrations,SI 729
S35067,VO005,Additional Scope (Outlets and Fire Collars),
S35067,VO006,Termination Bar (Credit),
R747,VO005,Substrate Crack Repairs,Email29/05
S34910,VO001,Weekly rental charges (04/05/2026 – 01/06/2026),
S35013,VO001,Transformer Temporary Waterproofing,SI35
S34543,VO018,Main Core Floor Finishing ,SI-6206
S34543,VO019,L3 Point Drain,SI-6239
S34543,VO020,Various Sealant Works,SI-6221
S34183,VO029,Additional Cetcoat,SI-2447
S34884,V004,MCB Plumbing & Drainage Work to existing plumbing,
S34884,V005,MCB Plumbing & Drainage Credit 3 Collars,
S34884,V006,Pearse Construction - Labour to modify Soffit Framing for plumbing,
23159,VO086,PC68 Coatings - Remediation of the Mechanical Damage to the Coating Areas,SI-006662
22168,VO137,N6 Bituthene 3000 Removal & Remediation  ,
S34443,VO072,Cap sheet to base of Shed to Home Access Ladder,SI-6251
S34539,VO008,Temporary Waterproof L6,SI-748
23159,VO087,WP1_SP5 ground floor temp waterproof,SI-006683
S34884,V007,Credit for Channel Drain- Off the Shelf Channel drain in lieu of Custom order,
S34631,VO005,Replace waterbar in lift pit,SI-001187
S34631,VO006,Remedials to the Volclay between GL D/E - 1/2.,SI-001188
S34754,VO024,Auckland Hospital - A35 Te Whetu Tawera: ACute Mental Health Unit,WOT0247580
S34543,VO021,ILD Repairs to matacryl areas all levels,SI-6295
S34543,VO022,Application of Sikadur 31,SI-6249
R1059,VO003,B41 Floor replacement (UoA B03.B41C) - Main Lab Flooring,Email8/06
R1046,VO008,Crack Repairs Core Samples,SI 200
R1046,VO009,Sika Grout 215 between block wall and 300PFC,SI 207
R1186,VO002,Plaster Block wall ,Email 9/06
S34323,VO009,Mid Winter party 2026,
R1194,VO004,Additional work after the facade,Email11/06
S34884,VO003,Remove and replace existing sealant,
S34543,VO023,GF to L1 Ramp Works,SI-6329
R444,VO036,Concrete / Mortar Removal - 1B Terrace,1159/2056
S34443,VO073,Credit - Design Change and Temporary Termination Works Due to Staging,
23159,VO088,Sita roof and gutter,
23159,VO089,Additional Gutter Membrane Works,
S34543,VO024,Chase Cuts & Matacryl to L5,SI-6343
S34482,VO026,Application for sealant to the joint,SI 1231
S34482,VO027,Installation of Flashing,SI 1237
R937,VO002,Level 6 Floor Levelling (Ardex K900BF),SI778
S34183,VO030,Supply and Install HAS04 Cover Plates,CI 1702
R1046,VO010,"Crack Injection: Cold joints in units 1E,1F,1G and Cracks in unit DG and Retail 4.",SI 210
S35155,VO001,G04 Investigation remedial works,WOT0250443
S34183,VO031,Reinstall of cover plates and base members on link 1,SI 2476
S35054,VO001,Podium Planter Box Remediation,Email17/06
S35169,VO001,Material Change to Newton 503  Mesh to room ends,Email17/06
S34183,VO032,Supply and Install flashings on link 2,SI 2457
S35067,VO007,Tiles on Jacks / direct stick to stairs,Email/1706
S35067,VO008,Flashing works,Email/1706
S35067,VO009,Extra over membrane upstand works,Email/1706
S35067,VO010,Plaster to exposed blockwall - GA,Email/1706
S35067,VO011,Flat termination bar to perimeter,Email/1706
S35067,VO012,P & G,Email/1706
S34183,VO033,Plant Room control joint sealant works,SI 2496
S34482,VO028,Supply and installation of tape,SI-001285
R1206,VO001,Carpark Test Area,2340/1
R765,VO002,Concrete remove and replace ,PO5058837
S34183,VO034,Defect remedials – damages to coating ,SI-2467
S34183,VO035,Waitakere Hospital - Seismic joints variation,CAN158&164
S34631,VO007,Thermal Insulation to the internal face of the capping beam ,
S34631,VO008,IFC to Tender Drawings ,SI-000167
S34631,VO009,Foundation Waterstop,SI-000305
S34975,VO001,Contract Variances,
22196,VO077,Membrane Repairs to Mechanical Plant Supports,
S34539,VO009,Small water ingress L1 Podium,SI 777
22168,VO138,N9 Exposed External Conduit & Pipe Flashing ,
22168,VO139,NB - Post Plant Install Floor Repairs ,
22168,VO140,Perimeter Flashing Repairs ,
22168,VO141,Balco Seismic System,
22168,VO142,Zone 1 Break Thru Door Level 1,
R1028,VO002,Basement Concrete Repairs,Email16/06
S35036,VO002,Sikalastic to BCT Threshold Drains,
S35036,VO003,"Termination Bar & Sealant to Thermathene Membrane on Grid AA, A1 & A0",
S34772,VO006,"Nuradeck C to Joinery",Email23/6
S34884,VO004,Level 2 Soffitt & Garden Level Wardrobe Internal Leak,Email24/6
S34578,VO005,Air Freight,
S34832,VO001,Newtons Waterbar,
R1213,VO001,"Credit to Allow for Access Scaffolf, including erection, dismantling and 9 weeks rental",Email24/6
23159,VO090,Level 02 line marking remediation works ,Email/2406
R1213,VO002,Swings Stage,Email 24/0
23159,VO091,"Ground Mez, Line Marking - Credit",COR-000029
23159,VO092,A L2 Maintenance platform 3.02 WPM to timber nibs,SI-005860
S34631,VO010,Detailing to Penetration (upto 200mm dia),
23159,VO093,Waterproofing to Hydrant pipe inside L2 east corridoor,SI 6417
S34897,VO009,Sikaflex MS Sealant to the Floor Joints,
S34086,VO002,Chase cutting to flashings in asphalt ,
S34086,VO003,H47 Loading Dock Stair Flashing,
R1294,VO001,Additional Repairs,Email 25/6
S34884,VO005,Additional Channel Support,
S34910,VO002,Weekly Rental Charges 02.06.26 to 06.07.26,
S34910,VO003,Credit for items not completed,
S34910,VO004,Engineer's Inspection,
S34910,VO005,P&G Adjustment,
S35142,VO001,Additional Fixings for Existing Packers to Every Purlin,
S34443,VO074,Home Building - Redundant roof Penetration - L3 Roof,SI6401
S34443,VO075,Home Building - Level 43 Roof Torch on Repairs / Patching,SI6400
S35042,VO001,WO Building Flat membrane - Locate water leak,W/O 119612
S34754,VO025,Carrington Building C90 Rehab Plus  - Roof Leak Investigation,WOT0259798
S34545,VO026,Additional Waterproofing to Zone 3 SVR Room,
S35055,VO001,Contract Credits,
R937,VO003,Sika Grout 212 to Roof CHS Columns (70N),SI 792
S34539,VO010,Sika Grout 212 to Roof CHS Columns (70 N),SI 792
S34884,V008,Credit Variation for Louvre Frams,
S34482,VO029,Canopy Pipe Penetration,SI-001311
R1194,VO005,North Facade Waste Removal,NorthFacad
S34884,V009,"Measure and Value variaiton per day- Perimeter scaffolding, Stair access, Loading platform & porta loo hire. (Excludes hire for rubbish chute) ",
S34884,V010,Engineering cost for the Scaffold as per the original tender value.,
S34884,V011,Ground Level SS Plate Extra,
S34884,V012,Commercial Discount - as Agreed (for reduced area of east elevation),
S35142,V001,RFI #2 - Structural Engineers Advice - Existing Packer Fixings,
S35142,V002,RFI #3 - Structural Engineers Advice - Soft Spot Remedial,
S35142,V003,Plywood to upstands,
S34248,VO011,Butynol Gutter Remedials,SI 1756
23159,VO094,"Decarb, Sita & Grid 39 Works outside normal working hours",SI-006845
S34482,VO030,Supply and install coverplates,SI-001338
S34482,VO031,Supply and Install welded tray flashing,SI-001330
23245,VO037,Installation of flashing tape,
22168,VO143,N-6 Vertical Sealant/Additional Flashing,
S34539,VO011,Roof overflows,SI 799
S34543,VO025,"ACO drain, L4 base of ramp to L5",SI-4460
R937,VO004,Lift overrun Grinding,SI 796
S34539,VO012,Lift overrun,SI 796
22168,VO144,Flooring Remedials as required plant room,
S34543,VO026,Final Account Agreement,
S35013,VO002,Switchroom Penetrations,SI-000059
S34482,VO032,Build a nib using Sikadur 31CF,SI-001252
R1008,VO002,Joint Termination Nib,S34482
23245,VO038,Grinding concrete Nib ,SI-003486
R765,VO003,Baseplate Grouting,CAN001
S35197,VO001,Crack Repairs to the Lift Roof Wall,Email 14/0
S34966,VO001,Alternative Waterbar to Internal Slab Cut Outs ,
S34966,VO002,SIKA S2 Sealant to Internal Footing Slab Outs ,
S34966,VO003,Additional Sikaproof A to Internal Footings ,
S34870,VO001,Offsite Storage for PIR Insulation,SI 2237
S34466,VO002,Sikadur 42 Pilecap Repairs ,
"""

def _load_default_vos():
    reader = csv.DictReader(io.StringIO(DEFAULT_VOS_CSV))
    valid_jobs = {j.split(" - ")[0].strip() for j in DEFAULT_JOBS}
    rows = []
    for row in reader:
        job = (row.get("Job Number") or "").strip()
        vo = (row.get("Variation Order Number") or "").strip()
        if not job or not vo or job not in valid_jobs:
            continue
        rows.append({
            "job": job,
            "vo": vo,
            "description": (row.get("Description") or "").strip(),
            "customer_order": (row.get("Customer Order Number") or "").strip(),
        })
    return rows

DEFAULT_VOS = _load_default_vos()

# In-memory store — overwritten by webhook sync
_products = list(DEFAULT_PRODUCTS)
_jobs = list(DEFAULT_JOBS)
_vos = list(DEFAULT_VOS)

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

@app.get("/api/hand-tools")
async def get_hand_tools():
    """Returns the hand tools list with names and costs."""
    return HAND_TOOLS

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
    source: Optional[str] = None  # 'voice' or 'text'

@app.get("/api/products")
async def get_products():
    return _products

@app.get("/api/jobs")
async def get_jobs():
    return _jobs

@app.get("/api/vos")
async def get_vos():
    """Returns open Variation Orders per job (job, vo, description, customer_order)."""
    return _vos


@app.post("/api/match")
async def match_product(req: MatchRequest):
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    products_json = json.dumps(_products)
    jobs_json = json.dumps(_jobs)
    tools_json = json.dumps([t["name"] for t in HAND_TOOLS])
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
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
  "tools": [{{"name":"exact name from HAND TOOLS list","quantity":1}}],
  "job": "exact match from job list or null",
  "job_suggestions": ["up to 3 close matches if ambiguous"],
  "worker_name": "...",
  "ambiguous": false,
  "missing": []
}}

- If multiple stock products mentioned, include all in matches array, each with their own quantity
- If a word matches the alias of MORE THAN ONE product (e.g. "swelltite" matches both a bar and a roll), set ambiguous: true and include ALL matching products in matches so the user can choose
- If no quantity stated for a product, set quantity to null and add "quantity" to missing
- Put null and add to missing[] for job or worker_name if not in transcript
- Only include tools that are a clear match to the HAND TOOLS list
- For tools, if a quantity is stated (e.g. "2 hammers") set quantity accordingly, otherwise default to 1
- If ONLY tools are mentioned (no stock products), return matches: [] and do NOT add "product" or "quantity" to missing[]
"""}
        ]
    )
    return json.loads(response.choices[0].message.content.strip())

@app.post("/api/entries")
async def create_entry(entry: EntryCreate):
    conn = await get_db()
    try:
        nz_today = datetime.now(NZ_TZ).date()
        row = await conn.fetchrow("""
            INSERT INTO stock_entries (item_code, entry_date, job, supplier, description, cost_quantity, unit, gl_code, worker_name, source)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *
        """, entry.item_code, nz_today, entry.job, entry.supplier,
            entry.description, entry.cost_quantity, entry.unit, entry.gl_code, entry.worker_name, entry.source)
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
    quantity: int = 1
    source: Optional[str] = None  # 'voice' or 'text'

@app.post("/api/tool-entries")
async def create_tool_entry(entry: ToolEntryCreate):
    conn = await get_db()
    try:
        nz_today = datetime.now(NZ_TZ).date()
        row = await conn.fetchrow("""
            INSERT INTO tool_entries (tool_name, entry_date, job, worker_name, quantity, source)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING *
        """, entry.tool_name, nz_today, entry.job, entry.worker_name, entry.quantity, entry.source)
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
            f"SELECT tool_name, entry_date, job, worker_name, quantity FROM tool_entries {where} ORDER BY entry_date ASC, created_at ASC",
            *params
        )
    finally:
        await conn.close()

    # Build cost lookup: tool name (lowercase) -> unit cost
    tool_cost_lookup = {t["name"].lower(): t["cost"] for t in HAND_TOOLS}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tool", "Quantity", "Unit Cost", "Line Total", "Date", "Job Number", "Worker"])
    for r in rows:
        job_full = r["job"] or ""
        job_number = job_full.split(" - ")[0].strip() if " - " in job_full else job_full
        qty = r["quantity"] or 1
        unit_cost = tool_cost_lookup.get(r["tool_name"].lower())
        line_total = (unit_cost * qty) if unit_cost is not None else ""
        writer.writerow([
            r["tool_name"],
            qty,
            f"${unit_cost}" if unit_cost is not None else "",
            f"${line_total}" if line_total != "" else "",
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
    quantity: Optional[int] = None

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
        if update.quantity is not None:
            params.append(update.quantity); fields.append(f"quantity=${len(params)}")
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


# ── Dayworks entries ──────────────────────────────────────────────────────────

class DayworksEntryCreate(BaseModel):
    job: str
    date: str
    variation: str
    vo_number: Optional[str] = None
    location: Optional[str] = None
    labour_rows: list = []
    material_rows: list = []
    comments: Optional[str] = None
    photos: list = []
    signoff_mode: str
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    signature_data_url: Optional[str] = None
    status: str
    webhook_url: Optional[str] = None

class DayworksSignSubmit(BaseModel):
    client_name: Optional[str] = None
    signature_data_url: str

def _json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value

async def _send_dayworks_webhook(webhook_url: str, entry: dict, stage: str = 'submitted', sign_url: Optional[str] = None):
    try:
        pdf_bytes = render_dayworks_pdf(entry)
        pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')
        job_slug = re.sub(r'[^A-Za-z0-9]+', '_', entry.get('job') or 'job').strip('_') or 'job'
        date_slug = _json_safe(entry.get('entry_date')) or 'date'
        filename = f"dayworks_{job_slug}_{date_slug}.pdf"
        json_entry = {k: _json_safe(v) for k, v in entry.items()}
        payload = {
            "type": "dayworks_sheet_submitted",
            "stage": stage,
            "entry": json_entry,
            "pdf_base64": pdf_b64,
            "pdf_filename": filename,
            "at": datetime.utcnow().isoformat() + "Z",
        }
        if sign_url:
            payload["sign_url"] = sign_url
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Dayworks webhook failed: {e}")

@app.post("/api/dayworks")
async def create_dayworks_entry(entry: DayworksEntryCreate, request: Request):
    sign_token = secrets.token_urlsafe(32) if entry.signoff_mode == 'email' else None
    conn = await get_db()
    try:
        entry_date = date.fromisoformat(entry.date)
        row = await conn.fetchrow("""
            INSERT INTO dayworks_entries
                (job, entry_date, variation, vo_number, location, labour_rows, material_rows,
                 comments, photos, signoff_mode, client_name, client_email, signature_data_url, status,
                 sign_token, webhook_url)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16) RETURNING *
        """, entry.job, entry_date, entry.variation, entry.vo_number, entry.location,
            entry.labour_rows, entry.material_rows, entry.comments, entry.photos,
            entry.signoff_mode, entry.client_name, entry.client_email, entry.signature_data_url, entry.status,
            sign_token, entry.webhook_url)
        saved = dict(row)
    finally:
        await conn.close()

    if entry.webhook_url:
        sign_url = f"{str(request.base_url).rstrip('/')}/?sign={sign_token}" if sign_token else None
        await _send_dayworks_webhook(entry.webhook_url, saved, stage='submitted', sign_url=sign_url)

    return saved

@app.get("/api/dayworks/sign/{token}")
async def get_dayworks_for_signing(token: str):
    conn = await get_db()
    try:
        row = await conn.fetchrow("SELECT * FROM dayworks_entries WHERE sign_token = $1", token)
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    entry = dict(row)
    if entry.get("signature_data_url"):
        raise HTTPException(status_code=410, detail="This sheet has already been signed")
    return {
        "job": entry["job"], "entry_date": _json_safe(entry["entry_date"]),
        "variation": entry["variation"], "vo_number": entry["vo_number"], "location": entry["location"],
        "labour_rows": entry["labour_rows"], "material_rows": entry["material_rows"],
        "comments": entry["comments"], "photos": entry["photos"], "client_name": entry["client_name"],
    }

@app.post("/api/dayworks/sign/{token}")
async def submit_dayworks_signature(token: str, body: DayworksSignSubmit):
    conn = await get_db()
    try:
        row = await conn.fetchrow("SELECT * FROM dayworks_entries WHERE sign_token = $1", token)
        if not row:
            raise HTTPException(status_code=404, detail="Invalid or expired link")
        entry = dict(row)
        if entry.get("signature_data_url"):
            raise HTTPException(status_code=410, detail="This sheet has already been signed")
        updated = await conn.fetchrow("""
            UPDATE dayworks_entries
            SET signature_data_url = $1, client_name = COALESCE($2, client_name), status = 'Signed remotely'
            WHERE sign_token = $3 RETURNING *
        """, body.signature_data_url, body.client_name, token)
        saved = dict(updated)
    finally:
        await conn.close()

    if saved.get('webhook_url'):
        await _send_dayworks_webhook(saved['webhook_url'], saved, stage='signed')

    return {"ok": True}

@app.get("/api/dayworks")
async def list_dayworks_entries():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT * FROM dayworks_entries ORDER BY created_at DESC")
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.delete("/api/dayworks/{entry_id}")
async def delete_dayworks_entry(entry_id: int):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM dayworks_entries WHERE id = $1", entry_id)
        return {"ok": True}
    finally:
        await conn.close()

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
