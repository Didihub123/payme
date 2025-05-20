from flask import Flask, render_template, request, jsonify, redirect
import requests 
import json 
import time

app = Flask(__name__)

# TOKEN dan CHAT_ID Telegram 
TELEGRAM_TOKEN = '7805960444:AAEb3UUNT3DZUfds6G2trRLv8UrJtLZfyyc' 
CHAT_ID = '-1002500559635' 
  
# Data login didihub 
LOGIN_URL = 'https://www.didihub.com/api/main/user/email/login'
PAY_CHANNEL_URL = 'https://www.didihub.com/api/main/pay/channel'
PAY_POST_URL = 'https://www.didihub.com/api/main/pay/67'  # Channel QRIS id=67 
  
email = "Bukanmasterbiasa@gmail.com" 
password = "Gunawan12345" 
browserVisitorId = "05467f96e147f52215497fe02e9d24e0" 
programVisitorId = "8650KmEtzpHDEjWb" 
  
# Data pembayaran 
pay_phone = "822328947322" 
pay_name = "ASEp" 

# Variabel global untuk menyimpan URL terakhir
last_qr_url = None

def send_telegram_message(token, chat_id, message): 
    """Fungsi untuk mengirim pesan ke Telegram dengan penanganan error yang lebih baik"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = { 
        "chat_id": chat_id, 
        "text": message
    } 
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        print(f"Status respons Telegram: {resp.status_code}")
        print(f"Isi respons: {resp.text}")
        
        if resp.status_code == 200:
            return True, "Pesan berhasil dikirim"
        else:
            return False, f"Error mengirim pesan ke Telegram: {resp.text}"
    except Exception as e:
        return False, f"Exception saat mengirim pesan ke Telegram: {str(e)}"

def process_payment(amount):
    global last_qr_url
    try:
        print(f"Memulai proses pembayaran dengan nominal: {amount}...")
        
        # Login ke didihub 
        login_payload = { 
            "email": email, 
            "password": password, 
            "browserVisitorId": browserVisitorId, 
            "programVisitorId": programVisitorId 
        } 
        login_headers = { 
            "Content-Type": "application/json", 
            "Origin": "https://www.didihub.com", 
            "Referer": "https://www.didihub.com/" 
        } 
      
        print("Mencoba login ke didihub...")
        login_resp = requests.post(LOGIN_URL, json=login_payload, headers=login_headers, timeout=30) 
        print(f"Status login: {login_resp.status_code}")
        
        if login_resp.status_code != 200: 
            return False, f"Login gagal: {login_resp.text}", None
      
        login_data = login_resp.json()
        token = login_data.get("token") 
        if not token: 
            return False, f"Token tidak ditemukan dalam respons: {login_data}", None
      
        print("Login sukses, token diterima.") 
      
        # Request channel pembayaran
        headers_auth = { 
            "Authorization": f"Bearer {token}", 
            "User_token": token 
        } 
        
        print("Mengambil informasi channel pembayaran...")
        channel_resp = requests.get(PAY_CHANNEL_URL, headers=headers_auth, timeout=30) 
        if channel_resp.status_code != 200: 
            return False, f"Gagal ambil channel pembayaran: {channel_resp.text}", None
      
        print("Channel pembayaran berhasil diambil.") 
      
        # Request pembayaran via channel QRIS id=67 
        pay_headers = { 
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {token}", 
            "User_token": token, 
            "Origin": "https://www.didihub.com", 
            "Referer": "https://www.didihub.com/" 
        } 
      
        pay_payload = { 
            "amount": amount,  # Gunakan nominal dari parameter
            "phone": pay_phone, 
            "name": pay_name 
        } 
      
        print("Memproses pembayaran...")
        pay_resp = requests.post(PAY_POST_URL, json=pay_payload, headers=pay_headers, timeout=30) 
        if pay_resp.status_code != 200: 
            return False, f"Gagal request pembayaran: {pay_resp.text}", None
      
        pay_result = pay_resp.json() 
        print("Pembayaran berhasil diproses. Respons:", json.dumps(pay_result, indent=2)) 
      
        # Cari URL QR code dari berbagai kemungkinan field
        qr_code_url = None
        possible_fields = ['qrCodeUrl', 'qr_code', 'qr', 'qrCode', 'qrUrl', 'url']
        
        for field in possible_fields:
            if field in pay_result:
                qr_code_url = pay_result[field]
                print(f"URL QR Code ditemukan di field '{field}'")
                break
                
        # Jika tidak ditemukan di level atas, coba cari di nested objects
        if not qr_code_url:
            for key, value in pay_result.items():
                if isinstance(value, dict):
                    for field in possible_fields:
                        if field in value:
                            qr_code_url = value[field]
                            print(f"URL QR Code ditemukan di nested field '{key}.{field}'")
                            break
                    if qr_code_url:
                        break
      
        # Kirim ke Telegram
        if qr_code_url: 
            print(f"Mengirim URL ke Telegram: {qr_code_url}")
            last_qr_url = qr_code_url  # Simpan URL untuk redirect
            
            # Coba beberapa kali jika gagal
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                print(f"Percobaan ke-{attempt} mengirim pesan ke Telegram...")
                success, message = send_telegram_message(TELEGRAM_TOKEN, CHAT_ID, qr_code_url)
                if success: 
                    return True, "URL berhasil dikirim ke Telegram.", qr_code_url
                else: 
                    print(f"Gagal mengirim URL ke Telegram pada percobaan ke-{attempt}: {message}")
                    if attempt < max_attempts:
                        print("Mencoba lagi dalam 5 detik...")
                        time.sleep(5)
            
            return False, f"Gagal mengirim URL ke Telegram setelah {max_attempts} percobaan.", qr_code_url
        else:
            error_msg = "URL QR Code tidak ditemukan dalam response."
            print(error_msg)
            print("Isi lengkap response:", json.dumps(pay_result, indent=2))
            
            # Kirim seluruh response ke Telegram untuk debugging
            send_telegram_message(TELEGRAM_TOKEN, CHAT_ID, f"QR Code tidak ditemukan. Response: {json.dumps(pay_result)}")
            return False, error_msg, None
    
    except Exception as e:
        error_msg = f"Terjadi kesalahan: {str(e)}"
        print(error_msg)
        # Coba kirim pesan error ke Telegram
        send_telegram_message(TELEGRAM_TOKEN, CHAT_ID, f"Error dalam proses: {str(e)}")
        return False, error_msg, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    amount = request.form.get('amount', '')
    if not amount:
        return jsonify({'success': False, 'message': 'Nominal pembayaran tidak boleh kosong'})
    
    success, message, qr_url = process_payment(amount)
    
    if success and qr_url:
        # Redirect ke URL QR
        return redirect(qr_url)
    else:
        return jsonify({'success': success, 'message': message})

if __name__ == '__main__':
    app.run(debug=True)
