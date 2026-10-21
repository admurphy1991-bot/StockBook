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
    {"name": "Tajima knife", "cost": 18, "alias": "utility knife, box cutter, stanley knife"},
    {"name": "Hammer", "cost": 26, "alias": ""},
    {"name": "Hand saw", "cost": 16, "alias": ""},
    {"name": "Spirit level", "cost": 15, "alias": "level, bubble level"},
    {"name": "Crescent spanner", "cost": 29, "alias": "adjustable wrench, crescent wrench, shifter"},
    {"name": "Pilers", "cost": 12, "alias": "pliers"},
    {"name": "Chalk line", "cost": 24, "alias": "chalk reel, snap line"},
    {"name": "Hack saw", "cost": 6, "alias": ""},
    {"name": "Aviation tin snips", "cost": 29, "alias": "tin snips, aviation snips, metal snips"},
    {"name": "SINTEX R26:1 MS Cartridge Gun", "cost": 53, "alias": "sintex gun, cartridge gun, sealant gun, caulking gun"},
    {"name": "Trowell", "cost": 12, "alias": "trowel"},
    {"name": "Crack patch tool", "cost": 19, "alias": "crack tool, joint tool"},
    {"name": "Pinch bar", "cost": 29, "alias": "pry bar"},
    {"name": "Crow bar", "cost": 30, "alias": "crowbar"},
    {"name": "Pop riveter", "cost": 75, "alias": "rivet gun, riveter"},
    {"name": "Spatula", "cost": 10, "alias": ""},
    {"name": "Measuring tape", "cost": 20, "alias": "tape measure"},
    {"name": "Metal file", "cost": 13, "alias": "file"},
    {"name": "Bull nose trowell", "cost": 8, "alias": "bull nose trowel, pointing trowel"},
    {"name": "Wire brush", "cost": 7, "alias": ""},
    {"name": "Wood chisel", "cost": 23, "alias": "chisel"},
    {"name": "Allen keys", "cost": 25, "alias": "hex keys, allen key set"},
    {"name": "Linbide scraper", "cost": 15, "alias": "carbide scraper, scraper"},
    {"name": "Rubber mallet", "cost": 13, "alias": ""},
    {"name": "Scissors", "cost": 20, "alias": ""},
    {"name": "Window scraper", "cost": 9, "alias": "glass scraper"},
    {"name": "Socket set", "cost": 80, "alias": "sockets"},
    {"name": "Hand spade", "cost": 37, "alias": "spade"},
    {"name": "Hand shovel", "cost": 70, "alias": "shovel"},
    {"name": "Sledge hammer", "cost": 70, "alias": "sledgehammer"},
    {"name": "Hand pick", "cost": 50, "alias": "pick, pickaxe"},
    {"name": "Digging bar", "cost": 66, "alias": "steel bar, tamping bar"},
    {"name": "Builders set square", "cost": 24, "alias": "set square, framing square"},
    {"name": "Penny roller", "cost": 51, "alias": "spiked roller, membrane spike roller"},
    {"name": "Large Membrane roller - 90 mm", "cost": 132, "alias": "large roller, 90mm roller, big membrane roller"},
    {"name": "Medium Membrane roller - 40 mm", "cost": 49, "alias": "medium roller, 40mm roller"},
    {"name": "SIEVERT EASYJET PLUS Lighter", "cost": 131, "alias": "sievert lighter, gas torch lighter, easyjet lighter"},
    {"name": "steel club hammer", "cost": 32, "alias": "club hammer, lump hammer"},
    {"name": "Sterling knife", "cost": 9, "alias": "sterling utility knife"},
    {"name": "Small torch lighter", "cost": 131, "alias": "torch lighter, mini torch"},
    {"name": "Wire nipper cutters", "cost": 15, "alias": "wire cutters, nippers"},
    {"name": "Hand mallet", "cost": None, "alias": "mallet"},
    {"name": "Striker", "cost": 12, "alias": "flint striker, spark lighter"},
    {"name": "Broom", "cost": 40, "alias": ""},
    {"name": "Garden hose", "cost": 50, "alias": "hose"},
    {"name": "Garden hose fittings", "cost": 4, "alias": "hose fittings, hose connectors"},
    {"name": "Tool Bag", "cost": 60, "alias": "kit bag"},
    {"name": "Makita SDS-Plus Drill Bit 5mm (E-20856)", "cost": 17, "alias": "5mm drill bit, sds bit 5mm, makita 5mm bit"},
    {"name": "Makita SDS-Plus Drill Bit 5.5mm (E-20921)", "cost": 14, "alias": "5.5mm drill bit, sds bit five point five, makita 5.5mm bit"},
    {"name": "Makita SDS-Plus Drill Bit 10mm (E-21238)", "cost": 19, "alias": "10mm drill bit, sds bit 10mm, makita 10mm bit"},
    {"name": "Makita SDS-Plus Drill Bit 12mm (E-21319)", "cost": 22, "alias": "12mm drill bit, sds bit 12mm, makita 12mm bit"},
    {"name": "Tusk SDS-Plus Concrete Drill Bit 6mm Solid X-Head (TSX 6S)", "cost": 11, "alias": "6mm tusk bit, tusk drill bit 6mm, tsx6s"},
    {"name": "Tusk SDS-Plus Concrete Drill Bit 14mm Cross-Head (TSP 14M)", "cost": 23, "alias": "14mm tusk bit, tusk drill bit 14mm, tsp14m"},
    {"name": "Makita SDS-Plus Spade/Shovel Bit 50mm (D-62446)", "cost": 10, "alias": "scaling chisel, spade bit, flat chisel 50mm, shovel bit"},
    {"name": "Makita Spade/Shovel Bit 60mm (P-24957)", "cost": 58, "alias": "angle chisel, spade bit 60mm, shovel bit 60"},
]

# ── In-memory product/job store (seeded from DB config or defaults) ──────────

