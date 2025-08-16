import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport import requests
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import requests as req



import pathlib

# ------------------- Config -------------------
APP_ROOT = pathlib.Path(__file__).parent.resolve()
CONFIG_PATH = APP_ROOT / "config.json"
ALLOWED_USERS_PATH = APP_ROOT / "allowed_users.json"
CREDENTIALS_FILE = APP_ROOT / "credentials.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

with open(ALLOWED_USERS_PATH, "r", encoding="utf-8") as f:
    ALLOWED_USERS = set(json.load(f).get("emails", []))

print(f"Daftar email yang diizinkan: {ALLOWED_USERS}")


FOLDER_ID = CONFIG.get("folder_id", "")
BRANDING = CONFIG.get("branding", {})
THEME = CONFIG.get("theme", {})

# Flask app
app = Flask(__name__, static_url_path='/static', template_folder='.')

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# OAuth 2.0 settings
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive.file"
]

REDIRECT_URI = CONFIG.get("redirect_uri", "http://localhost:5000/oauth2callback")

# ------------------- Helpers -------------------
def build_flow():
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def get_drive(creds: Credentials):
    return build("drive", "v3", credentials=creds)


def get_user_email(creds: Credentials):
    # 1. Coba ambil email dari id_token (kalau ada)
    try:
        if hasattr(creds, "id_token") and creds.id_token:
            idinfo = id_token.verify_oauth2_token(
                creds.id_token,
                grequests.Request(),
                creds.client_id  # validasi client_id
            )
            email = idinfo.get("email")
            if email:
                return email
    except Exception as e:
        print(f"[DEBUG] Gagal ambil email dari id_token: {e}")

    # 2. Fallback ke endpoint userinfo
    try:
        resp = req.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"}
        )
        data = resp.json()
        return data.get("email")
    except Exception as e:
        print(f"[DEBUG] Gagal ambil email dari userinfo: {e}")
        return None


# ------------------- Routes -------------------
@app.route("/")
def home():
    user_email = session.get("user_email")
    return render_template(
        "index.html",
        branding=BRANDING,
        theme=THEME,
        user_email=user_email
    )


@app.route("/login")
def login():
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    session["state"] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    state = session.get("state")
    flow = build_flow()
    
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        print("=== DEBUG ERROR DETAIL ===")
        print(e)  # Akan tampil di CMD
        return f"ERROR saat ambil token: {e}"

    creds = flow.credentials
    # Persist only in session; for production consider server-side storage
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": getattr(creds, "refresh_token", None),
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    # Determine user email and convert to lowercase for case-insensitive matching
    user_email = get_user_email(creds)
    if user_email:
        user_email = user_email.lower()
    session["user_email"] = user_email

    print(f"DEBUGGING: Email yang diterima dari Google adalah ->'{user_email}'<-")

    if not user_email or user_email.strip().lower() not in [e.lower() for e in ALLOWED_USERS]:
        session.pop("credentials", None)
        session.pop("user_email", None)
        flash("Akses ditolak. Email Anda belum diizinkan.", "error")
        return redirect(url_for("home"))
    return redirect(url_for("home"))



@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for("home"))

@app.route("/upload", methods=["POST"])
def upload():
    # Auth check
    creds_dict = session.get("credentials")
    user_email = session.get("user_email")
    if not creds_dict or not user_email or user_email not in ALLOWED_USERS:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for("home"))

    creds = Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes"),
    )

    jenis = request.form.get("jenis", "").strip()
    custom_name = request.form.get("custom_name", "").strip()
    f = request.files.get("file")

    if not (jenis and custom_name and f):
        flash("Form belum lengkap.", "error")
        return redirect(url_for("home"))

    ext = os.path.splitext(f.filename)[1]  # contoh: .jpg, .pdf
    final_name = f"{jenis}_{custom_name}{ext}"

    temp_dir = APP_ROOT / "temp"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / final_name
    f.save(str(temp_path))

    try:
        drive = get_drive(creds)
        media = MediaFileUpload(str(temp_path), resumable=False)
        file_metadata = {"name": final_name}
        if FOLDER_ID:
            file_metadata["parents"] = [FOLDER_ID]

        created = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name"
        ).execute()

        flash(f"✅ Berhasil upload: {created.get('name')}", "success")
    except Exception as e:
        flash(f"❌ Gagal upload: {e}", "error")
    finally:
        try:
            os.remove(str(temp_path))
        except Exception:
            pass

    return redirect(url_for("home"))



# Health check / static send for logo placeholder
@app.route("/logo")
def logo():
    return send_from_directory("static/images", "logo.png")

if __name__ == "__main__":
    # Host on localhost:5000
    app.run(host="127.0.0.1", port=5000, debug=True)