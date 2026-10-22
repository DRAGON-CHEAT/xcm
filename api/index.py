from http.server import BaseHTTPRequestHandler
import json
import base64
import random
import uuid
from datetime import datetime

# مصفوفة الحروف الثابتة لفك وتشفير إحداثيات الحقن
ALLOWED_CHARACTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

def get_encrypt_key_position(char):
    return ALLOWED_CHARACTERS.find(char)

def get_encrypt_position_string(pos):
    if 0 <= pos < len(ALLOWED_CHARACTERS):
        return ALLOWED_CHARACTERS[pos]
    return "a"

def get_encrypt_key(length):
    return "".join(random.choice(ALLOWED_CHARACTERS) for _ in range(length))

# دالة فك تشفير البيانات القادمة من التطبيق (الطلب)
def decode_app_data(encrypted_str):
    try:
        if not encrypted_str or len(encrypted_str) < 2:
            return None
        pos_char = encrypted_str[-2]
        key_len_char = encrypted_str[-1]

        split_pos = get_encrypt_key_position(pos_char)
        key_length = get_encrypt_key_position(key_len_char)

        clean_text = encrypted_str[:-2]
        original_b64 = clean_text[:split_pos] + clean_text[split_pos + key_length:]

        if len(original_b64) % 4 != 0:
            original_b64 += '=' * (4 - len(original_b64) % 4)

        decoded_bytes = base64.b64decode(original_b64)
        return decoded_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        print("فشل فك تشفير الطلب الوارد:", str(e))
        return None

# دالة تشفير وحقن البيانات المرسلة للتطبيق (الاستجابة)
def encode_app_data(json_string):
    b64_str = base64.b64encode(json_string.encode('utf-8')).decode('utf-8').strip()
    key_length = random.randint(5, 15)
    encrypt_key = get_encrypt_key(key_length)
    split_pos = random.randint(5, len(b64_str) if len(b64_str) < 42 else 42)

    injected_str = b64_str[:split_pos] + encrypt_key + b64_str[split_pos:]
    pos_char = get_encrypt_position_string(split_pos)
    key_len_char = get_encrypt_position_string(key_length)
    return injected_str + pos_char + key_len_char


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")

        print("\n================ REQUEST الوارد ================")
        print("PATH:", self.path)

        try:
            req_json = json.loads(body)
            encoded_data = req_json.get("data", "")
            decoded_request_text = decode_app_data(encoded_data)

            print("الطلب الصافي بعد فك حقنة المنتصف:", decoded_request_text)

            if not decoded_request_text:
                raise ValueError("فشل فك الطلب")

            request_data_dict = json.loads(decoded_request_text)
        except Exception as e:
            print("فشل قراءة أو فك الطلب:", str(e))
            response_bytes = json.dumps({"status": "error"}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_bytes)
            return

        # ============================================================
        # معالجة طلب الـ Playlist
        # ============================================================
        if "playlist_type" in request_data_dict:
            print("\n[PLAYLIST REQUEST] تم اكتشاف playlist_type")
            playlist_name = request_data_dict.get("playlist_name", "") or request_data_dict.get("name", "") or "Playlist2"
            playlist_url = request_data_dict.get("playlist_url", "") or request_data_dict.get("url", "")
            playlist_id = uuid.uuid4().hex[:30]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            playlist_response = {
                "name": playlist_name,
                "id": playlist_id,
                "url": playlist_url,
                "type": "URL",
                "is_protected": False,
                "created_at": now,
                "updated_at": now
            }

            response_bytes = json.dumps(playlist_response, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_bytes)
            print("[✔] تم إرسال Playlist Response عادي بدون تشفير")
            return

        # ============================================================
        # معالجة بقية الطلبات والـ MAC والتشفير العكسي
        # ============================================================
        mac_from_device = ""
        try:
            nested_device_id_b64 = request_data_dict.get("app_device_id", "")
            if nested_device_id_b64:
                if len(nested_device_id_b64) % 4 != 0:
                    nested_device_id_b64 += '=' * (4 - len(nested_device_id_b64) % 4)
                mac_from_device = base64.b64decode(nested_device_id_b64).decode('utf-8', errors='ignore')
                print("تم التثبت من بصمة ماك جهاز المستخدم تلقائياً:", mac_from_device)
        except Exception as e:
            print("لم يتم العثور على ماك مضمن أو حدثت مشكلة:", str(e))

        response_template = {
            "android_version_code": "2.9",
            "apk_url": "",
            "device_key": "D2RAG0ON2SHO7W",
            "expire_date": "2026-09-25 13:36:45",
            "is_google_paid": True,
            "is_trial": 0,
            "notification": {
                "title": "DRAGONSHOW APP",
                "content": "Dragonshow player "
            },
            "urls": [
                {
                    "is_protected": "0",
                    "id": "51b568ea7c7969a881ebf3a6478f8486",
                    "name": "DRAGONSHOW XC",
                    "created_at": "2027-04-15 00:06:09",
                    "updated_at": "2099-04-15 00:06:09"
                }
            ],
            "mac_registered": True,
            "themes": [],
            "trial_days": 3600,
            "plan_id": "03370629",
            "mac_address": mac_from_device if mac_from_device else "06:0A:C4:25:CE:82:41:AD",
            "pin": "0000",
            "price": "0",
            "app_version": "2.9",
            "languages": None,
            "apk_link": ""
        }

        clean_json_str = json.dumps(response_template)
        encrypted_output_str = encode_app_data(clean_json_str)
        final_response_dict = {"data": encrypted_output_str}

        response_bytes = json.dumps(final_response_dict).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response_bytes)
        print("\n[✔] تم التشفير العكسي بنجاح، وإرسال الـ Response المُلغّم للتطبيق!")

    def do_GET(self):
        print("\nGET:", self.path)
        response_bytes = b'{"status":"OK"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response_bytes)
