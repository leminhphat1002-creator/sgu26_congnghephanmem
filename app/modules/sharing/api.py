"""Tạo QR cục bộ; không gửi đường dẫn qua dịch vụ bên ngoài."""

import os
from io import BytesIO
from urllib.parse import urlsplit

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter(tags=["sharing"])


def public_url(request: Request) -> str:
    url = (os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/") + "/"
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise HTTPException(503, "PUBLIC_BASE_URL cần là địa chỉ HTTP/HTTPS hợp lệ.")
    if parsed.query or parsed.fragment or parsed.path != "/":
        raise HTTPException(503, "PUBLIC_BASE_URL chỉ gồm tên miền/IP và cổng.")
    return url


@router.get("/api/share")
def share_info(request: Request):
    url = public_url(request)
    host = urlsplit(url).hostname
    return {
        "url": url,
        "qr_url": "/share/qr.svg",
        "local_only": host in {"localhost", "127.0.0.1", "::1"},
    }


@router.get("/share/qr.svg")
def qr_code(request: Request):
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    code.add_data(public_url(request))
    code.make(fit=True)
    image = code.make_image(image_factory=qrcode.image.svg.SvgPathFillImage)
    return Response(
        image.to_string(),
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": 'inline; filename="bat-trang-qr.svg"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/share/qr.png")
def qr_png(request: Request):
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    code.add_data(public_url(request))
    code.make(fit=True)
    image = code.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return Response(
        output.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": 'inline; filename="bat-trang-qr.png"',
            "Cache-Control": "no-store",
        },
    )
