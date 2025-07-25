from flask import Flask, request, render_template, send_file
import qrcode
import os
import uuid
import json
from cryptography.fernet import Fernet
from datetime import datetime, timedelta

app = Flask(__name__)

# === CONFIG ===
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max file size
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
KEY_STORE = os.path.join(app.root_path, 'keys')
LOG_FILE = os.path.join(app.root_path, 'downloads.json')
UPLOAD_LOG = os.path.join(app.root_path, 'upload_log.json')  # track upload timestamps

# === SETUP FOLDERS ===
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(KEY_STORE, exist_ok=True)

# === INIT JSON FILES ===
for file in [LOG_FILE, UPLOAD_LOG]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

# === CLEANUP OLD FILES ===
def cleanup_old_files():
    with open(UPLOAD_LOG, 'r') as f:
        uploads = json.load(f)

    now = datetime.now()
    updated_uploads = {}

    for filename, timestamp in uploads.items():
        upload_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        if now - upload_time > timedelta(minutes=15):
            # Delete files
            encrypted_path = os.path.join(UPLOAD_FOLDER, filename)
            key_id = filename.split("_")[0]
            key_path = os.path.join(KEY_STORE, f"{key_id}.key")
            qr_path = os.path.join(QR_FOLDER, f"{key_id}.png")

            for path in [encrypted_path, key_path, qr_path]:
                if os.path.exists(path):
                    os.remove(path)
        else:
            # Keep recent uploads
            updated_uploads[filename] = timestamp

    with open(UPLOAD_LOG, 'w') as f:
        json.dump(updated_uploads, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    cleanup_old_files()

    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part in request.'

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return 'No selected file.'

        # === Unique ID ===
        file_id = str(uuid.uuid4())
        original_filename = uploaded_file.filename
        encrypted_filename = f"{file_id}_{original_filename}.enc"
        encrypted_path = os.path.join(UPLOAD_FOLDER, encrypted_filename)

        # === Encrypt & Save ===
        key = Fernet.generate_key()
        cipher = Fernet(key)
        file_data = uploaded_file.read()
        encrypted_data = cipher.encrypt(file_data)

        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        with open(os.path.join(KEY_STORE, f"{file_id}.key"), 'wb') as key_file:
            key_file.write(key)

        # === QR Code ===
        render_domain = "https://qr-share-app.onrender.com"
        download_url = f"{render_domain}/download/{encrypted_filename}"
        qr = qrcode.make(download_url)
        qr_path = os.path.join(QR_FOLDER, f"{file_id}.png")
        qr.save(qr_path)

        # === Save upload time ===
        with open(UPLOAD_LOG, 'r') as f:
            uploads = json.load(f)

        uploads[encrypted_filename] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(UPLOAD_LOG, 'w') as f:
            json.dump(uploads, f)

        return render_template('index.html',
                               qr_path=os.path.join('static', 'qrcodes', f"{file_id}.png"),
                               encrypted_filename=encrypted_filename)

    return render_template('index.html')

@app.route('/download/<filename>')
def download(filename):
    cleanup_old_files()  # ensure expired files are removed before download

    try:
        encrypted_path = os.path.join(UPLOAD_FOLDER, filename)
        file_id = filename.replace(".enc", "").split("_")[0]
        key_path = os.path.join(KEY_STORE, f"{file_id}.key")

        # Load key & decrypt
        with open(key_path, 'rb') as key_file:
            key = key_file.read()
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()

        cipher = Fernet(key)
        decrypted_data = cipher.decrypt(encrypted_data)

        # Save and return decrypted file
        original_filename = filename.replace(".enc", "").split("_", 1)[1]
        decrypted_path = os.path.join(UPLOAD_FOLDER, f"dec_{original_filename}")
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)

        # Update download log
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
        logs[filename] = logs.get(filename, 0) + 1
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f)

        return send_file(decrypted_path, as_attachment=True)

    except FileNotFoundError:
        return "Error: File or key not found. It may have expired."
    except Exception as e:
        return f"Decryption failed: {str(e)}"

@app.route('/log')
def show_logs():
    with open(LOG_FILE, 'r') as f:
        logs = json.load(f)
    log_html = "<h2>Download Stats</h2><ul>"
    for file, count in logs.items():
        log_html += f"<li>{file} → {count} downloads</li>"
    log_html += "</ul>"
    return log_html

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
