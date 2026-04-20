"""
User registration: create Supabase account + send welcome email via Resend.
"""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.db import supabase
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    open_id: str = ""


@router.post("/register")
def register(body: RegisterRequest):
    # Create user via admin API (auto-confirmed, no Supabase email needed)
    try:
        result = supabase.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate magic link so user is auto-logged in when clicking the email
    redirect_to = f"{settings.dashboard_url}/bind"
    if body.open_id:
        redirect_to += f"?open_id={body.open_id}"

    try:
        link_resp = supabase.auth.admin.generate_link({
            "type": "magiclink",
            "email": body.email,
            "options": {"redirect_to": redirect_to},
        })
        magic_link = link_resp.properties.action_link
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate link: {e}")

    _send_welcome_email(body.email, magic_link)
    return {"ok": True}


def _send_welcome_email(email: str, magic_link: str) -> None:
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
  <h2 style="margin-bottom:8px">欢迎使用 pi-matrix</h2>
  <p style="color:#555;margin-bottom:24px">点击下方按钮，完成账号绑定，您的数字员工即刻上线。</p>
  <a href="{magic_link}"
     style="display:inline-block;background:#000;color:#fff;text-decoration:none;
            padding:12px 28px;border-radius:8px;font-weight:600">
    绑定飞书账号
  </a>
  <p style="color:#aaa;font-size:12px;margin-top:32px">
    此链接 24 小时内有效，仅限一次使用。
  </p>
</div>
""".strip()

    with httpx.Client(timeout=10) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.from_email,
                "to": [email],
                "subject": "欢迎使用 pi-matrix，点击完成绑定",
                "html": html,
            },
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=500, detail=f"Resend error: {resp.text}")
