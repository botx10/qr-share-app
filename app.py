from flask import Flask, request, render_template, send_file
import qrcode
import os
import uuid
from cryptography.fernet import Fernet

app = Flask(__name__)

# Absolute folder paths for Render
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
KEY_STORE = os.path.join(app.root_path, 'keys')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(KEY_STORE, exist_ok=True)

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

        # Generate key and encrypt data
        key = Fernet.generate_key()
        cipher = Fernet(key)
        file_data = uploaded_file.read()
        encrypted_data = cipher.encrypt(file_data)

        # Save encrypted file
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        # Save encryption key
        key_path = os.path.join(KEY_STORE, f"{file_id}.key")
        with open(key_path, 'wb') as key_file:
            key_file.write(key)

        # Generate QR code
        render_domain = "https://qr-share-app.onrender.com"  # replace with your actual Render domain
        download_url = f"{render_domain}/download/{file_id}_{original_filename}.enc"
        qr = qrcode.make(download_url)
        qr_path = os.path.join(QR_FOLDER, f"{file_id}.png")
        qr.save(qr_path)

        return render_template('index.html',
                               qr_path=os.path.join('static', 'qrcodes', f"{file_id}.png"),
                               key=key.decode())

    return render_template('index.html')

@app.route('/download/<filename>')
def download(filename):
    try:
        # Reconstruct paths
        encrypted_path = os.path.join(UPLOAD_FOLDER, filename)
        file_id = filename.split("_")[0]
        key_path = os.path.join(KEY_STORE, f"{file_id}.key")

        # Load encryption key
        with open(key_path, 'rb') as key_file:
            key = key_file.read()

        # Decrypt file
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        cipher = Fernet(key)
        decrypted_data = cipher.decrypt(encrypted_data)

        # Prepare decrypted file
        original_filename = filename.replace(".enc", "").split("_", 1)[1]
        decrypted_path = os.path.join(UPLOAD_FOLDER, f"dec_{original_filename}")
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)

        return send_file(decrypted_path, as_attachment=True)

    except FileNotFoundError as fnf:
        return f"Error: {str(fnf)} — file not found on server."
    except Exception as e:
        return f"Decryption failed: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
