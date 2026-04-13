import base64
from urllib.parse import quote_plus

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request


class FederationCompliancePortal(CustomerPortal):
    def _prepare_compliance_layout_values(self, **extra_values):
        values = self._prepare_portal_layout_values()
        values.update(extra_values)
        values.setdefault("page_name", "my_compliance")
        return values

    def _get_workspace_entry(self, requirement_id, target_model, target_id):
        return request.env[
            "federation.document.requirement"
        ]._portal_get_workspace_entry_for_user(
            requirement_id=requirement_id,
            target_model=target_model,
            target_id=target_id,
            user=request.env.user,
        )

    def _create_submission_attachments(self, submission, uploaded_files):
        attachment_ids = []
        Attachment = request.env["ir.attachment"].with_user(request.env.user).sudo()
        for uploaded_file in uploaded_files:
            filename = (uploaded_file.filename or "").strip()
            if not filename:
                continue
            payload = uploaded_file.read()
            if not payload:
                continue
            attachment = Attachment.create(
                {
                    "name": filename,
                    "datas": base64.b64encode(payload),
                    "res_model": submission._name,
                    "res_id": submission.id,
                    "mimetype": uploaded_file.mimetype,
                }
            )
            attachment_ids.append(attachment.id)

        if attachment_ids:
            submission.with_user(request.env.user).sudo().write(
                {"attachment_ids": [(6, 0, attachment_ids)]}
            )

    @http.route(["/my/compliance"], type="http", auth="user", website=True)
    def portal_my_compliance(self, **kw):
        Requirement = request.env["federation.document.requirement"]
        workspace_entries = Requirement._portal_get_workspace_entries(user=request.env.user)
        values = self._prepare_compliance_layout_values(
            workspace_entries=workspace_entries,
            has_compliance_access=Requirement._portal_has_access(user=request.env.user),
            counts={
                "attention": len([entry for entry in workspace_entries if entry["requires_attention"]]),
                "in_review": len([entry for entry in workspace_entries if entry["status_key"] == "submitted"]),
                "approved": len([entry for entry in workspace_entries if entry["status_key"] == "approved"]),
            },
            success=kw.get("success"),
            error=kw.get("error"),
        )
        return request.render(
            "sports_federation_compliance.portal_my_compliance_workspace",
            values,
        )

    @http.route(
        ["/my/compliance/<int:requirement_id>/<string:target_model>/<int:target_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_compliance_detail(self, requirement_id, target_model, target_id, **kw):
        entry = self._get_workspace_entry(requirement_id, target_model, target_id)
        if not entry:
            return request.not_found()

        values = self._prepare_compliance_layout_values(
            compliance_entry=entry,
            success=kw.get("success"),
            error=kw.get("error"),
        )
        return request.render(
            "sports_federation_compliance.portal_my_compliance_detail",
            values,
        )

    @http.route(
        ["/my/compliance/<int:requirement_id>/<string:target_model>/<int:target_id>/submit"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_compliance_submit(self, requirement_id, target_model, target_id, **post):
        entry = self._get_workspace_entry(requirement_id, target_model, target_id)
        if not entry:
            return request.not_found()

        redirect_url = entry["detail_url"]
        try:
            submission = request.env["federation.document.submission"]._portal_prepare_submission(
                entry["requirement"],
                entry["target"],
                values={
                    "issue_date": (post.get("issue_date") or "").strip() or False,
                    "expiry_date": (post.get("expiry_date") or "").strip() or False,
                    "notes": (post.get("notes") or "").strip() or False,
                },
                user=request.env.user,
            )
            self._create_submission_attachments(
                submission,
                request.httprequest.files.getlist("attachment"),
            )
            if not submission.attachment_ids:
                raise ValidationError(
                    "Upload at least one document attachment before submitting."
                )
            submission.with_user(request.env.user).sudo().action_submit()
        except (AccessError, ValidationError) as error:
            return request.redirect(f"{redirect_url}?error={quote_plus(str(error))}")

        return request.redirect(
            f"{redirect_url}?success=Compliance+submission+sent+for+review"
        )