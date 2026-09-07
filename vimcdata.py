from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
import requests
import os
# Lấy thông tin từ GitHub Actions
VBS_USERNAME = os.environ.get("VBS_USERNAME")
VBS_PASSWORD = os.environ.get("VBS_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Hàm gửi tin nhắn qua Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML" # Cho phép dùng thẻ <b> để in đậm
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Lỗi gửi Telegram: {response.text}")
    except Exception as e:
        print(f"Lỗi kết nối Telegram: {e}")

# Hàm cào dữ liệu HTML bằng Playwright
def get_schedule_html():
    with sync_playwright() as p:
        # headless=True để trình duyệt chạy ngầm (không bật cửa sổ lên)
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()

        print("Đang truy cập trang đăng nhập...")
        page.goto("https://vbs.vimc.co/")

        page.wait_for_selector("#username") 
        page.fill("#username", VBS_USERNAME)
        page.wait_for_selector("#password")
        page.fill("#password", VBS_PASSWORD)
        page.click("button[type='submit']") 

        page.wait_for_load_state("networkidle")
        
        print("Đang tải dữ liệu lịch...")
        page.goto("https://vbs.vimc.co/utility/company-work-schedule")
        
        # Đợi tiêu đề xuất hiện
        page.wait_for_selector("text='Thành viên tham gia'", timeout=30000) 
        time.sleep(3) 

        html_content = page.content()
        browser.close()
        
        return html_content

if __name__ == "__main__":    
    html_data = get_schedule_html()
    soup = BeautifulSoup(html_data, "html.parser")
    
    # Ép thời gian sang múi giờ Việt Nam (UTC+7)
    vn_timezone = timezone(timedelta(hours=7))
    now_vn = datetime.now(vn_timezone)
    
    today = now_vn
    tomorrow = today + timedelta(days=1)
    
    str_today = today.strftime("%d/%m")
    str_tomorrow = tomorrow.strftime("%d/%m")
    
    print(f"\nĐang quét lịch theo giờ Việt Nam - Hôm nay ({str_today}) và Ngày mai ({str_tomorrow})...")
    
    date_blocks = soup.find_all(lambda tag: tag.name == "strong" and re.search(r'\d{2}/\d{2}', tag.text))
    
    schedule_today = []
    schedule_tomorrow = []

    for block in date_blocks:
        date_match = re.search(r'\d{2}/\d{2}', block.text)
        if not date_match:
            continue
            
        current_block_date = date_match.group(0)
        
        if current_block_date in [str_today, str_tomorrow]:
            schedule_container = block.find_next_sibling("div")
            if not schedule_container:
                continue
                
            rows = schedule_container.find_all("div", recursive=False)
            
            for row in rows:
                wrapper = row.find("div", recursive=False)
                if wrapper:
                    cols = wrapper.find_all("div", recursive=False)
                    
                    if len(cols) >= 5:
                        noi_dung = cols[0].get_text(strip=True, separator=' | ')
                        thanh_vien = cols[2].get_text(strip=True, separator=', ')
                        dia_diem = cols[3].get_text(strip=True, separator=', ')
                        
                        # Điều kiện lọc: Đang lấy tất cả cuộc họp (để test). 
                        # Nếu bạn chỉ muốn lấy lịch của VIMC Lines, hãy dùng dòng này:
                        if "Tổ giám sát (Ban TK-TH và PC&QTRR)" in thanh_vien:
                        
                        meeting_info = {
                            "noi_dung": noi_dung,
                            "thanh_vien": thanh_vien,
                            "dia_diem": dia_diem
                        }
                        
                        if current_block_date == str_today:
                            schedule_today.append(meeting_info)
                        else:
                            schedule_tomorrow.append(meeting_info)

    # ĐÓNG GÓI VÀ GỬI THÔNG BÁO CHO HÔM NAY
    print(f"\nĐang xử lý thông báo Hôm nay...")
    if schedule_today:
        msg_today = f"<b>📅 LỊCH HỌP HÔM NAY ({str_today})</b>\n\n"
        for idx, meeting in enumerate(schedule_today, 1):
            msg_today += f"<b>Lịch {idx}:</b>\n- Nội dung: {meeting['noi_dung']}\n- Địa điểm: {meeting['dia_diem']}\n\n"
        send_telegram_message(msg_today)
        print("-> Đã gửi Telegram.")
    else:
        # Nếu muốn Bot báo cả khi trống lịch thì bật dòng dưới lên
        # send_telegram_message(f"<b>📅 LỊCH HỌP HÔM NAY ({str_today})</b>\nKhông có cuộc họp nào.")
        print("-> Trống lịch, không gửi tin nhắn.")

    # ĐÓNG GÓI VÀ GỬI THÔNG BÁO CHO NGÀY MAI
    print(f"\nĐang xử lý thông báo Ngày mai...")
    if schedule_tomorrow:
        msg_tomorrow = f"<b>📅 LỊCH HỌP NGÀY MAI ({str_tomorrow})</b>\n\n"
        for idx, meeting in enumerate(schedule_tomorrow, 1):
            msg_tomorrow += f"<b>Lịch {idx}:</b>\n- Nội dung: {meeting['noi_dung']}\n- Địa điểm: {meeting['dia_diem']}\n\n"
        send_telegram_message(msg_tomorrow)
        print("-> Đã gửi Telegram.")
    else:
        print("-> Trống lịch, không gửi tin nhắn.")
        
    print("\nHOÀN TẤT!")
