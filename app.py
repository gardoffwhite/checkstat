from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import requests
from bs4 import BeautifulSoup

# กำหนด templates folder
templates = Jinja2Templates(directory="templates")

app = FastAPI()

# URL สำหรับ logout, login และหน้า charedit.php
logout_url = "http://nage-warzone.com/admin/?logout=session_id()"
login_url = "http://nage-warzone.com/admin/index.php"
charedit_url = "http://nage-warzone.com/admin/charedit.php"

# ข้อมูลฟอร์มล็อกอิน
login_payload = {
    "username": "admin",
    "password": "3770",
    "submit": "Submit"
}

# สร้าง session
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

# ฟังก์ชันล็อกอินและดึงข้อมูล
def get_character_data(charname=""):
    try:
        session.post(login_url, data=login_payload, headers=headers, timeout=20)
        char_resp = session.post(
            charedit_url,
            data={"charname": charname, "searchname": "Submit"},
            headers=headers, timeout=20
        )
        soup = BeautifulSoup(char_resp.text, "html.parser")
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

    placeholders = soup.find_all('input', {'placeholder': True})
    data = {}
    for placeholder in placeholders:
        field_name = placeholder.get('name')
        placeholder_value = placeholder.get('placeholder')
        data[field_name] = int(placeholder_value) if placeholder_value.isdigit() else placeholder_value

    # คำนวณ lvpoint
    lvpoint = int(data.get("lvpoint", 0))

    # กระจาย point
    stats_str_dex = ['str', 'dex']
    existing_str_dex = [data.get("str", 0), data.get("dex", 0)]
    distributed_str_dex = distribute_lvpoint(lvpoint, stats_str_dex, existing_str_dex)

    stats_esp_spt = ['esp', 'spt']
    existing_esp_spt = [data.get("esp", 0), data.get("spt", 0)]
    distributed_esp_spt = distribute_lvpoint(lvpoint, stats_esp_spt, existing_esp_spt)

    data.update(distributed_str_dex)
    data.update(distributed_esp_spt)

    return data

# ฟังก์ชันกระจาย lvpoint
def distribute_lvpoint(lvpoint, stats_group, existing_values):
    total_existing = sum(existing_values)
    total_points = lvpoint + total_existing
    points_per_stat = total_points // len(stats_group)
    remainder = total_points % len(stats_group)

    distributed_points = {stat: points_per_stat for stat in stats_group}
    for i, stat in enumerate(stats_group):
        if i < remainder:
            distributed_points[stat] += 1
    return distributed_points

# หน้าเว็บหลัก
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, charname: str = ""):
    char_data = None

    if charname:
        char_data = get_character_data(charname)

    return templates.TemplateResponse("index.html", {"request": request, "char_data": char_data, "charname": charname})