DEFAULT_PRODUCTS = [
    {"code": "B1BTLQM", "description": "BITUTHENE LIQUID MEMBRANE LM3000 (5.7LT)", "supplier": "ALLNEX", "unit": "ea", "gl": "2000", "alias": "bituthene liquid membrane, bitu liquid membrane, LM three thousand"},
    {"code": "60255A02R", "description": "BITUTHENE 5000 - ROLL", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "bitu five thousand, bituthene roll, bitu roll"},
    {"code": "BIBT3000", "description": "Bituthene 3000 (1.00 x 20m Roll)", "supplier": "ALLNEX", "unit": "ROLL", "gl": "2000", "alias": "bituthene three thousand, bitu three thousand, bitu roll twenty metre"},
    {"code": "PFRO017", "description": "PF Rod 20mm 60m coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod twenty long roll, PF rod twenty sixty, backer twenty roll"},
    {"code": "PFRO022", "description": "PF Rod 40mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod forty, PF rod forty, backer rod forty"},
    {"code": "PFRO018", "description": "PF Rod 25mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod twenty five, PF rod twenty five, backer twenty five"},
    {"code": "PFRO014", "description": "PF Rod 15mm 50m Coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod fifteen mil, PF rod fifteen, backer rod fifteen"},
    {"code": "PFRO008", "description": "PF Rod 10mm 50m Coil (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod ten mil, PF rod ten, foam backer rod ten"},
    {"code": "PFRO023", "description": "PF Rod 50mm 2m length (per mtr)", "supplier": "KARSTEN", "unit": "M", "gl": "2000", "alias": "backing rod fifty, PF rod fifty, backer rod fifty"},
    {"code": "PFRO021", "description": "PF Rod 30mm 25m length (per roll)", "supplier": "KARSTEN", "unit": "ROLL", "gl": "2000", "alias": "backing rod thirty roll, PF rod thirty coil, backer thirty roll"},
    {"code": "ALLAQ15", "description": "Aquadrain 15 18.9m2 VAQUA15X", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "aquadrain, drainage mat, aquadrain fifteen"},
    {"code": "ALLBESA", "description": "Allco - Bentoseal 15kg", "supplier": "ALLCOWATER", "unit": "PAIL", "gl": "2000", "alias": "bentoseal, bento seal, bentonite seal"},
    {"code": "ALLCET", "description": "Allco - Cetcoat 15kg", "supplier": "ALLCOWATER", "unit": "PAIL", "gl": "2000", "alias": "cetcoat, cet coat, allco cet"},
    {"code": "ALLVOCR", "description": "Allco - Voltex CR (5.4sqm roll)", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "voltex CR, voltex cr roll, allco voltex CR"},
    {"code": "ALLRX101", "description": "RX101T Waterstop 6.1lm per roll", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh one waterstop, swelling waterstop, hydrophilic strip"},
    {"code": "VRX10210", "description": "Allco - RX102 Waterstop 10.2m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh two waterstop, RX102 strip, allco waterstop ten metre"},
    {"code": "ALLSWTB", "description": "Allco - Swelltite Termination Bar ea", "supplier": "ALLCOWATER", "unit": "ea", "gl": "2000", "alias": "swelltite bar, termination bar, swelltite termination"},
    {"code": "VSTPOL11.5", "description": "Swelltite Polish 3000 11.5m2/roll", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "swelltite polish, polish three thousand, swelltite roll"},
    {"code": "ALLVODS", "description": "Allco - Voltex Super 66.6 DS", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "voltex super, voltex DS, bentonite super sheet"},
    {"code": "ALLWSTG", "description": "Allco - Waterstoppage 25kg bag", "supplier": "ALLCOWATER", "unit": "BAG", "gl": "2000", "alias": "waterstoppage, water stoppage bag, allco grout, chicken shit"},
    {"code": "VCS600", "description": "Cetseal (20oz) 600mls Sausage - Polymeric Sealant/Adhesive", "supplier": "ALLCOWATER", "unit": "600ML", "gl": "2000", "alias": "cetseal sausage, polymeric sealant sausage, cet seal"},
    {"code": "COREFL18", "description": "Allguard Coreflute 1800 x 1150 x 4mm", "supplier": "ALLCOWATER", "unit": "SHEET", "gl": "2000", "alias": "coreflute, protection board, allguard coreflute"},
    {"code": "COREFL18", "description": "Mulfords Coreflute 1800 x 1150 x 4mm", "supplier": "MULFORDS", "unit": "SHEET", "gl": "2000", "alias": "mulfords coreflute, mulford coreflute, coreflute mulfords"},
    {"code": "COREFL18", "description": "Recycled Coreflute 1800 x 1150 x 4mm", "supplier": "", "unit": "SHEET", "gl": "2000", "alias": "recycled coreflute, recycled protection board, eco coreflute"},
    {"code": "SI212", "description": "Sika - 212 Grout 25kg", "supplier": "SIKA", "unit": "BAG", "gl": "2000", "alias": "sika two twelve grout, sika grout, two twelve bag"},
    {"code": "SI412", "description": "Sika - Monotop 412 bag", "supplier": "SIKA", "unit": "BAG", "gl": "2000", "alias": "sika monotop four twelve, monotop four twelve, sika repair bag"},
    {"code": "SI910", "description": "Sika Monotop 910N Primer 4kg", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika monotop nine ten, monotop primer, nine ten primer"},
    {"code": "153729", "description": "Sika - Sikaflex AT Facade (600ml sausage)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex facade sausage, sika facade, sikaflex AT facade"},
    {"code": "536973", "description": "Sikaflex - 400 Fire Grey 600ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex four hundred fire, sika fire sealant grey, fire rated sealant"},
    {"code": "114665", "description": "Sika - Primer 3N (250ml)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika primer, sika three N, primer three N"},
    {"code": "SISW53", "description": "Sika Swell A 2005 20nn x 5mm x 20m", "supplier": "SIKA", "unit": "ROLL", "gl": "2000", "alias": "sika swell A, swell strip twenty by five, hydrophilic strip sika"},
    {"code": "SISWP", "description": "SikaSwell-P 2010H 20mm x 10mm x 10m", "supplier": "SIKA", "unit": "ROLL", "gl": "2000", "alias": "sika swell P, swell profile twenty by ten, sika swellable profile"},
    {"code": "SISWS2", "description": "Sika Swell S2 600ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika swell S2, swell sausage, hydrophilic sausage"},
    {"code": "452399", "description": "Sika - Sikadur U.A 4 Lt", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika ua, sikadur ua, sikadur UA four litre, sika UA small, sikadur urethane four litre, concrete fix"},
    {"code": "444908", "description": "Sika Thinner C Lt (4 ltr)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika thinner four litre, sika C thinner small, thinner C small"},
    {"code": "92541", "description": "Sikaplug 5KG", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaplug, sika plug, hydraulic plug"},
    {"code": "497964", "description": "Sika AnchorFix-1 300ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika anchor fix, anchor fix one, sika anchor bolt"},
    {"code": "435005", "description": "Sikadur Injectokit-TH 250g", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikadur inject kit, injection kit TH, sika inject"},
    {"code": "SIINLV250", "description": "Sikadur Injectokit- LV 250", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikadur inject LV, low viscosity inject kit, sika LV inject"},
    {"code": "920045", "description": "Aluminum Injection Packer 10x100mm", "supplier": "", "unit": "ea", "gl": "2000", "alias": "packers, injection packer, aluminium injection packer"},
    {"code": "405BOOM", "description": "Sika Boom 750ml", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika boom, expanding foam, sika expanding foam"},
    {"code": "444906", "description": "Sika Thinner C Lt (20L)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika thinner twenty litre, sika C thinner large, thinner C big"},
    {"code": "440627", "description": "Sika Blackseal Plus Elastic 20L", "supplier": "SIKA", "unit": "PAIL", "gl": "2000", "alias": "sika blackseal elastic, blackseal plus, sika black seal twenty litre"},
    {"code": "153730", "description": "Sikaflex AT Facade 600ml White", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex facade white, sika facade white, AT facade white"},
    {"code": "153731", "description": "Sikaflex AT Facade 600ml Black", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex facade black, sika facade black, AT facade black"},
    {"code": "551940", "description": "Sika MonoTop-438 R (25kg)", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sika monotop four thirty eight, monotop repair mortar, sika repair mortar"},
    {"code": "551349", "description": "SikaTop Seal-107 Dryseal 5kg", "supplier": "SIKA", "unit": "KG", "gl": "2000", "alias": "sika top seal, dryseal, sika top one oh seven"},
    {"code": "TK102", "description": "NURAFLUX PRIMER (QD) 25l", "supplier": "NURA", "unit": "PAIL", "gl": "2000", "alias": "nuraflux primer, QD primer, quick dry primer twenty five litre"},
    {"code": "TK151", "description": "Bituthene Liquid Membrane (Kit)", "supplier": "NURA", "unit": "ea", "gl": "2000", "alias": "bituthene liquid membrane kit, bitu LM kit, liquid membrane kit"},
    {"code": "TK157", "description": "PREPRUFE LT TAPE 100mm (15M)", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "preprufe LT tape hundred mil, preprufe flashing tape, LT tape"},
    {"code": "TK109", "description": "Bitumen Trianglular Fillet 1.2m", "supplier": "NURA", "unit": "EA", "gl": "2000", "alias": "triangular bitu fillet, bitu triangle fillet, corner fillet"},
    {"code": "TK153", "description": "PREPRUFE 300R PLUS (31.15M)", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "preprufe three hundred plus, preprufe thirty metre, preprufe roll"},
    {"code": "PE751", "description": "TERMINATION BAR 2.4M(FOLDED)", "supplier": "NURA", "unit": "M", "gl": "2000", "alias": "termination bar, term bar, folded term bar"},
    {"code": "ATDUCT", "description": "Attwoods - Silver Cloth Tape per roll", "supplier": "ATTWOOD", "unit": "ROLL", "gl": "2000", "alias": "attwoods duct tape, silver cloth tape, attwoods tape"},
    {"code": "NURFIL", "description": "Bitumen Fillet 1.2m length", "supplier": "EQUUS", "unit": "ea", "gl": "2000", "alias": "bitumen fillet, bitu fillet, nura fillet"},
    {"code": "80151200", "description": "Turbo wave diamond blade dry/wet cured concrete", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "diamond blade, turbo wave blade, concrete cutting blade, concrete cutting disk blade, turbo wave"},
    {"code": "82151204", "description": "125mm Disc. (diamond saw blade)", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "one twenty five diamond disc, small diamond blade, angle grinder blade"},
    {"code": "GLASS/300", "description": "Fibreglass Mat 300 GSM per meter", "supplier": "EQUUS", "unit": "M", "gl": "2000", "alias": "fibreglass mat, chop strand mat, three hundred fibre mat, CSM"},
    {"code": "NURVB", "description": "Nuraply Alu Vapour Barrier", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "nuraply vapour barrier, alu vapour barrier, foil vapour barrier"},
    {"code": "SI42", "description": "Sikadur-42 (15KG KIT)", "supplier": "SIKA", "unit": "KIT", "gl": "2000", "alias": "sikadur forty two, sika forty two kit, epoxy grout kit"},
    {"code": "ALLRX101DH", "description": "RX101DH waterstop delayed Hydration 5m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": "RX one oh one delayed hydration, delayed hydration waterstop"},
    {"code": "SDM06030SS", "description": "SHURE DRIVE SS 6X30MM 01380", "supplier": "RAMSET", "unit": "ea", "gl": "2000", "alias": "shure drive screw, stainless screw six by thirty, SS timber screw, suredrive, shore drive"},
    {"code": "RF124", "description": "Nuraply 3PB Basesheet (10 m x 1m x 3mm roll) 25/p", "supplier": "NURA", "unit": "ROLL", "gl": "2000", "alias": "nuraply basesheet, three PB basesheet, nura base roll"},
    {"code": "ARD100FT", "description": "Ardex - Flashing Tape 4.7m x 100mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "ardex flashing tape, flashing tape one hundred, ardex tape roll"},
    {"code": "ARD150DT", "description": "Ardex - Uncured Detail Tape 30.4m x 150mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "ardex detail tape, uncured detail tape, ardex one fifty tape"},
    {"code": "ARD50ST", "description": "Ardex - Butynol Seam Tape 30.4m x 50mm roll", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "butynol seam tape, ardex seam tape, rubber seam tape"},
    {"code": "ARDAD", "description": "Ardex - WA98 Adhesive 20L pail", "supplier": "ARDEX", "unit": "PAIL", "gl": "2000", "alias": "ardex WA ninety eight adhesive, ardex adhesive pail, WA98 glue"},
    {"code": "ARDST", "description": "Ardex - Substrate Joint Tape 50mx25mm 36roll/ctn", "supplier": "ARDEX", "unit": "ROLL", "gl": "2000", "alias": "ardex joint tape, substrate tape, ardex seam tape roll"},
    {"code": "CA20P", "description": "CA20P Black - Cartridge 310 ML", "supplier": "ARDEX", "unit": "ea", "gl": "2000", "alias": "CA twenty P black, black cartridge, allco black cartridge"},
    {"code": "ARDA38", "description": "Ardex - A38 20kg bag (Aust)", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "ardex A thirty eight, A38 bag, ardex patch mortar"},
    {"code": "ARDA46", "description": "Ardex - A46 20kg bag", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "ardex A forty six, A46 bag, ardex leveller"},
    {"code": "ARDP51", "description": "Ardex - P51 5L bottle", "supplier": "ARDEX", "unit": "PAIL", "gl": "2000", "alias": "ardex P fifty one, P51 primer, ardex primer bottle"},
    {"code": "24954", "description": "K900BF 20kg bag", "supplier": "ARDEX", "unit": "BAG", "gl": "2000", "alias": "K nine hundred bag, ardex K900, K nine hundred BF"},
    {"code": "D21", "description": "Newton Basedrain - Sump Connector", "supplier": "NEWSYSLTD", "unit": "ea", "gl": "2000", "alias": "newton sump connector, basedrain sump, newton sump"},
    {"code": "D1", "description": "Newton Basedrain - 2m Length", "supplier": "NEWSYSLTD", "unit": "M", "gl": "2000", "alias": "newton basedrain, newton drain two metre, newton channel"},
    {"code": "D6", "description": "Newton Basedrain - Swept Corner", "supplier": "NEWSYSLTD", "unit": "ea", "gl": "2000", "alias": "newton swept corner, basedrain corner, newton corner piece"},
    {"code": "D30", "description": "Newton Basedrain - Inspection PortBase - 204 mm x 60 mm opening", "supplier": "NEWSYSLTD", "unit": "ea", "gl": "2000", "alias": "newton inspection port, basedrain inspection, newton port"},
    {"code": "VST50", "description": "DPM Tape Allsheet 48mm x 30 m Red", "supplier": "ALLCOWATER", "unit": "M", "gl": "2000", "alias": "DPM tape red, allsheet tape red, red DPC tape"},
    {"code": "617759", "description": "Sikaflex PRO-3 Purform 600ml", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikaflex pro three, sika pro three purform, sikaflex PRO sausage"},
    {"code": "85681206", "description": "105 turbo cup grinding wheel 12 segments", "supplier": "CHELSEA", "unit": "ea", "gl": "2000", "alias": "turbo cup wheel, grinding wheel, cup grinder wheel, concrete grinding disk"},
    {"code": "35933C", "description": "Tradextra S361 Silver Cloth Tape 48mm x 30m", "supplier": "TRADE", "unit": "ROLL", "gl": "2000", "alias": "silver cloth tape, tradextra silver tape, duct tape silver"},
    {"code": "RF170", "description": "KO hybrytech MS DETAIL 1LT [BLACK]", "supplier": "NURA", "unit": "LTR", "gl": "2000", "alias": "KO hybrytech black, MS detail black, hybrytech liquid"},
    {"code": "59300074", "description": "BluRez CS150 20kg", "supplier": "MBP", "unit": "ea", "gl": "2000", "alias": "bluerez CS one fifty, blurez powder, bluerez base"},
    {"code": "DEXX/GR/15", "description": "Chevaline Dexx", "supplier": "EQUUS", "unit": "ea", "gl": "2000", "alias": "chevaline dexx, dexx primer, dexx treatment"},
    {"code": "24560", "description": "WPM117 Shelterstick 15m x 1m x 2mm - roll", "supplier": "ARDEX", "unit": "ea", "gl": "2000", "alias": "shelterstick roll, WPM one seventeen, ardex shelterstick"},
    {"code": "10543", "description": "WPM3000X 20M X 1.0M X 1.5MM ROLL", "supplier": "ARDEX", "unit": "ea", "gl": "2000", "alias": "WPM roll, waterproof membrane roll, three thousand roll"},
    {"code": "452396", "description": "Sikadur UA 8L", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sika ua, sikadur ua, sikadur UA eight litre, sika UA large, sikadur urethane eight litre, concrete fix"},
    {"code": "ALSANMASTIC/2200", "description": "ALSAN MASTIC 2200 SEALANT (310ML/CARTRIDGE)", "supplier": "EQUUS", "unit": "ea", "gl": "2000", "alias": "alsan mastic, alsan two two hundred, alsan sealant cartridge"},
    {"code": "M1000035", "description": "Bitumen Sealant 300ml", "supplier": "MERZLTD", "unit": "ea", "gl": "2000", "alias": "bitumen sealant, bitu sealant cartridge, black sealant"},
    {"code": "CBFIL30", "description": "Bitumen Fillet 30mm x 30mm x 1100mm", "supplier": "ALLCOWATER", "unit": "ea", "gl": "2000", "alias": "bitumen fillet thirty mil, small bitu fillet, bitu corner fillet"},
    {"code": "67485A14R01", "description": "CSM E20 EMULSION 300g/sm JUSHI - ROL", "supplier": "DGL", "unit": "KG", "gl": "2000", "alias": "CSM emulsion roll, chopped strand mat roll, fibre emulsion roll"},
    {"code": "20101", "description": "Soudal Soudaseal 240FC MS Adhesive 600ml Grey", "supplier": "MERZLTD", "unit": "ea", "gl": "2000", "alias": "soudal adhesive grey, soudaseal grey, soudal MS grey"},
    {"code": "SI11FC", "description": "Sika - Sikaflex11 FC purform", "supplier": "SIKA", "unit": "EA", "gl": "2000", "alias": "sikaflex eleven FC, sika eleven FC purform, sikaflex joint sealant"},
    {"code": "591755", "description": "Sikaflex MS 600ml White", "supplier": "SIKA", "unit": "ea", "gl": "2000", "alias": "sikaflex MS white, sika MS white sausage, sikaflex white six hundred"},
    {"code": "SXR261S", "description": "SINTEX R26:1S MS Sausage Gun", "supplier": "GLUE", "unit": "ea", "gl": "2000", "alias": "sintex sausage gun, big sausage gun, twenty six to one gun"},
    {"code": "AQUAKEM10", "description": "Aquakem 10L Pail", "supplier": "DGL", "unit": "LTR", "gl": "2000", "alias": "aquakem kit, aquakem ten litre, AK kit"},
    {"code": "AQUAKEM8", "description": "Aquakem 8l kit", "supplier": "DGL", "unit": "KIT", "gl": "2000", "alias": "aquakem eight litre, AK eight litre kit, aquakem small kit"},
    {"code": "11204", "description": "Washers - Trackmaster 00120 (Box of 1,000)", "supplier": "RAMSET", "unit": "BAG", "gl": "2000", "alias": ""},
    {"code": "P8C630", "description": "Pulsa 800 30mm STD pin 07050 (500 per bag)", "supplier": "RAMSET", "unit": "BAG", "gl": "2000", "alias": "ramset nails 30mm"},
    {"code": "P8HC627", "description": "Pulsa 800 27mm Hard Conc pin 07175 (500 per bag)", "supplier": "RAMSET", "unit": "BAG", "gl": "2000", "alias": "ramset nails 27mm"},
    {"code": "FAB604", "description": "Ramset Vacuum Bags 5pk", "supplier": "RAMSET", "unit": "PACK", "gl": "2000", "alias": "ramset vaccum bags, spit vacuum bags, ramset vac bags, ramset fleece bags, Ramset/Spit Vacuum Cleaner Fleece Bags 5pk"},
    {"code": "W107418353", "description": "Makita Vacuum Bags 5pk", "supplier": "MAKITA", "unit": "PACK", "gl": "2000", "alias": "makita vaccum bags, makita dust bags, VC4210 bags, makita fleece bags, Makita Vacuum Fleece Dust Bag 5pk"},
    {"code": "VVT500-2", "description": "Allsheet 500T 500T-micron Virgin DPM PE 50m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": ""},
    {"code": "VVT300", "description": "Allsheet 300T-micron virgin DPM PE 2 x 50m", "supplier": "ALLCOWATER", "unit": "ROLL", "gl": "2000", "alias": ""},
]

DEFAULT_JOBS = [
    "2306 - Warranty Work - Sansom Construction Systems Ltd",
    "0001NOJOB - NONJOBRELATED",
    "19239 - Sansom Concrete Repairs",
    "R9999 - Pre-Investigation / Quote / Admin Time",
    "R200 - Stock - Concrete Repairs",
    "R169 - Eden Crescent",
    "21148 - CRL Mined Tunnels *",
    "R344 - Concrete Staff Training / Health & Safety / Meetings",
    "22196 - CRL Aotea - Facade & Seismic",
    "R444 - Parkwood Apartments",
    "23159 - AIAL - WP1 - Terminal Integration",
    "S34000 - Sansom Construction Systems LTD",
    "S9000 - Admin Time - Sansom Ltd",
    "S34042 - Half Moon Bay , 25 Thurston Place - Waterproofing",
    "23300 - Newton Systems",
    "S34065 - Auckland Airport Domestic Processor Pier & FLB Tanking Works",
    "23245 - AATH Facade Package",
    "S34131 - Lorne Street - Student Accommodation",
    "S34160 - Precinct Apartments - 6-8 Lorne Street Auckland CBD",
    "S34182 - AIAL Domestic Processor - Headhouse",
    "S34183 - Waitakere Hospital - Tanking",
    "S34194 - Project Waka - Stage 2 Waterproofing",
    "R626 - Mt Eden 101, Concrete Office / Yard",
    "S34228 - JTFJ Costs Mt Eden Road 101",
    "S34266 - Maintenance / Membrane and Admininistration",
    "S34323 - Staff Appreciation",
    "S2301 - Pre-Investigation / Quotes",
    "S34345 - Auckland Art Gallery - East Terrace",
    "S34360 - Mt Eden Road 101 -Building Maintenance",
    "S34371 - Newton Systems Limited",
    "S34430 - Brighton Road, 6 - Roof Inspection",
    "S34444 - UoA B505, Park Road 85 - Basement Carkpark Leaks",
    "R765 - Diocesan School Aquatics Centre Panel Remediation",
    "S34466 - Queen Street 256 Student Accommodation",
    "S34477 - Summerset St Johns - Building G - Excavation, Inground Plumbing and Tanking",
    "S34482 - Orams Commercial Buildings B1A & B1B",
    "S34490 - Marine Parade 13 - Tanking",
    "101 - Rates",
    "S200STOCK - Sansom Ltd Stock Purchases",
    "S34539 - The Hill Ellerslie - Warm Roof",
    "S34543 - Fisher & Paykel - Garage Building",
    "S34545 - MPI PHEC- Southbase Construction",
    "S34568 - Kings School JR Fletcher Memorial Centre",
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
    "S34688 - Auckland City Mission - Shade Sail Post Detailing",
    "R937 - The Hill - Belvedere, Screeding",
    "R0001NOJOB - Sansom Concrete Repairs - NONJOBRELEATED",
    "S34754 - Sansom Maintenance - Investigation Costs",
    "S34763 - Jervois Road 41",
    "S34766 - Alberton Avenue 57",
    "S34772 - Sarsfied, 81 -  Waterproofing",
    "S34808 - 147 Captain Springs Road  -  Aquakem Coating to walls",
    "S34822 - Fisher & Paykel Healthcare B5.1 - Seismic Joint",
    "S34832 - Barfoot & Thompson Remerua - 367 Remuera Road",
    "S34844 - Pukekohe North Wastewater Pump Station - Tanking",
    "S34846 - 74 - 76 Grafton Road - Grafton Meditel Hotel",
    "S34854 - ARWCF Gate House - Roof Gutters Works",
    "S34870 - MPI PHEC - Membrane Roofing and Emseal Package",
    "S34872 - Snells Beach Waste Water Treatment Plant Injection",
    "S34874 - Air NZ Hangar 4 (JFC) - Flame Trap 4",
    "R1059 - UOA B503.B41C - Autoclaves Replacement, Floor Repalcement",
    "S34902 - AIAL TH01 – Remedial Works",
    "R1073 - Air NZ Hangar 2 Re-life",
    "S34905 - Kiwirail MWN2 Ngakoroa Station Main Works - Auckland",
    "S34910 - Broadway 255, Newmarket, Auckland -  Canopy Remediation works",
    "R1079 - UoA B230 Screeding",
    "S34914 - Waitemata (Britomart) Train Station Escalators",
    "S34947 - Rosedale Bus Station and Corridor - Tanking",
    "S34956 - Beresford Square 16-18",
    "S34966 - East Coast Bays Community Centre Refurbishment",
    "R1138 - MANGERE WASTEWATER TREATMENT PLANT PREPERATION & SEDIMENTATION TANK 3&4 PR",
    "S34972 - Orams Existing Carpark - Sealant Works",
    "S34975 - Station M - 21 Manapau Street, Meadowbank - Precast Sealant",
    "R1148 - Ardmore B2 Tank Roof Replacement",
    "S34981 - Murray Halberg Retirement Village - Remedial Waterproofinga",
    "R1150 - Holcim, Onehunga Harbour Road, 57 -  Concrete Repairs",
    "S34984 - 7 Winn Road, Freemans Bay - Waterproofing Works",
    "R1155 - Concrete Repairs - Small Sales",
    "R1159 - Middlemore Hospital,Hospital Road 100 , Otahuhu, Auckland–Concrete Repairs",
    "S34996 - Three Kings - Maintenance Annual inspections",
    "S35000 - Cancer Society Whangarei Accommodation Lodge",
    "S35010 - ADHB A01 Stair Area - Coating Works",
    "S35013 - CDC HV2.2 - Roofing",
    "S35019 - 44 Polygon Road - Polygon House Stage 1",
    "S35021 - PaknSave Albany",
    "S35023 - Manawaora Road 285",
    "S35031 - Auckland Airport ITB Roof Remediation",
    "S35035 - BEKS2025 Limited",
    "S35036 - Bledisloe Cruise Terminal - Tanking",
    "S35042 - AUT, Wakefield Street, 56 -  Roof Repairs",
    "S35048 - Racecourse Parade, 26  -  Sansom Annual Maintenance Inspection",
    "S35049 - Greenside Rd, 101 - Annual Maintenance Inspection",
    "R1213 - Saint Paul Street, 47, Auckland Central -  Northern Façade Concrete Wall Repair",
    "S35068 - Warranty Work - Sansom Ltd",
    "S35072 - Carlaw Park Stage 2 - Seismic Joint Replacement",
    "S35074 - Pipe Penetrations",
    "S35077 - Ascot Office Park - 93-95 Ascot Ave, Greenlane",
    "S35078 - Gibbons Road, 8B -  Membrane Remedial Works",
    "R1241 - Waikeria, Ngaio Prison  - Stage 2 A&B",
    "S35085 - Remuera Road, 464, Auckland - Roof membrane Maintenance Remedial Works",
    "S35087 - 6 Pekapeka Street, Raglan - Tanking Remediation Consultant",
    "S35088 - 19 Ngaiwi St, Orakei - Roof Membrane",
    "S35092 - Medlands Beach GBI - Hays",
    "R1261 - Bunnings Westgate Floor Joint Repairs",
    "S35099 - Island View Drive 47, Gulf Harbour - Newtons",
    "S35103 - 107 Carlton Gore Road  - Drainage Improvement",
    "S35110 - Gould Street 9 - Russell (Beach House)",
    "S35114 - 41C Sandpiper Ave- TPO Roof Membrane",
    "S35123 - 34 Rawene Avenue, Westmere - Membrane Replacement",
    "S35135 - Mt Wellington Estate Warehouse 1  -  2 Monahan Road, Mt Wellington - Tanking",
    "R1290 - Warranty Repair work - Concrete Repairs",
    "S35141 - Vulcan Lane 10",
    "S35150 - MIT Manukau Campus - Interior Plant Room Works",
    "S35154 - Grey Ave 139  Auckland - Annual Maintenance Investigation",
    "S35155 - Greenlane Hospital, Greenlane West  214 - G04 Investigation and Remedial Works",
    "S35156 - Auckland Hospital - A08 Level 6 , Oncology Remedial Works",
    "S35158 - Epsom Retirement Village - Membrane Works",
    "S35163 - Westwater Golf Resort",
    "S2309 - Athens Road 1/59, Onehunga",
    "S2310 - Riddell Rd 283, Glendowie",
    "S2311 - Speights Rd 8, Kohimararama",
    "S2312 - Glendowie Road 12a",
    "S2313 - ILD Australia PTY",
    "R1315 - Block 10 St Lukes Gardens Crack Repairs",
    "S35171 - Mackelvie Street 28a",
    "S35173 - Woolworths Ponsonby - B2 Carpark Storage Room",
    "S35185 - 18 Taurarua Terrace, Parnell - Balcony Remedial",
    "R1327 - Eden Park - West Stand Redevelopment SikaFloor 400",
    "S35190 - Bledisloe Cruise Terminal  - Sikalastic to Columns",
    "R1329 - Britomart Station Core Drilling and PH Testing",
    "S35195 - Lynn Mall Carpark - Seismic Joint",
    "R1336 - WSL Army bay WWTP - Renewals",
    "S35199 - Site 6 - Annual Maintenance Inspection",
    "R1343 - Rosedale WWTP - Concrete Repairs",
    "S35208 - Greenlane Hospital G15 Building - Membrane Investigation Works",
    "S35209 - University of Auckland B315 - Kate Edgar Building",
    "R1346 - Rosedale Bus Station , Pile demolition",
    "R1350 - BR66 CB MDLND - Upgrade",
    "R1356 - ADHB - Pedestrian Walkway Repair",
    "S35224 - 13 Cheshire Street, Parnell - Maintenance Works",
    "R1364 - Great South Rd, 232 Epsom - Remediation",
    "S35225 - Auckland Hospital - Pedestrian Walkway",
    "S35231 - H47 Building - Small Membrane Roof Remedial Works",
    "S35232 - Auckland City Hospital A32 Main Building",
    "S35233 - The Pacifica, Commerce Street - Annual Maintenance Inspection",
    "S35234 - Next Generation Gym - Tennis Court Resurfacing",
    "R1367 - Mangere Wastewater - Biofilter 3",
    "S35239 - Med School - B505 (Pumping Systems)",
    "S35240 - Auckland Airport WP3 BOH and Main Works (Façade)",
    "R1385 - CDC Building 2 Switchrooms Hobsonville",
    "S35248 - Tyler Street. Britomart 59 -  Membrane Remedial Works",
    "S35253 - 456A Remuera Road - Balcony Works",
    "R1390 - Eden Park - Crack Repairs to Block Work",
    "R1392 - Brisbane Street,1, Grey Lynn -  Ramp Remediation",
    "S35258 - The Galleries, Graham Street, 23 -  Maintenance Remedial Works",
    "S35261 - The Statesman Apartments, Parliament Street, 1 -  Annual Maintenance",
    "R1398 - B301 and B303 - Confined Space Investigation",
    "S35266 - Mt Eden Corrections Facility Carpark - Coating Remedial Works",
    "S35268 - Auckland Hospital A08 Level 6 Oncology -  Maintenance Work",
    "R1408 - Cartwright Road, 34, Kelston - Warehouse Floor Remediation",
    "S35277 - The Statesman Apartments - Maintenance Works",
    "R1410 - The Statesman Apartment - Concrete Repairs",
    "S17221 - WTJO Gt Nth Rod 1405 Waterview",
    "S35288 - 8 Lake Pupuke Drive, Takapuna - Remedial Waterproofing",
    "R1415 - University of Waikato - STEM Block C-F Concete Panel Remediation",
    "R1417 - Sale Street, 70 -  Void Breakouts ST00112",
    "S35294 - Starship Hospital Park RD, 2 -  Seismic Cap Flashing",
    "S35295 - H47 Building - Sansom Annual Inspection",
    "S35300 - Milford School - New 10TS Block and Playground and Block 2 &4b Demo",
    "S35304 - Britomart Roof Replacment",
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
21148,VO025,"KTN - Concrete Crack Injection Repairs 
",
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
21148,VO037,"KRD - Concrete Crack Injection Repairs 
",
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
R169,VO001,Apartment J concrete repair,SPM-23566
21148,VO042,"KRD- RX101 (T) & Cetseal Supply 2023
",SI-003042
21148,VO043,"MCL - Mapei Planiseal Coating 
",
21148,VO044,"MCL - Pipe Penetration Detailing 
",
21148,VO045,MCL - Peel n Stick membrate to PVC Waterbar,
21148,VO046,"MCL - Torch on Membrane Patch Works 
",
21148,VO047,"KRD  - Bluey Hose Connector Supply 
",
21148,VO048,"KTN - MC20/50 Patching Works 
",
21148,VO049,Mercury Lane Facade,
22196,VO020,Roof Waterproofing,7/09/2022
21148,VO050,Application of Sikalastic 152,SI-003050
21148,VO051,KRD – MC21 Headwall Repairs ,Email/2403
22196,VO021,Additional Roof Substrate,
22196,VO022,AOT - SUMP H00 Ceiling / Roof Crack injection works,SI-003140
22196,VO023,Concrete Grinding and panel upstand repair,SI-003142
21148,VO052,"KTN - MC20/50 Patching Works 
",
21148,VO053,Temporary Sealant on Level 3,SI-003150
22196,VO024,Wellesley Roof - RAB board temporary sealant,SI-003181
22196,VO025,Separation Flashing,SI-003183
22196,VO026,L0 internal air seal works,SI-003243 
22196,VO027,WST Application of Dowsil Firestop for L3/L4 Joints,SI-003276
21148,VO054,Air freight,
22196,VO028,AOT - WST - Installation or Gorter Access Hatch on Roof,SI-003339 
22196,VO029,North L1 air seal,SI-003353 
22196,VO030,WST Façade Structural Cover Plates,SI-003277
22196,VO031,Temporary Waterproofing to the Deck on L2 East,SI-003377
22196,VO032,Wellesley roof - substrate drying,SI-003394
21148,VO056,MC20/50 Dry Crack Repairs ,
21148,VO057,Mercury Lane Grouting Works ,
23159,VO001,Canopy Waterproofing Works,COR-000021
22196,VO033,GL32/E Dowsil sealant in 30-50mm gap from L1 to L4,SI-003498
22196,VO034,AOT-VST SI for nib waterproofing,SI-003649 
22196,VO035,AOT - WST - 600mm long rainsheilf flashing,SI-003687
22196,VO036,AOT - Sealing of scuppers through facade panels,SI-003678
21148,VO058,"Double Sided Tapes for Adit A1 Waterbar 
",
21148,VO059,"Cross Passage Investigation & Injection Works 
",
22196,VO037,AOT - Closure of L1 Western Moisture Barrier,SI-003842
22196,VO038,Exhaust Flue penetration waterproofing,SI-003870
21148,VO060,Adit A1 Shaft Downtime ,
21148,VO061,Mercury Lane Seismic Joints ,
21148,VO062,KRD - Cavity drainage holes at joint intersections ,
22196,VO039,AOT - Flashing for Electrical covers,SI-003924
22196,VO040,AOT - Sikalastic Application for EWS502 - East Elevation,
22196,VO041,AOT - WST Skirt flashings for Penthouse Louvres,SI-004022
23159,VO002,Supply and install of temporary wind break to protect Tapered board.,SI-001383
22196,VO042,Sealant for under parapet buildersworks,SI-004071
22196,VO043,Repair works Gutter overflow Western side.,SI-004067
S34131,VO001,"Replacement of Waterbar around L2 Capping beam (Grid 11 & 12) 

",SI-000041
21148,VO063,"MTE - 10FT  Container Repair 
",7/9 email 
22196,VO044,Proclima solitex to VST soffit,SI-004108
23245,VO001,Freight costs for the materials from Sika,251023
23159,VO003,Additional freight cost due to on-site logistics issues (Reimbursement only),
S34131,VO002,Surface Prep to Grid F Existing Structure ,RFI-000132
22196,VO045,AOT - Base flashing and overflashing and detailing for MEFH Penetrations through roof,SI-004111
23245,VO002,Sika MonoTop-352 N fillet and the sealant,Email14/11
S34131,VO003,Remedial works to damaged waterproofing ,SI-000054
22196,VO046,Facade Flashings at Gutter level,SI-004211
S9000,VO001,HSEQ - Admin,
21148,VO064,MCL – B3 Waler Beam Injection,Email27/11
21148,VO065,Temporary PEF Rod Panel Seismic Joint Weatherproofing Supply and Install,SI-004249
22196,VO047,AOT - Sikalastic and Tremco Detailing for TCL Gutter and Fascia,SI-004109
21148,VO066,Additional Sealant to Louvre Openings,SI-003300
21148,VO067,K Rd Crack Injection MC30 ,SI-004258
21148,VO068,Temporary sealant - L3 to Precast,FCR047574
S34131,VO004,Epoxy Injection for Ground Water,SI-000061 
23245,VO003,Groutfill the baffle rebate using Sika Monotop 412,SI-001411
21148,VO069,Temporary torch-on Waterpprofing for rain water pipe at MNL roof Level L3,SI-004400
23159,VO004,Waterproofing - EBH L2 slab edge to existing building,SI-001773
R169,VO002,9H potential exterior water leak investigation,25/01EMAIL
23245,VO004,Precast Panel Concrete repairs,SI-001715
23245,VO005,Supply and install Sika EMSEAL 150mm to East Concourse Riser,SI-001617
23159,VO005,Slab repairs to Make Substrate Suitable for Warm Roof,SI-001852
21148,VO070,Beresford Square Torch On,
22196,VO048,Southern Parapet Cap Flashing,SI-004056
S34131,VO005,Grid EJ Surface Preparation ,Email06/03
22196,VO049,Removal and Reinstatement of WST roof membrane around gutter droppers,SI-004580
23159,VO007,Temporary membrane for scaffold penetrations to the canopy,SI-002042
22196,VO050,Application of Sikalastic 152 to Skylight Upstands,SI-004597
22196,VO051,Application of Sikalastic 152 to Skylight Upstands,SI050090
S34131,VO006,South Core Membrane Repairs ,000179
S34131,VO007,Waterproof Services Through Existing Building Wall,SI-000077
21148,VO071,Planiseal MR Supply to LKA ,PUR59767
21148,VO072,"Supply & Install of Bitumen Fillet 
",SI-004631 
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
21148,VO077,Mercury Lane Additionall Surface Waterproofing,SI-004716
23245,VO008,TH01 - Sealing office barrier panels,SI-002154
23245,VO009,Carpark - Sealing to top of flashing - Lvl1 Gl C4 - E-J,SI-002120
S34131,VO009,Koolfoam Poly to Triangular Core ,000248
23245,VO010,Sikalastic 152 coating to Speedramp,SI-002195
R444,VO001,"P&G associated with contract works valued at $3,338.67",1159/173
R444,VO002,Concrete Slab Edge Repair,ATS No 176
23159,VO011,Flood testing to roof ,SI-002209
23245,VO011,PP Grout Fill to C3,SI-002285
23245,VO012,Sealant at Precast Barrier Ends along Concourse GL J,SI-002265
R444,VO003,Concrete Slab Chase Repairs 5E & 7A,CI-170 
21148,VO078,Supply and Install of Illmod 600- 30/17- 32,SI-004867
R444,VO004,"BCA-A Approved Documents FC 


",CI-171
S34131,VO010,Plug Former Ground Anchor Locations,SI-000093
23159,VO015,WP1 - L2FS - L1 Fire Door Works,SI-002170
22196,VO053,Sealant over fixings - Stacker door steel & Canopy beam brackets,SI-004890
S34131,VO011,Grid E9 Surface Preparation ,
23159,VO016,Temporary termination on level 03 ,SI-002333
23159,VO017,Canopy remedial sump outlet adjustments,SI-000006
23245,VO013,Temp Roof WP to Progress Comms Rooms,SI-002436
S34131,VO012,Waterstop for the stitches on north core (Core 3) from level 2 to 19,SI-000102
23245,VO014,Stair 5 & 6 Precast Penetration Seals Around Steel Stubs,SI-002457
23220,VO001,S34338 - AUT WH Plant room Waterproofing Remedial Works,S34338
21148,VO079,MLA L0 Glazing Structural Opening Waterproofing,SI-004966
23159,VO018,WP1- L3 plinth update to accommodate DP,Email/2006
23245,VO015,Proclima Adhero membrane to speed ramp opening,VPR-000053
21148,VO080,MLA L0 - Roller Door Entrance Flashings,LKA-SI-004
S34131,VO013,Grid F & M1/MB Precast soft Joint Sealant ,
21148,VO081,KRD MLA Additional Emseal Seismic Sealant,SI-004992
21148,VO082,KRD MLA Additional Cement Waterproofing,SI-005078
21148,VO083,Additional Western Service Block Waterproofing ,
S34131,VO016,Grid F Internal Capping Beam Plastering ,
23159,VO022,PC69 sealant,SI-002676
23159,VO023,Decarb 2 - Detailed Design,COR-000850
23159,VO024,Additional matacryl work to plinths on level 03 roof,CAN508
S34131,VO014,Micheral Chip to Exposed Membrane ,GCOR-00369
21148,VO084,"LinkSeal Installation to BSQ
",SI-005130
21148,VO085,KRD MLA Precast Cored Hole Repairs,SI-005114
23245,VO016,Tender to IFC credit,56787542-3
R444,VO005, Concrete Slab Edge Repairs (curve),CI 219
S34160,VO001,Casali membrane cap sheet colour confirmation,CI-048
S34160,VO002,Carpark / site trip reimbursement,Email/1508
23245,VO017,Tender to IFC ICONCO-VARPS-000,56788190-7
23245,VO018,Prov Sum Extra value works,56788484-8
23245,VO019,Provisional Sum for Detailing,56788484-8
23245,VO020,IFC freight Costs,56788492-9
21148,VO086,KRD MLA West 200mm Seicmic Joint SI,SI-005175
23245,VO021,"TH01 - Level 4 Stair 1,2 & 3 - Wall Closer Details",SI-002748
22196,VO054,WST Roof - remedials to waterproofing membrane,SI-005189
S34131,VO015,Facade & Seismic Joint Works,
23245,VO022,Extra value weep holes to junction of soakers,46
23245,VO023,Top Soaker to terminate baffle on top of panel joints,47
21148,VO087,Freight Costs - Emseal WFR2,
S34131,VO017,Waterproofing Roofing Works,SI-000135
R444,VO006,Holes through balcony from exiting balustrades,CI223
23245,VO024,ACO Drain Sealant application,
23245,VO025,Plywood Joints,SI-002839
23245,VO026,Sikalastic 152 to Sump and Upstand,SI-002840
23245,VO030,Air Freight Charges ,SI-002748
23159,VO025,SP2B/Canopy-  Temporary Membrane / Waterproof around Scaffold Pipe / Removal,SI-003200
S34183,VO001, MH - Volclay to Ground Beams Gridline DY1,SI-324
23245,VO027,Seal the timber frame on L3 GL J/17-18,SI-002673
S34131,VO018,M-03 - Supply and Install of VaproShield Vapro-SS Flashing Tape Over Nuraply System,SI-000148
23245,VO028,Speedramp - Crack Repair,SI-002921
23159,VO026,Waterproofing for tx rooms,SI-003278
S34131,VO019,Precast Joint at window opening - waterproofing,SI-000150
23245,VO029,Concourse East & West stairs landing finishes,SI-002947
23159,VO027,Substrate Repairs prior to Coating Works,Email/2009
S34131,VO020,"L0 Waterbar Replacement 
",SI-000153
S34490,VO001,Tanking Penetrations,
23245,VO031,"Sea freight Cost- Not Included in $512,506.75 Credit",
S34183,VO002,Pipe Penetrations,
S34183,VO003,RX101DH to Construction Joints,
22196,VO055,Application of sealant and sikalastic 152 on blockwall,SI-005300
S34131,VO021,Temporary Torch On Level 3,SI-000156
S34131,VO022,Additional cost for spotter,
S34131,VO023,CR - Grouting Baseplates & Lintel Remedial Works,Email/0210
23245,VO032,Sea Freight - incl Tender to IFC,56788740
21148,VO088,MLA East facade sealant colour matching,SI-005384
S34131,VO024,Supply and install saddle flashing for the termination of the Nuralite system interfacing to the Permatec system,SI-000159
R444,VO007,Concrete column repairs ,CI-259
23159,VO029,WP1 - Temporary waterproofing protection,SI-003460
S34131,VO025,L4 Nib Waterproofing Above Glazed Roof,GCOR-00448
S34131,VO026,Supply and Install of VaproShield Vapro-SS Flashing Tape,SI-000148
S34183,VO004,Waterbar installation to top of Ground beams,SI-426
23159,VO030,WP1 Level 2 CHW Plant Room- Fixing of Internia Base into Waterproofed Plinths,SI-003385
21148,VO090,L3 Mercury Lane Station Waterproofing ,
R169,VO003,Inspection of the upper floors SW corner,24592.12B.
R444,VO008,Balcony Joint Infill,CI-182 
S34131,VO027,Install Ryanspan Pro 50- 30mm Thick,SI-000197
S34183,VO005,Lift Pit Rectifications,
S34160,VO001.1,Labour for Vertical material movement,
23159,VO032,Waterproofing to CLT service penetration,
23159,VO033,WP1 - SP2B/Carousel - Gas Enclosure - Screed to Fall,SI-003592
S34182,VO001,Early Tanking Works -ATP ,
21148,VO091,"Additional EFVM Visits 
",
21148,VO093,B6 Sump Injection & Coating Remedials ,
21148,VO094,Materials Off Site,
S34430,VO001,Scaffolding Access (at cost - charge up),
S34430,VO002,Contingency Sum,
S34430,VO003,Substrate repairs (if required),
S34194,VO001,Level 2 Deck waterproofing - Plinth and Infill Details,R710VO026
S34160,VO004,Roof B Nib Dimension Variance,CI093
S34160,VO005,Level 35 lift motor roof bin reinforcing steel remediation,CI097
S34131,VO029,CR: Grouting to Base Plates,SI-000170
S34131,VO030,CR: Concrete repairs,SI-000170
S34131,VO031,CR: Structural Columns (Columns to Wall Interface),SI-000170
S34131,VO032,CR: Grouting of Plates (Plates to Walll Interface),SI-000170
S34131,VO033,CR: PFC Grouting,SI-000170
S34131,VO034,CR: Supply Electric Scissor Lift,Email 20/1
S34183,VO006,MH - Volclay Lift Pit & Ground Beams,
S34160,VO006,Prototype Waterproofing,ATS 313
S34131,VO035,Sika AT Façade to the joints between the Precast lids,SI-000239
S34131,VO036,Temporary Waterproofing,SI-005695
23159,VO035,PC68 HV Rooms: Temporary bunding and torch on (URGENT),
S34490,VO002,Aquaron Coating to Upper Concrete Slab ,
S34490,VO003,Additional Preprufe 300R to Upperslab,
S34160,VO007,Roller Door Damage,Email10/12
S34160,VO008,Level 33 existing nib demolition,ATS 280
S34160,VO009,Joinery Nibs,ATS 302
23159,VO036,"L1 Temp waterproofing. GL 35, IA, 36A",
21148,VO095,BSQ Dwall Waterproofing Injection ,SI-005640
S34131,VO037,Materials Off Site,
R444,VO009,Concrete slab chase repairs - Apartment 5E and 7A ,CAN 85
22196,VO056,Aotea Station Façade Works,
S34131,VO038,GL-M1 Replace damaged Ryanspan ,SI-0002602
S34160,VO010, Balcony Substrate Preparation,7767-339
S34160,VO011,Level 33 north elevations screed remediation,7767-344 
R444,VO010,New concrete nib - Ground floor,CI-272
S34593,VO001,Additional Works B2-141 - Dressing room 9,
S34183,VO007,Sealant works on isolation joints,
22196,VO057,Waterproofing strip to seismic nib,
S34131,VO039,Level 3 column dry packing,SI-000273
S34160,VO012,Nib and Column concrete repair,ATS7767251
S34160,VO013,L32 2 x scuppers to be squared,ATS7767305
S34160,VO014,Removal of existing sealant to horizontal & vertical gutter joints ,CAN 84
S34131,VO040,Volclay Waterstop and Seismic Cover Flashing,SI-000285
S34131,VO042,Goose neck for lightning cable,SI-000292
21148,VO096,Additional ILD Visit South Western Corner ,SI-005771
21148,VO097,"Additional Protection Sheets to West Elevation Membrane 

",SI-005792
S34131,VO043,Mayoral Drive Entry Waterproofing,SI-000291
22196,VO058,Crowne Plaza Airbridge Waterproof Membrane,SI-005811
21148,VO098,BSQ precast panel,SI-005809
S34131,VO045,Pipe Boot Flashing,SI-000326
S34182,VO002,Credit Early Tanking Works - ATP,
23159,VO038,Remove existing chevaline dexx ,SI-004215
21148,VO099,Additional ILD Visit to SW Corner ,
21148,VO100,BSQ Access Hatch Waterproofing Works ,SI-005809
S34160,VO015,Level 32 - Panel Joint,AT7767-381
S34194,VO002,Hiab for Vertical Lifts,VDRCT 311
S34160,VO016,Rebate Infills L30 & L31 Joinery Openings,7767-357
S34131,VO046,Temporary Waterproofing to Roof ,
S34160,VO017,7767-404 - Balcony precast joint treatment,ATS776 404
S34160,VO018,Consent Amendment B,7767-394
22196,VO059,Crowne Plaza Airbridge Waterproof Membrane-Repair at the northeast corner,SI-005892
S34160,VO019,L33 Slab Edge Packing ,CI163
S34131,VO047,L1 Grid E9/EA-EB Wall Surface Prep ,
R444,VO011,Concrete Slab Chase  Repairs Unit 7A,CI382
S34183,VO008,Sikalastic 152 to Window Sill,SI-720
S34131,VO048,L2 Sealant Joint Against Column ,SI-000291
21148,VO101,KRD MLA roof chiller plantroom weatherproofing,FCR-060505
S34490,VO004,Chevaline Dexx to Northern Deck ,
S34490,VO005,Ardex to Entrance porch ,
R344,VO003,Monthly H&S Meeting,
R344,VO004,Staff Training,
R344,VO005,HR Meeting,
S2302,VO001,Monthly H&S Meeting,
S2302,VO002,Staff Training,
S2302,VO003,HR Meeting,
S34160,VO020,Grinding and plastering, CI 167
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
S34160,VO021,New Existing Transition Junctions Level 30 & 31,AT7767/375
S34131,VO050,Screed Credit,SI-286
23159,VO040,Supply and install of Monkey toe foot pads ,SI-004508
22196,VO061,Sikafloor Multidur EB-31 Coating ,003544
S34160,VO022,Dry Packing Under Structural Steel Base Plates,CI 169
S34160,VO023,L30 & 31 Exposed Baseplates,CI 200
S34194,VO003,L4 Parapet separation flashing,VDRCT-0004
23159,VO041,Seal as directed areas on pc68 roof,SI-004597
R444,VO012,Slab Infill for Wastes CMBND,CI425
23159,VO043,Rain Preperation - Temporary Waterproofing works,SI 4657
S34182,VO004,EBS Pit - Sikaproof to EBS 125 Credit ,
S34131,VO051,Roof -Sika Hyflex Facade Sealant,SI-000421
S34160,VO024,Patch exposed reinforcing to concrete columns,7767-467
S34593,VO002,Basement Level 2 Kitchen - Remedial Waterproofing,
S34160,VO025,Nib Extension,AT7767-441
S34131,VO052,Supply of collars for copper pipe on level 4 roof,SI-000439
S34182,VO005,Re Detailing of Pipe at Service Pit (Grid D5/H10) ,SI-000708
S34160,VO026,Patching Concrete Blowout on External Parapets,7767-474
S34131,VO053,Transformer Room Trench Injection,SI-000468
S34482,VO001,Lift Pit B1B Structural Toe Changes  ,SI-000112
S34160,VO027,MV020- L33 north elevation repair to slab edge,7767 -468
S34490,VO007,Additional Torch on Works,
S34490,VO008,Additional Works to Pool side/Garden box,
21148,VO104,BSQ - Station Perimeter Mapelastic Remedials ,
22196,VO062,Supply of Sikafloor 377 to Air Bridge ,
S34131,VO054,Level 2 Sealant,SI-000462
S34160,VO028,Parking Fee,Email 11/4
S34323,VO004,H&S meeting Woolworths vouchers,
S34131,VO055,L4 Mechanical Louver Details ,SI-000327
S34131,VO056,Supply & Installation of Bitumen Fillets ,SI-000476
S34131,VO057,Heritage Roof Revised Details ,VPR-000073
S34160,VO029,MV 016 level 32 south balcony penetration,CI 195
22196,VO063,Sikafloor Car Park Deck System to Crown Plaza Airbridge,
S34131,VO058, Level 4 Diesel Exhaust Flashing,SI-000503
23159,VO045,"AIAL WP1- Terminal Integration  - Flood testing to remaining gutters

",CAN414
S34131,VO059,Main Entry Canopy Remedial Works to Upstand,SI-000505
S34131,VO060,Additional Sika Hyflex Sealant - Level 2-5,SI-000504
S34183,VO010,Sika EMSEAL boot flashing,SI-954
S34131,VO061,Sealant to Grid M2 - Abseiling,
22196,VO064,Additional Waterproofing & Flashings over Exposed Foundations ,
S34131,VO062,Damage to Nuraply Membrane on Heritage Roof,SI-000512
S34182,VO006,Sprinkler Valve and SW Chamber to EBS Pit Waterproofing ,
21148,VO105,L2 bolts waterproofing,SI-006157
21148,VO107,Additional Sealant to Lourve Openings,SI-003300
S34131,VO063,Waterproofing Pipe Penetrations to Vector Ducts ,
S34194,VO004,CPRW Waterproofing CANS - Combined,VDRCT 421
S34490,VO009,Powder Room and Storage – Newtons,
R444,VO013,New Concrete Nib Extension & Concrete Topping,CI-464
S34160,VO030,Spandrel Soffit Plastering (Levels 31 & 32),ATS7767/52
S34182,VO007,Additional Works for Sprinkler and Sewer Chamber,SI-000866
21148,VO108,Waterproofing HDPE Pipes,SI-006215
21148,VO109,Northern elevation cores sealant,SI-006220
S34360,VO001,L2 Meeting room & Office,
S34160,VO031,CI251 Precast wall on GL-D West Elevation,CI251
S34754,VO001,MMH building C88 Manawanui meeting house,WO55351
S34754,VO002,"Carrington Site  -C03 Rehab Plus, Pt Chev / Ground Floor ",WO55557
S34754,VO003,101 Sarsfield Street - Deck leak investigation (Urgent),Email12/06
S34754,VO004,"Auckland Hospital - Building A01, Support Building AK / 16th Floor",WO #55763
S34754,VO005,Auckland Hospital - Building A08 Oncology AK,W/O #55896
S34183,VO011,Sikafloor 2510W to Lower Ground Floor Plant Room Plinths,
S34183,VO012,"Waterbar installation in Energy Pit - concrete wall and slab joint , pipe penetrations",SI-1121 
R444,VO014,Repair Concrete Nib wall and Saddle flashings aligning to cladding,CI 453
S34754,VO006,"Greenlane Hospital Building G16
Related work from WO #55612 and WO #55492",WO #56080
22196,VO065,Planiseal MR Green Concrete Coating ,
21148,VO110,Beresford Square Mapelastic Smart ,
S34772,VO001,Temp and final detailing for posts to deck,Email 2306
S34754,VO007,"56123/ 55007 - Greenlane Hopsital - Building GO4, 6th Floor",WO 56123
S34754,VO008,"Greenlane Hospital, Building G15 Greenlane / 7th Floor relates to w/order 53116 and 56312",WO #56312
S34160,VO032,Bostik Dampfix 3 to Level 30 & 31,ATS525
21148,VO111,Adit A1 Closure Additional Items ,SI-006279
S34182,VO008,Re-taping of Column Joints,SI-000993
S34131,VO065,Grid EJ Blockwall Wateproofing ,SI-000601
S34490,VO010,Swelltite to Retaining Wall Behind Stairs ,
S34578,VO002,SP1 Level 1 and 2 Grid E+ seismic joint & Emseal,CI#101.20
S34591,VO001,Reprofiling of Piles,
S34754,VO009,Greenalne Hospital Building G01 Greenlane,W/O 56556
S34160,VO033,Precast Spandrel Grinding ,7767-593
S34754,VO010,"Auckland Hospital AO1, L16 Plant Room - Tank Room (PR0117)",WO #58171
23159,VO047,PC68 MSB-B/TX waterproofing protection,SI 5111
S34131,VO066,Level 2 Courtyard - Exhaust Duct Precast Panel,SI-000657
23159,VO048,Level 2 Grid IA - Seismic Gap - Install Temporary Roof - Waterproof ,SI-005134
S34754,VO011,Auckland Hospital L16 -AO1 Support Building,w/o 83828
S34754,VO012,"Auckland Hospital - Ceiling Leak Investigation
A35 - Te Whetu Tawera - Acute Mental Health Unit room 1.156",WOT0084812
S34131,VO067,Site Waterfeed Waterproofing ,SI-000676
S34131,VO068,L0 Gid EJ Nib Wall Waterstop ,SI-000669
R444,VO015,Prep work for Concrete Beams on North Balconies,AT1159/926
S34591,VO002,Bund site concrete/pile upstand with Sika Plug,SI-80
S34754,VO013,Auckland City Hospital A21 - Wall Penetration Repairs,WOT0088001
S34624,VO001,Off-Site Storage Cost,
S34160,VO034,Roof A and Roof C Council Items,7767-614
S34591,VO003,Pile 26 Additional Work,SI-92
S34591,VO004,Pile 58 Remedial Works,SI-98
23159,VO049,WP1 - SP2C - Level 2 Grid IA - Seismic Gap - Removed Waterproof over the stair plate,SI-005237
S34183,VO014,Stand By Time,
S34160,VO035,Widen concrete Nib,CI 279
S34591,VO005,Remedial to Pile 4 edges in Zone 3,SI-104
S34160,VO036,Roof A & C cover board fixings 150mm from sheet edges,CI-286
S34131,VO069,Level 0 Trench in GF Slab,SI-000634
S34131,VO070,Laundry Services Penetration Waterproofing ,SI-000652
S34131,VO071,Roof Detailing to Threaded Rods & Steel Posts ,SI-000621
R444,VO016,Self levelling credit,Email24/07
23159,VO052,Water-proofing to Temporary UC Prop Penetration at E4 &E5/VVa,SI-005299
23245,VO033,Level 4 Office Plant Waterproofing,SI-003357
S34065,VO001,Z1 - Unbonded Waterproofing Generator Pits,SI-001274
23159,VO053,Prep for Column Top Plates on L2 Mezz,SI-005339
S34131,VO072,Waterproofing Membrane to Heritage Parapet Capping,SI-000758
S34131,VO073,Grid F External Precast Panel Sealant,GCOR-00896
S34545,VO001,Additional Pile Detailing,SI-000222
S34545,VO002,Supply and Install Sika Blackseal/Fosroc Mulseal,SI-000234
S34772,VO002,Joinery Remedial Waterproofing,
R444,VO017,Slab extension (level 3 and 5) ,CI-546
S34591,VO006,Additional detailing to Pipe penetration,SI115
S34545,VO003,Replacement of Waterbars,SI-000286
S34545,VO004,Additional Waterbars,SI-000286
S34754,VO014,Greenlane Clinical Centre - Head Flashing Repair,WOT0105309
S34591,VO007,Pipe Penetration Detailing,
S34591,VO008,Additional for Preprufe Detailing to Pile Setdown,
S34545,VO005,EDS Sump Remedials,SI-000442
S34131,VO074,Level 4 - Oil spill on roof area - Remedial on Contaminated Waterproofing ,SI-000815
S34131,VO075,Chemical Discoloration on Plant Roof Membrane ,SI-000829
S34194,VO005,Level 2 Deck Generator Structure – Plinths (GCOR-000111),R710VO77
S34131,VO076,L2 Egress Stair Seal and Flashing,SI-000816
S34323,VO006,Cricket Costs,
S34182,VO009,Waterbars to Level 1,SI-001574
S34183,VO015,Low profile water for link bridge LG,SI-1505
S34183,VO016,Waterbars and sealant works in the link bridge pockets and part of the main building,
R444,VO018,Apartment 2B Concrete Column Remediation,CI 461
S34131,VO077,Level 0 Canopy Down Pipe - Tile Penetration Cover Flange,SI000853
S34131,VO078, T Flashing Trim,SI-000871
S34160,VO037,Precast Concrete Deck Joints,CI-661
23159,VO058,L2 Mezz anchor plate waterproofing  ,SI-005623
S34042,VO001,Temporary termination  to Podium Sumps,SI-V-00025
S34183,VO017,Sikafloor 2510w to Plantroom floor,SI 1262 
23159,VO059,L2 grid IA nib waterproofing ,SI-005658
23159,VO060,L2 E4M platform WPM remedials/repairs,SI-005673
R444,VO019,"Floor Levels In Existing Lobby, New Gym, Entrance",CI 579
S34131,VO079,Supply and install stainless steel door thresholds,SI-000917
S34545,VO006,Elect - LV Switchroom - GL11 Additional Electrical Conduits,SI-00044
S34131,VO080,Additional/Change in Scope - Mayoral Drive Entry Waterproofing,SI-000291
S34131,VO081,Void Room Wall Flashings ,SI-000826
S34545,VO007,Waterproofing to lift pit wing wall ,SI000322
S34545,VO008,PVC water bar and additional detailing  ,SI000429
S34482,VO002,Application of Dowsil 790 to Spandrel Panels,
S34131,VO082,Provisional Sum for Future Variation Works,
22196,VO066,Aotea air bridge BAS expansion joint,
22196,VO067,Sea freight for BAS Parking Span 150 expansion joint,
22196,VO068,Supply and apply epoxy grouting to gap between substate and expansion joint,
S34754,VO015,"A02 - Starship Children's Hospital
A02 L1 - HDU Lounge


",WOT0121636
S34754,VO016,"A01 - Support Building
Floor: L4 - Level 4
",WOT0118127
R344,VO007,KiwiRail medicals / Tunnel operations,
22196,VO069,Aotea foul water sump – Additional Floor Coating (Sikagard 62),SI-006349
R444,VO020,Concrete nib cut on Ground floor,1159/1209
R444,VO021,Level 8 Grinding/ Cleaning of balconies,1159/1206
R444,VO022,Seal Drilled Scaffold Holes,1159-1243
R878,VO001,Structural Column Investigation,EMAIL7/10
R444,VO023," Sikafloor Level 30 
",CI 650
R878,VO002,Grinding as advsied - M² allowed for - 60m²,Email8/10
S34545,VO009,GL C Membrane repairs,SI-000493
21148,VO112,Flashing Around BSQ Louvre Fixing Angle ,FCR-065250
S34160,VO038,Additional membrane works to Pipe Blocks on Roof A & C as per Babbage’s instruction,
S34131,VO083,Sikalastic 152 to Entrance Opening ,SI-000943
S34042,VO002,Prep work for water proofing the podium gutter sump,SI-000278
S34754,VO017,"A32 - Auckland City Hospital (Main Building)  Level 9
",WOT0130811
R444,VO024,CI-483 - Ground Floor MV001 APPRVD,CI 483
23159,VO061,CAN - 844- Additional Detail for Concrete around Unistrut supports,SI-005825
S34591,VO009,Replacement of waterbar on stitch joint,SI-255
S34545,VO010,EDS - Removal and reinstatement of water bar,SI-000540
S34160,VO039,Hydrotech detailing to Balustrade Fixings,
S34160,VO040,Additional 1 new fixing installed,
S34160,VO041,Additional kettle hire,
21148,VO113,TVS & ADIT A1 Drained Floor Injection,
S34160,VO042,Credit as per agreement with Aspec: VO002-036,
23159,VO062,Working outside of Ordinary hours to apply the 2 x Topcoats,SI-005840
22196,VO070,Application of 11FC Black to the station facade,SI-006576
R878,VO003,Beam Demolition,Email 20/1
21148,VO114,SW Mercury Lane Station Corner Reinstatement of Membrane Protection ,
S34065,VO002,Credit - Original Contract Schedule,
S34065,VO003,Auckland Airport Domestic Processor Pier & FLB Tanking Works,
S34160,VO043,Additional Kettle Hire credit,
S34042,VO003,Additional Grinding for Podium gutters prep,SI-00028
S34042,VO004,Podium - Gutters Temp Protection Supply,SI-00028
S34545,VO011, New Rebate Zone 1 preprufe detail  ,SI-000286 
S34545,VO012,Additional Pipe detailing to LV room,SI-00044 
R444,VO025,Column L2 Repair (RFI 269),CI 503
R444,VO026,Repair of 7A chase,CI 649
S34874,VO001,Additional Waterstop,PO 197054
S34543,VO001,Pipe penetrations to perimeter of lift pit/underslab interface,
S34874,VO002,Commercial Discount ,
S34194,VO006,New plywood plinths membrane detailing ,R710/VO088
S34194,VO007,Stair 4 Vestibule concrete nib at steel beam ,R710/VO089
S34194,VO008,Stair 4 Vestibule reclad (Level 2 deck level),R710VO090
S34131,VO084,Credit Adjustment - Facade Sealant,
23159,VO063,L2 CHW plantroom WPM remedials,SI-005886
S34545,VO013,Detailing to piles,
S34593,VO003,Wintergarden Area Newtons CDM Works ,
23159,VO066,WP1 - SP2C - Level 1 Grid 35 - ED - VVA - Removed Temporary Waterproof,SI-005900
R444,VO027,Concrete column repairs ground floor.,1159/1323
23159,VO068,CAN 958 L2 Roller door gap infill around skirting,SI-005771
21148,VO115,Penetration Infill ,SI-002860
S34543,VO002,Sealant to block wall to allow MSB to be installed,
S34545,VO014,Zone 2 repairs due to concrete splatters,
S34042,VO005,Podium - Gutters Temp protection Supply & Sill Protection ,VO-000047
S34545,VO015,Zone 2b pour stop ends – Additional CJ tapes and Replacement of Waterbars,
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
S34182,VO010,Sikaproof P to side of beams + Sikaproof A tape termination to DPM ,SI-002415
S34591,VO011,Sealant Waterproofing details,SI-281
21148,VO117,Adjust Flashing,SI-004988
S34482,VO003,HDPE & Termination to Revised Area,
S34482,VO004,Geofabric & Testing to Revised Dragowrap Scope ,SI-420
S34482,VO005,Dragowrap Vapour Barrier to B1A & B1B,
S34543,VO003,RX-102 Replacement,SI-4590
R1059,VO001,UoA Autoclaves Replacement (Subsequent Visits) – Floor Coating – 143 Park Road (Autoclave 1 Only),MCA-1 
S34160,VO044,Hydrotech Repairs,7767-730
S34578,VO003,MV66 Cross Brace Strengthening,
23245,VO034,Leak at stair 2,GCOR-03916
S34482,VO006,Temporary Waterproofing to L3 Columns ,SI-000562
S34543,VO004,GARAGE Building - Matacryl Detailing,SI 4721
S34482,VO007,Sikadur 42 to Service Pipework ,SI-000550
21148,VO118,Mercury Lane - Sealing pipe annulus gap between D-wall and pipes,SI-006847 
S34578,VO004,Seismic upgrade and weathertightness remediation,
R626,VO001,Dead time ,Dec 25
23159,VO070,Drain Connection to mechanical plant,SI-005616
S34183,VO019,"Credit - VO11, VO13 & VO17",
S34183,VO020,Sika Floor 2510W,
S34545,VO017,Zone 3 - Replacement Preprufe,SI-000688
S34194,VO009,Alsan Flashing Quadro Termination Detail to Stairwell,SI-000658
S34194,VO010,Spotter – Chevaline Coverflexx System ,SI-000655
S34194,VO011,Level 2 Membrane ILD re- testing ,SI-000656
23159,VO071,WP1- SP4-L2 Waterproofing remedials.,SI-006038
22196,VO072,Termination of the existing Wabo Expansion Joint at Planter Box,SI-006838
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
S2302,VO005,Health Checks ,
S34591,VO012,Membrane Repairs - Damage to waterproofing GL 9,SI-405
S34065,VO004,Supply and installation of Geo textile,SI-002996
S34482,VO013,Supply only 2x Scuppers,SI-000670
S34065,VO005,Pipe penetrations through membrane,SI-003273 
21148,VO119,BSQ Dwall & Pipe Penetration Works ,SI-006932
S34228,VO003,Window Leaks,
S34444,VO001,Detailing of Existing Pipework,Email/2701
S34754,VO020,Auckland City Hospital - A08 - Cancer & Blood Services (Oncology),WOT0176495
S34754,VO021,Greenlane Clinical Centre -G15 - Cornwall Complex,WOT0176393
S34754,VO022,"Auckland City Hospital A02 - Starship Children's Hospital
L7 - Level 7

",WOT0175655
S34766,VO001,Digging External Pump Chamber ,
S34042,VO006,Podium - Light Grinding prep for waterproofing,SI-000391
S34772,VO004,Epoxy Infill to Window Rebate,
S34160,VO045,Additional ILD Testing,7767-772
R444,VO030,Block wall outside GF west bay window,CI-824 
S34482,VO014,Supply Equus Seperation Layer Tape for Box Gutter Detail,SI-000717
S34545,VO018,Waterbar replacement zone 3,SI-000911
S35021,VO001,Supply and installation of Swelltite membrane to exterior garden box,
S34183,VO021,Staff Entry DPM ,SI-1305 
S34545,VO019,GL E - Termination Detail,SI-000942
S34543,VO008,Aquafin 2K W/Proofing to face of Nib,SI-5238
23245,VO036,Waterproofing around slab penetrations,SI-003482
S34160,VO046,ATS No 7767-788,
23159,VO074,WP1: L3 Roof - Removeable Walkway Drawings - additional waterproofing,SI-006132
R444,VO031,Additional nib adjacent to front entry,CI-856
22196,VO074,V11 Lift Sump Leak Repairs ,SI-006993
S34183,VO022,Replace damaged Balco cover plate,SI-2056
S2302,VO006,Mask fitting,
S34545,VO020,Zone 4 L1 Slab Works,SI-000993
S35023,V001,Travel & Away Allowance,
S34543,VO009,Garage Building Roofing,
S34582,VO001,Membrane reinforcement over cracks,
S34582,VO002,Supply and install of bollards,
S34582,VO003,Supply and Install of Wheelstops,
S34582,VO004,Scaffolding and Shrink Wrap,
23159,VO075,WP1 SP4 Waterproofing remedials.,SI-006251
S34543,VO010,Sealant to Block Walls,SI-5263
S34466,VO001,Boundary Wall Temporary Waterproofing ,
S34981,VO001,Back Up Pump Preparation & Installation ,
S34194,VO013,Rainwater Leak from L2 Deck into Golf Lounge - Membrane Plinth Works,P0003974
S34543,VO011,Crash Barrier & Bollard Fixings,SI-5341
S34160,VO047,Hydrotech Repair L32 North,ATS No 776
S34545,VO021,Removal of Preprufe,SI-001050
R1159,VO001,Concrete Repairs ICU North,CVI 126
23159,VO076,L3 Door Sill Flashings,SI-006253
S34477,VO001,Additional Costs,
S34183,VO023,Plant Area Credit,
S34183,VO024,Precast Jointing Variance,
S34631,VO002,B240 Basement Floor Remediation Works,SI-000564
S34631,VO003,Blackseal to UC columns,SI-000549
S34477,VO002,Material Cost Escalation,
S34648,VO001,Grid Z/D - Apply Sikadur-32,SI-58
S34591,VO013,Adjust waterproofing terminaton on GL:E,SI-535
S34444,VO002,Credit Planter Box Structural Repair Works ,
S34444,VO003,Revised Planter Box Structural Repairs ,
S34444,VO004,"Investigation, Digging & Remediation of Planter Beside Entrance Ramp ",
R878,VO005,Stage 1 Column Reinstatement,SI 11
S34981,VO002,Supply and install new probes as the previous probes were missing,Email/2003
R937,VO001,Materials  on site,Email23/03
R878,VO006,Men Change Rooms columns,SI 11
S34539,VO001,Supply and install Scuppers,SI-571 
S34763,VO001,Credit Value of works - Aquadrain Deletion,
S34545,VO023,Membrane Termination Detailing with Silcor HB Band of 500mm,
S34545,VO024,Membrane Detailing of Membrane with Protection Sheet of NPX Layer,
S34545,VO025,Detailing to Retaining Wall as per Structural Setout,
S34482,VO015,"Credit - Drago Wrap to Ablution, Sprinkler and Pump Room",
S34482,VO016,Balco Seismic Joints,
S34482,VO017,Air Freight - Provisional Sum,
S34482,VO018,Powder Coating - Provisional Sum,
23159,VO077,L3 Door Sill Flashings - Installation,SI-006382
S34582,VO005,Contract/Variation Credits,
S34543,VO012,Supply and install Nuralite fixing plates ,SI-5480
S35023,VO001,Additional Negative Panel Detailing,
S34065,VO006,Installation of asphalt protection to nibs ,GCOR-02138
22196,VO075,B1 Ceiling & S23 Corridor Leak Review & Remediation ,
23159,VO078,Air NZ Wedge - Temp Waterproofing,SI-006393
S34539,VO002,Temporary Waterproofing to Risers L2 and L3,SI-580
23159,VO079,SP5 L1 & 2 Water Drainage Control,SI-006396
S34482,VO019,Supply only 2 X 200mm X 75mm Scuppers ,SI-000955
S34754,VO023,Auckland Hopsital - A01 Support Building L3 Leak Investigation,WOT0209652
S34183,VO025,Remove seismic cover plates on main link ,SI-2204
R878,VO007,Grid 6 beam remediation,Email31/03
R878,VO008,Les Mills Concrete Repairs ( Beam and columns)  ,Email01/04
S34160,VO048,Down Pipe Apron Boot Flashings ,AKL-505637
S34539,VO003,Packing sill angles for membrane,SI-605
S34683,VO002,Penetration Detailing and Temporary Waterproofing,
R344,VO008,2026 Flu Vaccine,
S35088,VO001,1x outlet & 1x overflow,
23159,VO080,WP1-SP4 L2 East corridor Hydrant cupboard Waterproofing,
S34591,VO014,Vertical sealant to GL D Precast Panels,SI-609
S34183,VO026,Sika Fillets to Plant Room,
S34482,VO020,Level one carpark substrate repairs as required,
S34477,VO003,Waterbar replacement ,
S34683,VO003,Gridline 33 Recoat Works,
S34591,VO015,Additional detailing to pipe penetration,Email24/03
S34183,VO027,Reinstate transition flashing,SI-2283
23159,VO081,Waterproofing to L2 Lounge south and north façade Nibs,SI-006453
S34183,VO028,Install flashings and seal against existing building - Link 5 & 6,SI 2287
S34539,VO004,Seal All Penetrations L5,SI-642
R878,VO009,,
23159,VO082,Level 3 Warm Roof - ILD Retest and repairs to defects as per site instruction,SI-006472
S34482,VO021,Concrete Repairs to Slab Edge Grid 4 ,SI-001074
S34539,VO005,Sample/Mock-up ,
S34763,VO002,Membrane Replacement,SI-17
S34482,VO022,B1 Concrete Screed,SI-000950
S34631,VO004,Ground Anchor Penetration Detailing Along Gridline SC Capping Beam ,
S34582,VO006,Additional Cost Value due to Substrate Undulations & Unevenness,
S34482,VO023,Grid H Aquafin 2KM Pipe Penetration Detailing,SI-001088
S35023,VO002,Sika Guard - Credit ,
23159,VO083,Waterproofing to level 1 hydraulic riser night works,SI-006495
S34482,VO024,B2/B1B Precast Seals – extend sealant by 50mm,SI-001096
S34543,VO013,Main & Secondary Core Roof Penetrations,SI-5837
S34543,VO014,Re-apply matacryl membrane to the top of nib Level 5,SI-5926
S34772,VO005,Tapered PIR Insulation Works to the Level 3 Area ,
S34543,VO015,Levels 4&5 new outlet matacryl application,SI-5927 
S34160,VO049,Roof C Membrane Repairs and ILD Re-Test, 7767-841
R1159,VO002,Damaged Concrete Remedials - ATC230,CANs 19a
R444,VO032,Balcony Scaffold hole Repair/ Infill,1159/1884
R444,VO033,Level 7 Balcony Concrete Repair,CI 941
23159,VO084,"Level 1 wet,mech riser waterproofing patching",SI6552
S34582,VO007,Credit for Hire of Dehumidifier and Dryer used by Orams,
S34543,VO016,Matacryl LM to Channel Drains,SI 5992
S35135,VO001,Additional supply and installation of Voltex membrane around pad footings,
S34591,VO016,Temporary protection over membrane at GL K 8/K,SI-694
R1159,VO003,M3 Burns - Exposed Reinforcing,PO5057729
S34624,VO002,UoA - L6 Overflow Works,HA022276
S34543,VO017,"Reapplication of waterproofing, section of ground to Level 1 ramp",SI-6122 
S34539,VO006,Scupper membrane exposed,SI 715
R444,VO034,Entry Ramp Screed,CI 994
23159,VO085,WP1  MKT Platform 1 Hatch Ladder Extra  Layer Membrane,SI 6604
22196,VO076,Maintenance Inspection - Expansion Joint,
R444,VO035,Ground Floor Bay Window Dry Pack,CI 1000
S34042,VO007,Detailing to additional plinths,
R1073,VO001,,Email25/5
R1073,VO002,Additional Bracing Steel Underneath for 20 off plates,Email25/05
S34482,VO025,Credit B1A Aquafin - No Access ,
R878,VO010,Change Room Refurbishment,SI 50
S34582,VO008,Additional cost for stage 3b due to substrate undulations & uneveness,
S34539,VO007,Temp Waterproofing  Podium Penetrations,SI 729
S34910,VO001,Weekly rental charges (04/05/2026 – 01/06/2026),
S35013,VO001,Transformer Temporary Waterproofing,SI35
S34543,VO018,Main Core Floor Finishing ,SI-6206
S34543,VO019,L3 Point Drain,SI-6239
S34543,VO020,Various Sealant Works,SI-6221
S34183,VO029,Additional Cetcoat,SI-2447
23159,VO086,PC68 Coatings - Remediation of the Mechanical Damage to the Coating Areas,SI-006662
S34539,VO008,Temporary Waterproof L6,SI-748
23159,VO087,WP1_SP5 ground floor temp waterproof,SI-006683
S34631,VO005,Replace waterbar in lift pit,SI-001187
S34631,VO006,Remedials to the Volclay between GL D/E - 1/2.,SI-001188
S34754,VO024,Auckland Hospital - A35 Te Whetu Tawera: Acute Mental Health Unit,PO 4259181
S34543,VO021,ILD Repairs to matacryl areas all levels,SI-6295
S34543,VO022,Application of Sikadur 31,SI-6249
R1059,VO003,B41 Floor replacement (UoA B03.B41C) - Main Lab Flooring,Email8/06
S34323,VO009,Mid Winter party 2026,
S34543,VO023,GF to L1 Ramp Works,SI-6329 
R444,VO036,Concrete / Mortar Removal - 1B Terrace,1159/2056
23159,VO088,Sita roof and gutter,
23159,VO089,Additional Gutter Membrane Works,
S34543,VO024,Chase Cuts & Matacryl to L5,SI-6343
S34482,VO026,Application for sealant to the joint,SI 1231
S34482,VO027,Installation of Flashing,SI 1237
R937,VO002,Level 6 Floor Levelling (Ardex K900BF),SI778
S34183,VO030,Supply and Install HAS04 Cover Plates,CI 1702
S34183,VO031,Reinstall of cover plates and base members on link 1,SI 2476
S34183,VO032,Supply and Install flashings on link 2,SI 2457
S34183,VO033,Plant Room control joint sealant works,SI 2496
S34482,VO028,Supply and installation of tape,SI-001285
R765,VO002,Concrete remove and replace ,PO5058837
S34183,VO034,Defect remedials – damages to coating ,SI-2467
S34183,VO035,Waitakere Hospital - Seismic joints variation,CAN158&164
S34631,VO007,Thermal Insulation to the internal face of the capping beam ,
S34631,VO008,IFC to Tender Drawings ,SI-000167
S34631,VO009,Foundation Waterstop,SI-000305
S34975,VO001,Contract Variances,
22196,VO077,Membrane Repairs to Mechanical Plant Supports,
S34539,VO009,Small water ingress L1 Podium,SI 777
S34772,VO006,"Nuradeck C to Joinery
",Email23/6
S34578,VO005,Air Freight,
S34832,VO001,Newtons Waterbar,
R1213,VO001,"Credit to Allow for Access Scaffolf, including erection, dismantling and 9 weeks rental",Email24/6
23159,VO090,Level 02 line marking remediation works ,Email/2406
R1213,VO002,Swings Stage,Email 24/0
23159,VO091,"Ground Mez, Line Marking - Credit",COR-000029
23159,VO092,A L2 Maintenance platform 3.02 WPM to timber nibs,SI-005860
S34631,VO010,Detailing to Penetration (upto 200mm dia),
23159,VO093,Waterproofing to Hydrant pipe inside L2 east corridoor,SI 6417
S34910,VO002,Weekly Rental Charges 02.06.26 to 06.07.26,
S34910,VO003,Credit for items not completed,
S34910,VO004,Engineer's Inspection,
S34910,VO005,P&G Adjustment,
S34754,VO025,Carrington Building C90 Rehab Plus  - Roof Leak Investigation,WOT0259798
S34545,VO026,Additional Waterproofing to Zone 3 SVR Room,
R937,VO003,Sika Grout 212 to Roof CHS Columns (70N),SI 792
S34539,VO010,Sika Grout 212 to Roof CHS Columns (70 N),SI-792
S34482,VO029,Canopy Pipe Penetration,SI-001311
23159,VO094,"Decarb, Sita & Grid 39 Works outside normal working hours",SI-006845
S34482,VO030,Supply and lnstall Powdercoated Flashing,SI-001338
S34482,VO031,Supply and Install welded tray flashing,SI-001330
23245,VO037,Application of flashing barrier tape,
S34539,VO011,Roof overflows,SI 799
S34543,VO025,"ACO drain, L4 base of ramp to L5",SI-4460 
R937,VO004,Lift overrun Grinding,SI 796
S34539,VO012,Lift overrun,SI 796
S34543,VO026,Final Account Agreement,
S35013,VO002,Switchroom Penetrations,SI-000059
S34482,VO032,Build a nib using Sikadur 31CF,SI-001252
23245,VO038,Grinding concrete Nib ,SI-003486
R765,VO003,Baseplate Grouting,CAN001
S34966,VO001,Alternative Waterbar to Internal Slab Cut Outs ,
S34966,VO002,SIKA S2 Sealant to Internal Footing Slab Outs ,
S34966,VO003,Additional Sikaproof A to Internal Footings ,
S34870,VO001,Offsite Storage for PIR Insulation,SI-002237
S34466,VO002,Sikadur 42 Pilecap Repairs ,
S34947,VO001,Pile Demolition and Repairs ,NTSC 020
S34183,VO036,Stairs 1 & 2 - Substrate,
S34975,VO002,Precast Panel Joint Variance,
23159,VO095,Chevaline Dexx Coating Works (as per agreed measure and value),SI-002364
S34673,VO001,Gridline E Horizontal Detail Works,SI-14
23159,VO096,"Credits for VO021, 28, 50 & 51. Reflected now under VO095",Email 8may
S34543,VO027,"Garage Pipeworks relocation works, SVR room reinstate matacryl system",SI 6426
23159,VO097,"WP1 - SP5 Remedials to floor
",SI 6902
23159,VO098,Repairs to open space damaged areas,SI 6900
S35010,VO001,A01 Tile resurfacing - stair nosing,Email21/07
R1315,VO001,Additional  Crack repairs above the original quantities quoted,email22/07
S34631,VO011,HV Room Penetrations,
S34631,VO012,Volclay & Waterbar Reworks,SI-001466
23159,VO099,WP1 SP5 Waterproofing Weekend work,SI006846
23159,VO100,Reversal of VO091,COR-000029
S34466,VO003,Waterbar replacement to pile caps ,
S34466,VO004,Relief Hose Repairs - Lift Pit / Zone 003 ,
S34539,VO013,Roof level adjustment for PIR,SI-778
S34482,VO033,Pipe Penetration Through the Asphalt,SI-001291
S34482,VO034,Carpark Entry Cladding and Nib Protection,SI-001332
S34832,VO002,Detailing to wall ties through membrane Gridline 1,
S34631,VO013,"Penetrations ( upto 100 mm Dia, as per Contract Rate)",
S34631,VO014,RX Waterstop to the Perimeter Slab & Capping Beam as per waterproofing details (to be treated as variation  as noted in the contract and as per approved rate),
23159,VO101,Capping of Existing Overflows on VVa Parapet,SI-006932
21148,VO120,Crack repair in R60,
R1213,VO003,Additioanl Concrete Repairs,CI 002
S34966,VO004,Additional Mobilisations & As Built Footings  Changes ,
S34966,VO005,Downtime Waiting for Work Area ,
S34466,VO005,Additional Geotextile to Lift Pit,
23159,VO102,Weekend Works - 25/7 & 26/7/26,
S34889,VO001,Coating to Lift Pit & Thresholds ,
R1059,VO004,Main lab floor Repairs,SI 9
S34539,VO014,Wet Vac Roof,SI 838
S34631,VO015,Bentonite granules to liner wall remedial ,SI-001508
S34631,VO016,Replacement of Voltex underfloor Gridline 3-6,SI-001509
S35010,VO002,Glass Balustrade,
S34754,VO026,Auckland City Hospital - AO01 Support Building L5,WOT0272881
S34482,VO035,L1 Carpark Fire Door Waterproofing Remedial,SI 1437
S34482,VO036,Sill detail of door at L1 Carpark -  Curring of Asphalt,SI 1438
S34578,VO006,Additional Sealant Application,
R878,VO011,Stage 4 - Building structure repairs,CI 138
R878,VO012,External Wall Repair Infill,CI 123
23159,VO103,AC Unit Builders work Detail to PC11 Bridge Roof,SI-006983
S34870,VO002,Temp waterproofing to level 5 and level 4,SI-002465
S34183,VO037,Flashing and cetcoat - Link 1 (RFI-1000),SI-2569
S34183,VO038,Link 2 - Promat cladding,SI-2572
S34183,VO039,Final Account Settlement,
S34577,VO001,Install waterbar for transformer room,SI-532
S34631,VO017,Additional for Swelltite in lieu of Voltex- HV Room,SI-001593
S34182,VO011,Chevaline dexx to plinths ,SI-006697
R1315,VO002,Final Crack Map - Last 20%,SI 86
S34673,VO002,Panel Joints Basement to GF Panel - Illmod600,SI-19
23159,VO104,Re waterproof CLT where screws required removing for other trade remediation,SI-006997
R1138,VO001,PST Crack and Small Leak,Email7/8
S34065,VO007,Rectification of Incorrect Pipe Installation at Ground Floor Slab 14 ,SI-006739
S34466,VO006,PC Panel Pipe Support Membrane Detailing ,SI-000179
R1159,VO004,"KF1 Stage 2, Stair 3 area - Exposed Reinforcing and Concrete Repairs",AKL5060287
S34065,VO008,Temporary Waterproofing Works,SI-006791
S34482,VO037,Supply 2 rolls of Double stick tape and install on B1B canopy,SI-001483
S34631,VO018,Corewall Waterstop,VPR-000016
S34631,VO019,Zone B GL SC Volclay Rectification,SI-001643
S35110,VO001,Supply and install Nuraglaze coating,Email14/08
R1356,VO001,Shot blast walkway infill,Email14/08
S34539,VO015,Custom DP Transition (Membrane Remedial),SI 869
S34545,VO027,Coverboard protection to zone 1,SI-002556
R1241,VO001,Site Induction and Visit - 5th August 2026,19/08/2026
S34956,VO001,Credit - Deletion of Membrane,SI-105
S34956,VO002,Change of parapet membrane along gridline A,SI-87
R1367,VO001,Corroded Reinforcement Repairs within the Plenum Chamber,Email20/08
S34947,VO002,Pile Demolition and Repairs,NTSC 020
R878,VO013,Louver Opening Preperation,SI 122
S34577,VO003,Intu-mastic seal around orbi bolt washer holes,SI-582
S34545,VO028,Zone 5 Level 0 - Preprufe Repairs,SI-002509
S34477,VO005,Building G Membrane Roofing Scope (Changed to Bitumen Membrane – Refer VO006),Email/1408
S34477,VO006,Cost uplift due to Double Layer Torch-on Membrane ,Email/2408
S34182,VO012,Remedial work to WP1 membrane ,SI-007065
23159,VO105,WP1 - PC11 Bridge Roof Existing Height Safety Access Rail.,SI-007068
S34466,VO007,Facade Works,
S34482,VO038,B1 & B2 Canopy ,SI-000708
S34854,VO001,Extra Mobilisation for Staged Sikalastic 152 work,Email14/08
S34482,VO039,Chain wire fences + doors for B1a level 1 carpark (AAN-162),SI-001524
S34482,VO040,Waterproofing of door rebate,SI-001447
S34466,VO008,Extra Over PC SUM - Pipe Penetrations through Preprufe 300R ,
S34466,VO009,Extra Over PC - Reinforcing Starters to Grid 7 Wall ,
S34466,VO010,Membrane Damage Repairs Zone 002/Zone 003 Raft Slab ,
S34631,VO020,Additional run of waterstop to the tanked areas at the wall construction joint,SI-001521
S34870,VO003,Waterproof concrete that has been chipped out for façade GL—7 J-J+,SI-002658
23159,VO106,Additional membrane works to upstands only,SI-006668
23159,VO107,Waterproofing to Hydrant pipe inside L2 east corridor,SI-006417
23159,VO108,Seismic detail to L2 Grid 35-VVa,COR-000278
S35013,VO003,Damaged Membrane Repairs – Building A & B,SI-000079
S35013,VO004,NIB Membrane Reinstatement,SI-000043
23159,VO109,Sp5 Level 2 Services Plinth waterproofing,SI-007085
S34577,VO004,Replacement Horizontal P Seal - Grid J,SI-591
23159,VO110,"Scope Reduction Credit -  Flood testing to remaining gutters

",CAN414
22196,VO078,Additional Outlet,
S35110,VO002,Supply of outlets/overflows,Email/2608
S34182,VO013,T13-12 Landside Tanking Work,SI-005864
S9000,VO002,Dead Time - below contract hours,
R169,VO004,Eden Apartments 13A - Sikadur 52 Injection,Email31/08
S34539,VO016,Nuralite Gooseneck,SI 887
22196,VO079,Torch on detail around cable peno,SI-007310
S34545,VO029,Zone 5 Additional termination detailing,SI-002768
S34578,VO007,Supply and Install Inseal Tape 3109,ATS No. 48
S34539,VO017,Cricket Roof Buildup,SI 893
S35013,VO005,Flue Support Waterproofing - Option 2,
S35110,VO003,Additional Visit Due to Staging of Works – Beach House Top Flat Roof,
S35110,VO004,Additional Membrane Detailing to Valleys and Chimneys ,
R1367,VO002,Wall Coating,PO 62827
R1148,VO001,"Crack Survey, Classification, Reporting and Repair Scope",2669
S34482,VO041,Supply only 4ltr Equus Ferroclean ,SI-001540
S34182,VO014,Cooling frame waterproof detail ,SI-007110
S34822,VO001,Sikadur UA Concrete Fix to Precast Joints,SI-899
S34182,VO015,Coating works to steel on northern nibs ,SI-007333
S35234,VO001,Crack Repairs,Email03/09
23159,VO111,Review of Symonite fixing proposal (Quintus Slabber email 04.08.26) ARCH - CAN 1186,SI-007120
S34482,VO042,Laneway R/S Door Opening Aquafin 2KM Repairs ,SI-001563
S34754,VO027,Carrington Campus - C25 Buchanan Clinic Leak Investigation,WOT0297505
S34754,VO028,Auckland City Hospital -  A08 Oncology Investigation of leaks,WOT0296899
S34754,VO029,"Carrington C25 - Buchanan Clinic Room 4, Leak Investigation",WOT0298747
S34631,VO021,Volclay Removal and Repair Zone B,SI-001849
R1315,VO003,Crack Cores,SI 124
S34545,VO030,Adjust termination to new level – Zone 2 stairs,SI-002879
R1364,VO001,Grouting works /  Steel cutting,PO520-1300
S34631,VO022,Removal of Newtons on Gridline E,SI-001856
R1159,VO005,KF1 - Render to base of shearwall,AKL5061209
R1159,VO006,Grout Install,AKL5061225
S34477,VO007,Membrane Roofing Penetration Re Detailing,
S34477,VO008,Membrane Roofing – Central Roof Additional Diverters,
R1356,VO002,"ADHB Canopy Repairs:
AO8 Oncology",PO S06021
R1346,VO001,Spiral Top Cover Repair Tower 1B 2B ,NTSC 033
S34947,VO003,Pile Demolition,NTC-020
S34947,VO004,Penetrations,
R1138,VO002,"Scope of works wiith Rate only
Main tank - PST3  &4",Email1809
S34947,VO005,Pile Demolition: Spiral Top Cover Repair Tower 1B 2B,NTSC 033
R1148,VO002,Crack Repairs 1m down  from top of column,2669112824
S35190,VO001,Precast wall sealant,SI-000132
S35234,VO002,Screeding to Channel Drains,
S35234,VO003,Metal Outlets ,
S35013,VO006,Waterproofing Membrane to Door Bunds (A2-D2),SI 136
S34183,VO040,Seal plantroom cable,SI-2645
S34539,VO018,Temp Waterproofing Risers,SI 934
23159,VO112,WP1 SP4 L2 remedials,SI-007162
S35000,VO001,Locating and drilling injection holes,157785
S34466,VO012,Waterbar Replacement ,SI-000204
S34631,VO023,Standing Time 24/09 and 25/09 ,SI-001964
S34577,VO005,Seismic and precast jointing ,
S35013,VO007,Credit - Deleted Scope,
R1148,VO003,Concrete Perimeter walls,CAN ST- 01
R1343,VO001,"Rosedale WWTP RC1 Works
(admin@seipp.co.nz)",PO 63386
S35253,VO001,Screed,
S35253,VO002,Substrate Repairs,
S35253,VO003,Deck Waterproofing,
R1138,VO003,PST 3 & 4 Stud Removal,Email28/9
S35019,VO002,Pipe Penetration Detailing,
S35019,VO003,Control Joint Detailing,
S35019,VO004,Aquadrain Protection,
R1350,VO001,Design Work,49133775
S34870,VO004,Additional PIR Insulation costs as per latest design,
S34870,VO005,Additional Waterproofing - Zone 2 Grid 7,
S34870,VO006,Waterproofing to Zone 2 Level 4,
S34631,VO024,Volclay Rectification,SI 2009
R1159,VO007,KF2 Concrete Remedials,AKL 506166
S34870,VO007,RFI 11 - Warm roof system to Zone 2 Level 2 Risers ,VARPS-0009
S34870,VO008,Chevaline Dexx to All Risers (Design Change),SI - 3069
S34870,V001,Zone 1: Level 4,
S34870,V002,Zone 1: Level 5,
S34870,V003,Zone 2: Level 4,
S34870,V004,Zone 2: Level 5,
S34870,V005,Zone 3: Level 3,
S34870,V006,Zone 5: Outbuilding,
S34870,V007,Zone 5: Transformer Roof,
S34870,V008,All Chevaline Dexx Works,
S34870,V009,Dewatering,
S34870,V010,PIR Material Movement - For other trades work,
S34870,V011,PIR Material - Secure & Packaging,
S34631,VO025,B230 - Zone B GL/11 Additional Waterbar,SI 2032
S35258,VO001,Atrium Gap Sealing,Email6/10
S35258,VO002,L4 Roof gutter ledge wall waterproofing,Email6/10
S34870,VO009,Bunding Works,Email 7/10
S34482,VO043,Laneway R/S Doors Shopfront Aquafin Remedials,SI 1649
S34688,VO001,Testing of Completed Post Detailing,Email7/10
S34323,VO010,2026 EOY Christmas costs,
S34323,VO011,2026 Christmas Hampers,
S34984,VO001,Waterproofing Tanking - Cess Pitt,Email9/10
R1155,VO001,18-20 Tauraru Tce,SO6243
R1367,VO003,Bio Bed 2 & 4 Jointing,PO 63779
S34577,VO006,Remediate Damaged P-seal Gridline 3,SI 678
S34577,VO007,Cutting slab edge to fit Ryanspan,SI 745
R1367,VO004,Odour Bed Block Crack Injection,Email13/10
S34772,VO007,Ardex membrane repair,Email14/10
R1159,VO008,Concrete Repairs to slab face on stage 3,AKL5062070
R1356,VO003,ADHB Canopies A & B Tile Removal,S06021
S34846,VO001,Patch Repair Lift Piles,SI 021
R1159,VO009,Concrete Footing remedials for block veneer base,AKL 506192
R1149,VO001,Boundary Wall Remediation,Email16/10
S34466,VO013,Patch existing sleeve,SI-000232
S34578,VO008,Adjustment to Air Freight Cost ,
23159,VO113,Waterproofing coating around new plinth and drain pipe,COR-002719
R444,VO037,Final Account,Email20/10
R1138,VO004,Additional Sikagard 7000 PST 3 & 4,Email20/10
S34477,VO009," Additional screed to 1x balcony and 2x Juliet balconies, Level 1 ",VO-000221
S34947,VO006,Pile Inspection - Piles 5-8,
S34688,VO002,Downtime Staff Hours,
S35013,VO008,Secure Duct Waterproofing & EFVM,SI-000091
R1148,VO004,Column and top of wall crack injection (final updated),CAN ST19
S35309,VO001,Investigation works,
S35309,VO002,Removal and Reinstatement of Bottom Weatherboards,
S35309,VO003,Install tiles on pedestals,
S35309,VO004,Upgrade Drainage,
S34539,VO019,Roof Updates,SI-858
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
    tools_json = json.dumps([{"name": t["name"], "alias": t.get("alias", "")} for t in HAND_TOOLS])
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

HAND TOOLS (match by name or alias, allow for misspellings and abbreviations):
{tools_json}

Extract everything mentioned:
1. Stock products - match against PRODUCTS list using description, code, or alias. Each product gets its own entry with quantity.
2. Tools - match any tools mentioned against the HAND TOOLS list using name or alias. A "blade" could match "Hack saw" or a cutting tool - use best judgement.
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
- If a word matches the alias of MORE THAN ONE product (e.g. "swelltite" matches both a bar and a roll, or "sika ua"/"sikadur ua" matches both the 4L and 8L Sikadur UA), set ambiguous: true and include ALL matching products in matches so the user can choose. Never silently pick one size/variant over another when the transcript doesn't specify which.
- Only match a product when the transcript genuinely overlaps its description or alias text. Sharing just a supplier name (e.g. "sika") is not enough on its own — do not force a match to an unrelated product just because it's the same supplier.
- NEVER invent, guess, abbreviate, or construct a "code" that isn't copied verbatim from an entry in the PRODUCTS list above. Every object in "matches" must correspond to a real PRODUCTS entry with that exact code. If you can't find an exact PRODUCTS entry for something, do not put it in matches — check whether it's actually in HAND TOOLS instead (some consumables like drill bits are listed there, not in PRODUCTS), and if it's in neither list, leave it out entirely rather than fabricating an entry.
- If no quantity stated for a product, set quantity to null and add "quantity" to missing
- Put null and add to missing[] for job or worker_name if not in transcript
- Only include tools that are a clear match (by name or alias) to the HAND TOOLS list. Don't be shy about matching a long or branded tool name just because the transcript only loosely resembles it — if the meaning clearly matches, include it and copy the "name" field exactly as written in the list. Just never invent a tool name that isn't in the list at all.
- For tools, if a quantity is stated (e.g. "2 hammers") set quantity accordingly, otherwise default to 1
- If ONLY tools are mentioned (no stock products), return matches: [] and do NOT add "product" or "quantity" to missing[]
"""}
        ]
    )
    data = json.loads(response.choices[0].message.content.strip())

    # Hard guardrail: never trust the model's word for it. A "match" is only kept if
    # its code is a real PRODUCTS entry — and even then every field except quantity
    # is overwritten with the real record, because the model has been seen pairing a
    # real code with a totally unrelated description (e.g. code RF170, a NURA
    # sealant, mislabelled as vacuum bags). Same idea for tools: name must be a real
    # HAND_TOOLS entry. Prompt instructions alone don't prevent this kind of error,
    # so it's enforced here instead (see RAMVACBAGS/RAMVBG/RF170 incidents).
    products_by_code = {}
    for p in _products:
        products_by_code.setdefault(p["code"], []).append(p)
    valid_tool_names = {t["name"] for t in HAND_TOOLS}

    clean_matches = []
    for m in data.get("matches", []):
        candidates = products_by_code.get(m.get("code"))
        if not candidates:
            continue
        real = next((c for c in candidates if c["description"].lower() == str(m.get("description", "")).lower()), candidates[0])
        clean_matches.append({**real, "quantity": m.get("quantity")})
    data["matches"] = clean_matches
    data["tools"] = [t for t in data.get("tools", []) if t.get("name") in valid_tool_names]
    if len(data["matches"]) < 2:
        data["ambiguous"] = False

    return data

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
