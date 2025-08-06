# qr-share-app
Secure file sharing using QR codes
# 🔐 Secure File Sharing Using QR Codes

This project allows users to securely upload and share encrypted files using QR codes. It supports password protection, auto-deletion of files, and has an admin panel to monitor logs and file activity.

## 🌐 Live Demo
🔗 [Try the Application](https://qr-share-app.onrender.com)

---

## 🚀 Features

- Upload any document or image (up to 100MB)
- Files are encrypted on the server
- Unique QR code is generated for every upload
- Option to set a password before sharing
- File auto-deletes after 15 minutes
- Admin dashboard for monitoring downloads, files, and passwords

---

## 🔧 Tech Stack

- **Backend**: Python + Flask
- **Frontend**: HTML, CSS, JavaScript
- **Encryption**: cryptography (Fernet)
- **Password Security**: bcrypt
- **QR Code Generation**: qrcode (Python package)
- **Hosting**: Render
- **Version Control**: Git, GitHub

---

## 📸 Screenshots

> Include screenshots of:
- Home upload page
- QR code generation
- Admin login
- Admin dashboard

---

## 🔐 Admin Access

To access the admin dashboard:
1. Click **Admin** on the homepage.
2. Use the default password: `admin123`

(Admin password is securely managed on server.)

---

## 📁 File Structure

```
project-root/
│
├── templates/
│   └── index.html, admin.html
├── static/qrcodes/
├── uploads/
├── keys/
├── app.py
├── passwords.json
├── upload_log.json
├── downloads.json
├── requirements.txt
```

---

## 🛠 How to Run Locally

```bash
git clone https://github.com/your-username/qr-file-share.git
cd qr-file-share
pip install -r requirements.txt
python app.py
```

---

## 📌 Future Enhancements

- Countdown timer on QR page
- OTP/email verification for download
- Native Android/iOS support
- File preview before download

---

## 🧠 Made With

❤️ By Aryaman Menon | MCA @ RV Institute of Technology and Management

---

## 📄 License

This project is for academic use only.
