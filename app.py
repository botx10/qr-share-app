from flask import Flask, request, render_template, send_from_directory
import qrcode
import os
import uuid
from cryptography.fernet import Fernet

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
QR_FOLDER = 'static/qrcodes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create folders if they don’t exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# Generate encryption key
fernet_key = Fernet.generate_key()
cipher = Fernet(fernet_key)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part in request.'

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return 'No selected file.'

        # Save encrypted file
        file_id = str(uuid.uuid4())
        filename = file_id + "_" + uploaded_file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        file_data = uploaded_file.read()
        encrypted_data = cipher.encrypt(file_data)

        with open(file_path, 'wb') as f:
            f.write(encrypted_data)

        # Generate QR with download link
        download_url = f"https://qr-share-app.onrender.com/download/{filename}"
        qr = qrcode.make(download_url)
        qr_path = os.path.join(QR_FOLDER, file_id + ".png")
        qr.save(qr_path)

        return render_template('index.html', qr_path=qr_path, key=fernet_key.decode())

    return render_template('index.html')

from flask import send_file

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

