from fastapi import FastAPI, Form
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
        session.post(login_url, data=login_payload, headers=headers, timeout=20)

        # Convert charname to TIS-620 encoding for compatibility
        charname_encoded = charname.encode("tis-620")
        charname_fixed = charname_encoded.decode("tis-620")

        char_resp = session.post(
            charedit_url,
            data={"charname": charname_fixed, "searchname": "Submit"},
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

    lvpoint = int(data.get("lvpoint", 0))

    # Distribute stats (leave remainder 1 point always)
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
        return {stat: existing for stat, existing in zip(stats_group, existing_values)}

    lvpoint -= 1  # keep 1 point as remainder
    total_existing = sum(existing_values)
    total_points = lvpoint + total_existing
    points_per_stat = total_points // len(stats_group)

    distributed_points = {stat: points_per_stat for stat in stats_group}
    return distributed_points

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
