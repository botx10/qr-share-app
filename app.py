from flask import Flask, request, render_template, send_file, redirect, url_for
import qrcode
import os
import uuid
import json
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import bcrypt

app = Flask(__name__)

# === CONFIG ===
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
KEY_STORE = os.path.join(app.root_path, 'keys')
LOG_FILE = os.path.join(app.root_path, 'downloads.json')
UPLOAD_LOG = os.path.join(app.root_path, 'upload_log.json')
PASSWORD_LOG = os.path.join(app.root_path, 'passwords.json')

for folder in [UPLOAD_FOLDER, QR_FOLDER, KEY_STORE]:
    os.makedirs(folder, exist_ok=True)

for file in [LOG_FILE, UPLOAD_LOG, PASSWORD_LOG]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

# === CLEANUP ===
def cleanup_old_files():
    now = datetime.now()

    with open(UPLOAD_LOG, 'r') as f:
        uploads = json.load(f)

    with open(PASSWORD_LOG, 'r') as f:
        pw_data = json.load(f)

    updated_uploads = {}
    for filename, timestamp in uploads.items():
        upload_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        if now - upload_time > timedelta(minutes=15):
            file_id = filename.split("_")[0]
            paths = [
                os.path.join(UPLOAD_FOLDER, filename),
                os.path.join(QR_FOLDER, f"{file_id}.png"),
                os.path.join(KEY_STORE, f"{file_id}.key")
            ]
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)
            pw_data.pop(filename, None)
        else:
            updated_uploads[filename] = timestamp

    with open(UPLOAD_LOG, 'w') as f:
        json.dump(updated_uploads, f)

    with open(PASSWORD_LOG, 'w') as f:
        json.dump(pw_data, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    cleanup_old_files()

    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            return 'No file selected.'

        access_type = request.form.get('access')
        password_raw = request.form.get('password') if access_type == 'private' else None

        file_id = str(uuid.uuid4())
        encrypted_filename = f"{file_id}_{file.filename}.enc"
        encrypted_path = os.path.join(UPLOAD_FOLDER, encrypted_filename)

        key = Fernet.generate_key()
        cipher = Fernet(key)
        encrypted_data = cipher.encrypt(file.read())

        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        with open(os.path.join(KEY_STORE, f"{file_id}.key"), 'wb') as f:
            f.write(key)

        domain = "https://qr-share-app.onrender.com"
        download_url = f"{domain}/download/{encrypted_filename}"
        qr_path = os.path.join(QR_FOLDER, f"{file_id}.png")
        qrcode.make(download_url).save(qr_path)

        with open(UPLOAD_LOG, 'r') as f:
            uploads = json.load(f)
        uploads[encrypted_filename] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(UPLOAD_LOG, 'w') as f:
            json.dump(uploads, f)

        if access_type == 'private' and password_raw:
            hashed_pw = bcrypt.hashpw(password_raw.encode(), bcrypt.gensalt()).decode()
            with open(PASSWORD_LOG, 'r') as f:
                pw_data = json.load(f)
            pw_data[encrypted_filename] = hashed_pw
            with open(PASSWORD_LOG, 'w') as f:
                json.dump(pw_data, f)

        return render_template('index.html',
                               qr_path=os.path.join('static', 'qrcodes', f"{file_id}.png"),
                               encrypted_filename=encrypted_filename)

    return render_template('index.html')

@app.route('/download/<filename>', methods=['GET', 'POST'])
def download(filename):
    cleanup_old_files()
    with open(PASSWORD_LOG, 'r') as f:
        pw_data = json.load(f)

    requires_password = filename in pw_data

    if request.method == 'POST':
        entered_pw = request.form.get('password', '')
        stored_hash = pw_data.get(filename, '').encode()

        if not entered_pw or not bcrypt.checkpw(entered_pw.encode(), stored_hash):
            return "Incorrect password. Access denied."

        return process_file_download(filename)

    if requires_password:
        return '''
        <h3>This file is password protected.</h3>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter password" required>
            <button type="submit">Download</button>
        </form>
        '''

    return process_file_download(filename)

def process_file_download(filename):
    try:
        encrypted_path = os.path.join(UPLOAD_FOLDER, filename)
        file_id = filename.replace(".enc", "").split("_", 1)[0]
        key_path = os.path.join(KEY_STORE, f"{file_id}.key")

        with open(key_path, 'rb') as kf:
            key = kf.read()
        cipher = Fernet(key)

        with open(encrypted_path, 'rb') as ef:
            decrypted_data = cipher.decrypt(ef.read())

        original_filename = filename.replace(".enc", "").split("_", 1)[1]
        decrypted_path = os.path.join(UPLOAD_FOLDER, f"dec_{original_filename}")
        with open(decrypted_path, 'wb') as df:
            df.write(decrypted_data)

        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
        logs[filename] = logs.get(filename, 0) + 1
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f)

        return send_file(decrypted_path, as_attachment=True)

    except FileNotFoundError:
        return "File not found or has expired."
    except Exception as e:
        return f"Error decrypting file: {str(e)}"

@app.route('/log')
def show_logs():
    with open(LOG_FILE, 'r') as f:
        logs = json.load(f)
    return "<h2>Download Stats</h2><ul>" + "".join(f"<li>{k} → {v} downloads</li>" for k, v in logs.items()) + "</ul>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
