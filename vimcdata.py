from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re

import os
USERNAME = os.environ.get("VBS_USERNAME")
PASSWORD = os.environ.get("VBS_PASSWORD")

def get_schedule_html():
    with sync_playwright() as p:
        # headless=False để dễ quan sát. Khi nào chạy ổn định có thể đổi thành True
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        print("Đang truy cập trang đăng nhập...")
        page.goto("https://vbs.vimc.co/")

        # 1. ĐĂNG NHẬP
        page.wait_for_selector("#username") 
        page.fill("#username", USERNAME)
        
        page.wait_for_selector("#password")
        page.fill("#password", PASSWORD)
        
        page.click("button[type='submit']") 

        # Chờ đăng nhập thành công
        page.wait_for_load_state("networkidle")
        print("Đăng nhập thành công!")

        # 2. TRUY CẬP TRANG LỊCH CÔNG TÁC
        print("Đang tải dữ liệu lịch...")
        page.goto("https://vbs.vimc.co/utility/company-work-schedule")
        
        # Đợi tiêu đề cột xuất hiện thay vì tìm thẻ table
        page.wait_for_selector("text='Thành viên tham gia'", timeout=30000) 
        time.sleep(3) # Đợi thêm 1 chút cho animation và dữ liệu load hết

        # 3. LẤY MÃ HTML
        html_content = page.content()
        browser.close()
        
        return html_content

if __name__ == "__main__":
    html_data = get_schedule_html()
    soup = BeautifulSoup(html_data, "html.parser")
    
    # 1. KHỞI TẠO BIẾN THỜI GIAN
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    str_today = today.strftime("%d/%m")       # VD: "07/09"
    str_tomorrow = tomorrow.strftime("%d/%m") # VD: "08/09"
    
    print(f"\nĐang quét lịch cho Hôm nay ({str_today}) và Ngày mai ({str_tomorrow})...")

    # 2. LẤY TOÀN BỘ CÁC KHỐI NGÀY TRÊN BẢNG
    date_blocks = soup.find_all(lambda tag: tag.name == "strong" and re.search(r'\d{2}/\d{2}', tag.text))
    
    # Danh sách chứa kết quả cuối cùng
    schedule_today = []
    schedule_tomorrow = []

    # 3. QUÉT TỪNG NGÀY ĐỂ TÌM KIẾM
    for block in date_blocks:
        # Xác định khối này đang là ngày nào
        date_match = re.search(r'\d{2}/\d{2}', block.text)
        if not date_match:
            continue
            
        current_block_date = date_match.group(0)
        
        # Chỉ xử lý nếu ngày đó là Hôm nay hoặc Ngày mai
        if current_block_date in [str_today, str_tomorrow]:
            schedule_container = block.find_next_sibling("div")
            if not schedule_container:
                continue
                
            rows = schedule_container.find_all("div", recursive=False)
            
            # Duyệt qua các cuộc họp của ngày đang xét
            for row in rows:
                wrapper = row.find("div", recursive=False)
                if wrapper:
                    cols = wrapper.find_all("div", recursive=False)
                    
                    if len(cols) >= 5:
                        noi_dung = cols[0].get_text(strip=True, separator=' | ')
                        thanh_vien = cols[2].get_text(strip=True, separator=', ')
                        dia_diem = cols[3].get_text(strip=True, separator=', ')
                        
                        # 4. LỌC THEO TỪ KHÓA
                        if "Tổ giám sát (Ban TK-TH và PC&QTRR)" in thanh_vien:  # Có thể đổi thành "Ban TK-TH" để test
                            meeting_info = {
                                "noi_dung": noi_dung,
                                "thanh_vien": thanh_vien,
                                "dia_diem": dia_diem
                            }
                            
                            # Phân loại vào đúng danh sách
                            if current_block_date == str_today:
                                schedule_today.append(meeting_info)
                            else:
                                schedule_tomorrow.append(meeting_info)

    # 5. IN THÔNG BÁO CHO HÔM NAY
    print(f"\n======================================")
    print(f"THÔNG BÁO 1: LỊCH HÔM NAY ({str_today})")
    print(f"======================================")
    if schedule_today:
        for idx, meeting in enumerate(schedule_today, 1):
            print(f"Lịch {idx}:")
            print(f" - Nội dung: {meeting['noi_dung']}")
            print(f" - Địa điểm: {meeting['dia_diem']}")
    else:
        print("Trống lịch (Không có cuộc họp nào liên quan)")

    # 6. IN THÔNG BÁO CHO NGÀY MAI
    print(f"\n======================================")
    print(f"THÔNG BÁO 2: LỊCH NGÀY MAI ({str_tomorrow})")
    print(f"======================================")
    if schedule_tomorrow:
        for idx, meeting in enumerate(schedule_tomorrow, 1):
            print(f"Lịch {idx}:")
            print(f" - Nội dung: {meeting['noi_dung']}")
            print(f" - Địa điểm: {meeting['dia_diem']}")
    else:
        print("Trống lịch (Không có cuộc họp nào liên quan)")
