
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import io, math, json, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "gw_express.db"

app = FastAPI(title="GW Express Roteirizador")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")

ORIGIN_LAT = -10.911148
ORIGIN_LON = -37.059038

PALETTE = ["#e6194B","#4363d8","#3cb44b","#f58231","#911eb4","#46f0f0","#f032e6","#bcf60c","#008080","#ff7f50","#2e8b57","#8b008b"]

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        routes TEXT,
        summary TEXT,
        invalid TEXT,
        config TEXT
    )
    """)
    con.commit()
    con.close()

init_db()

def fnum(v):
    try:
        if v is None or v == "":
            return None
        return float(str(v).replace(",", "."))
    except:
        return None

def hav(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def clean(v):
    s = str(v or "").strip().replace("SPR", "").replace("spr", "").strip()
    return s or "GERAL"

def nearest(rows, lat_col, lon_col):
    rem = rows[:]
    out = []
    clat, clon = ORIGIN_LAT, ORIGIN_LON
    while rem:
        best, bestd = 0, 10**9
        for i, r in enumerate(rem):
            lat, lon = fnum(r.get(lat_col)), fnum(r.get(lon_col))
            if lat is None or lon is None:
                d = 10**9
            else:
                d = hav(clat, clon, lat, lon)
            if d < bestd:
                best, bestd = i, d
        p = rem.pop(best)
        out.append(p)
        lat, lon = fnum(p.get(lat_col)), fnum(p.get(lon_col))
        if lat is not None and lon is not None:
            clat, clon = lat, lon
    return out

def route_km(rows, lat_col, lon_col):
    km = 0
    clat, clon = ORIGIN_LAT, ORIGIN_LON
    for r in rows:
        lat, lon = fnum(r.get(lat_col)), fnum(r.get(lon_col))
        if lat is None or lon is None:
            continue
        km += hav(clat, clon, lat, lon)
        clat, clon = lat, lon
    if rows:
        km += hav(clat, clon, ORIGIN_LAT, ORIGIN_LON)
    return km

def split_routes(rows, cap_max, km_max, lat_col, lon_col):
    rows = nearest(rows, lat_col, lon_col)
    groups, cur = [], []
    for r in rows:
        test = nearest(cur + [r], lat_col, lon_col)
        if cur and (len(test) > cap_max or route_km(test, lat_col, lon_col) > km_max):
            groups.append(nearest(cur, lat_col, lon_col))
            cur = [r]
        else:
            cur = test
    if cur:
        groups.append(nearest(cur, lat_col, lon_col))
    return groups

def maps_link(rows, lat_col, lon_col):
    coords = [f"{ORIGIN_LAT},{ORIGIN_LON}"]
    for r in rows:
        lat, lon = fnum(r.get(lat_col)), fnum(r.get(lon_col))
        if lat is not None and lon is not None:
            coords.append(f"{lat},{lon}")
    return "https://www.google.com/maps/dir/" + "/".join(coords)

def process(rows, cfg):
    lat_col = cfg["lat_col"]
    lon_col = cfg["lon_col"]
    spr_col = cfg.get("spr_col") or ""
    bairro_col = cfg.get("bairro_col") or ""
    cap_max = int(cfg.get("cap_max", 95))
    cap_min = int(cfg.get("cap_min", 70))
    km_max = float(cfg.get("km_max", 35))

    valid = []
    invalid = []

    for idx, r in enumerate(rows, 1):
        r = dict(r)
        r["ID_ROTA"] = r.get("ID_ROTA") or idx
        lat, lon = fnum(r.get(lat_col)), fnum(r.get(lon_col))
        if lat is None or lon is None:
            r["STATUS"] = "COORDENADA INVALIDA"
            invalid.append(r)
            continue
        r["SPR_PLANEJADO"] = clean(r.get(spr_col)) if spr_col else "GERAL"
        r["BAIRRO_CLUSTER"] = str(r.get(bairro_col, "")).strip().upper() if bairro_col else ""
        valid.append(r)

    by_spr = {}
    for r in valid:
        by_spr.setdefault(r["SPR_PLANEJADO"], []).append(r)

    routes = []
    summary = []
    color_idx = 0

    for spr, rs in sorted(by_spr.items()):
        groups = split_routes(rs, cap_max, km_max, lat_col, lon_col)

        for i, g in enumerate(groups, 1):
            g = nearest(g, lat_col, lon_col)
            km = route_km(g, lat_col, lon_col)
            ok = len(g) >= cap_min and len(g) <= cap_max and km <= km_max
            route_name = f"{spr}.{i}" if ok else f"NAO_VIAVEL_{spr}.{i}"
            color = PALETTE[color_idx % len(PALETTE)] if ok else "#ff0000"
            if ok:
                color_idx += 1

            clat, clon = ORIGIN_LAT, ORIGIN_LON
            km_ac = 0
            for seq, r in enumerate(g, 1):
                lat, lon = fnum(r.get(lat_col)), fnum(r.get(lon_col))
                trecho = hav(clat, clon, lat, lon)
                km_ac += trecho
                out = dict(r)
                out.update({
                    "SPR_FINAL": route_name,
                    "SEQ_SPR": seq,
                    "COR_SPR": color,
                    "QTD_PEDIDOS_ROTA": len(g),
                    "KM_TOTAL_ROTA_ESTIMADO": round(km, 2),
                    "KM_ACUMULADO_ESTIMADO": round(km_ac, 2),
                    "CAPACIDADE_MINIMA": cap_min,
                    "CAPACIDADE_MAXIMA": cap_max,
                    "KM_MAXIMO": km_max,
                    "STATUS": "VALIDO PARA ENTREGA" if ok else "NAO VIAVEL",
                    "LINK_PEDIDO_MAPS": f"https://www.google.com/maps?q={lat},{lon}",
                    "LINK_ROTA_MAPS": maps_link(g, lat_col, lon_col)
                })
                if ok:
                    routes.append(out)
                else:
                    invalid.append(out)
                clat, clon = lat, lon

            if ok:
                summary.append({
                    "SPR": route_name,
                    "SPR_PLANEJADO": spr,
                    "QTD_PEDIDOS": len(g),
                    "KM_ROTA_ESTIMADO": round(km, 2),
                    "CAPACIDADE_MINIMA": cap_min,
                    "CAPACIDADE_MAXIMA": cap_max,
                    "KM_MAXIMO": km_max,
                    "OCUPACAO": f"{round((len(g)/cap_max)*100)}%",
                    "STATUS": "VALIDO PARA ENTREGA",
                    "COR": color,
                    "LINK_GOOGLE_MAPS": maps_link(g, lat_col, lon_col)
                })

    return routes, summary, invalid

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    lat_col: str = Form(...),
    lon_col: str = Form(...),
    spr_col: str = Form(""),
    bairro_col: str = Form(""),
    cap_max: int = Form(95),
    cap_min: int = Form(70),
    km_max: float = Form(35)
):
    data = await file.read()
    if file.filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(data))
    else:
        df = pd.read_excel(io.BytesIO(data))
    df = df.fillna("")
    rows = df.to_dict(orient="records")
    cfg = {
        "lat_col": lat_col, "lon_col": lon_col, "spr_col": spr_col,
        "bairro_col": bairro_col, "cap_max": cap_max, "cap_min": cap_min, "km_max": km_max
    }
    routes, summary, invalid = process(rows, cfg)
    con = sqlite3.connect(DB_PATH)
    cur = con.execute(
        "INSERT INTO jobs(name,routes,summary,invalid,config) VALUES(?,?,?,?,?)",
        (file.filename, json.dumps(routes, ensure_ascii=False), json.dumps(summary, ensure_ascii=False),
         json.dumps(invalid, ensure_ascii=False), json.dumps(cfg, ensure_ascii=False))
    )
    job_id = cur.lastrowid
    con.commit()
    con.close()
    return {"job_id": job_id, "routes": routes, "summary": summary, "invalid": invalid}

@app.get("/api/job/{job_id}")
def job(job_id: int):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    con.close()
    if not row:
        return JSONResponse({"error": "não encontrado"}, status_code=404)
    return {
        "id": row["id"],
        "routes": json.loads(row["routes"]),
        "summary": json.loads(row["summary"]),
        "invalid": json.loads(row["invalid"]),
        "config": json.loads(row["config"])
    }

@app.get("/api/job/{job_id}/export.csv")
def export_csv(job_id: int):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT routes FROM jobs WHERE id=?", (job_id,)).fetchone()
    con.close()
    data = json.loads(row["routes"]) if row else []
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, sep=";", index=False)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=gw_express_rotas.csv"})
