from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import requests
from bs4 import BeautifulSoup

# Templates
templates = Jinja2Templates(directory="templates")
app = FastAPI()

# URL
logout_url = "http://nage-warzone.com/admin/?logout=session_id()"
login_url = "http://nage-warzone.com/admin/index.php"
charedit_url = "http://nage-warzone.com/admin/charedit.php"

# Login payload
login_payload = {
    "username": "admin",
    "password": "3770",
    "submit": "Submit"
}

# Session
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ฟังก์ชันดึงข้อมูลตัวละคร
def get_character_data(charname=""):
    try:
        # เข้าระบบก่อน
        session.post(login_url, data=login_payload, headers=headers, timeout=20)

        # Encode เป็น TIS-620 ถ้าเป็นภาษาไทย
        try:
            encoded_name = charname.encode('tis-620')
            charname = encoded_name.decode('tis-620')  # decode กลับเพื่อส่งให้ requests
        except UnicodeEncodeError:
            pass  # ถ้าไม่ใช่ไทยก็ข้าม

        char_resp = session.post(
            charedit_url,
            data={"charname": charname, "searchname": "Submit"},
            headers=headers, timeout=20
        )
        soup = BeautifulSoup(char_resp.text, "html.parser")

    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

    # ดึงข้อมูลจาก input field
    placeholders = soup.find_all('input', {'placeholder': True})
    data = {}
    for placeholder in placeholders:
        field_name = placeholder.get('name')
        placeholder_value = placeholder.get('placeholder')
        data[field_name] = int(placeholder_value) if placeholder_value.isdigit() else placeholder_value

    # คำนวณ lvpoint แบบเหลือเศษ 1 ไว้เสมอ
    lvpoint = int(data.get("lvpoint", 0))

    stats_str_dex = ['str', 'dex']
    existing_str_dex = [data.get("str", 0), data.get("dex", 0)]
    distributed_str_dex = distribute_lvpoint(lvpoint, stats_str_dex, existing_str_dex)

    stats_esp_spt = ['esp', 'spt']
    existing_esp_spt = [data.get("esp", 0), data.get("spt", 0)]
    distributed_esp_spt = distribute_lvpoint(lvpoint, stats_esp_spt, existing_esp_spt)

    data.update(distributed_str_dex)
    data.update(distributed_esp_spt)

    return data

# แบ่ง lvpoint แบบเหลือเศษ 1 ไว้เสมอ
def distribute_lvpoint(lvpoint, stats_group, existing_values):
    total_existing = sum(existing_values)
    total_points = lvpoint + total_existing

    if total_points > 1:
        total_points -= 1  # กันเศษ 1 ไว้เสมอ

    points_per_stat = total_points // len(stats_group)

    distributed_points = {stat: points_per_stat for stat in stats_group}

    return distributed_points

# หน้าเว็บหลัก
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, charname: str = ""):
    char_data = None

    if charname:
        char_data = get_character_data(charname)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "char_data": char_data,
        "charname": charname
    })
