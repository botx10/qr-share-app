from flask import Flask, request, render_template, send_file
import qrcode
import os
import uuid
import json
from cryptography.fernet import Fernet

app = Flask(__name__)

# ==== CONFIGURATION ====
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max upload
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
KEY_STORE = os.path.join(app.root_path, 'keys')
LOG_FILE = os.path.join(app.root_path, 'downloads.json')  # download counter

# ==== FOLDER SETUP ====
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(KEY_STORE, exist_ok=True)

# ==== INIT DOWNLOAD COUNTS ====
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        json.dump({}, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part in request.'

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return 'No selected file.'

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        original_filename = uploaded_file.filename
        encrypted_filename = f"{file_id}_{original_filename}.enc"
        encrypted_path = os.path.join(UPLOAD_FOLDER, encrypted_filename)

        # Encrypt file
        key = Fernet.generate_key()
        cipher = Fernet(key)
        file_data = uploaded_file.read()
        encrypted_data = cipher.encrypt(file_data)

        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        # Save key
        key_path = os.path.join(KEY_STORE, f"{file_id}.key")
        with open(key_path, 'wb') as key_file:
            key_file.write(key)

        # Create QR code
        render_domain = "https://qr-share-app.onrender.com"
        download_url = f"{render_domain}/download/{encrypted_filename}"
        qr = qrcode.make(download_url)
        qr_path = os.path.join(QR_FOLDER, f"{file_id}.png")
        qr.save(qr_path)

        return render_template('index.html',
                               qr_path=os.path.join('static', 'qrcodes', f"{file_id}.png"),
                               key=key.decode(),
                               encrypted_filename=encrypted_filename)  # 👈 New line

    return render_template('index.html')

@app.route('/download/<filename>')
def download(filename):
    try:
        # Paths
        encrypted_path = os.path.join(UPLOAD_FOLDER, filename)
        file_id = filename.replace(".enc", "").split("_")[0]
        key_path = os.path.join(KEY_STORE, f"{file_id}.key")

        # Load key
        with open(key_path, 'rb') as key_file:
            key = key_file.read()

        # Decrypt
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        cipher = Fernet(key)
        decrypted_data = cipher.decrypt(encrypted_data)

        # Save decrypted file
        original_filename = filename.replace(".enc", "").split("_", 1)[1]
        decrypted_path = os.path.join(UPLOAD_FOLDER, f"dec_{original_filename}")
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)

        # Update download count
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)

        logs[filename] = logs.get(filename, 0) + 1

        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f)

        return send_file(decrypted_path, as_attachment=True)

    except FileNotFoundError as fnf:
        return f"Error: {str(fnf)}"
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
