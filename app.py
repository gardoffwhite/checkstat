from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import requests
from bs4 import BeautifulSoup

app = FastAPI()
templates = Jinja2Templates(directory="templates")

login_url = "http://nage-warzone.com/admin/index.php"
charedit_url = "http://nage-warzone.com/admin/charedit.php"

login_payload = {
    "username": "admin",
    "password": "3770",
    "submit": "Submit"
}

session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_character_data(charname=""):
    try:
        # login ก่อน
        session.post(login_url, data=login_payload, headers=headers, timeout=20)

        # เตรียม data ให้ใช้ TIS-620
        post_data = {
            "charname": charname.encode('tis-620', errors='ignore').decode('tis-620', errors='ignore'),
            "searchname": "Submit"
        }

        # แปลงข้อมูลก่อนส่ง
        response = session.post(
            charedit_url,
            data=post_data,
            headers=headers,
            timeout=20
        )

        # แปลงเนื้อหา response เป็น TIS-620
        response.encoding = 'tis-620'
        soup = BeautifulSoup(response.text, "html.parser")

    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

    placeholders = soup.find_all('input', {'placeholder': True})
    data = {}
    for placeholder in placeholders:
        field_name = placeholder.get('name')
        placeholder_value = placeholder.get('placeholder')
        data[field_name] = int(placeholder_value) if placeholder_value.isdigit() else placeholder_value

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

def distribute_lvpoint(lvpoint, stats_group, existing_values):
    if lvpoint <= 1:
        return {stat: value for stat, value in zip(stats_group, existing_values)}

    usable_points = lvpoint - 1  # เหลือเศษ 1 ไว้
    total_existing = sum(existing_values)
    total_points = usable_points + total_existing

    points_per_stat = total_points // len(stats_group)

    distributed_points = {stat: points_per_stat for stat in stats_group}
    return distributed_points

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, charname: str = ""):
    char_data = None

    if charname.strip() != "":
        char_data = get_character_data(charname)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "char_data": char_data,
        "charname": charname
    })
