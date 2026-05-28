from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.models.script import Script, ComplianceReport, ScriptResponse
from backend.features.yt_shorts.services.script import generate_script
from backend.features.yt_shorts.services.compliance import check_compliance

router = APIRouter(tags=["yt-shorts-script"])


@router.post("/generate", response_model=ScriptResponse)
def generate_script_endpoint(
    project_id: str,
    store: ProjectStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    approved_topic = project.get("approved_topic")
    if not approved_topic:
        raise HTTPException(status_code=400, detail="No approved topic. Approve a topic first.")

    script, claude_compliance = generate_script(
        api_key=settings.anthropic_api_key,
        topic_title=approved_topic["title"],
        misconception=approved_topic["misconception"],
    )
    compliance = check_compliance(
        script,
        sensitive_content=claude_compliance.get("sensitive_content", "CLEAR"),
        sensitive_content_details=claude_compliance.get("sensitive_content_details"),
        revision_notes=claude_compliance.get("revision_notes"),
    )
    store.update(project_id, {
        "script_draft": script.model_dump(),
        "compliance_report": compliance.model_dump(),
    })
    return ScriptResponse(script=script, compliance=compliance)


@router.get("", response_model=ScriptResponse)
def get_script(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    compliance_dict = project.get("compliance_report")
    script = Script(**script_dict) if script_dict else None
    compliance = ComplianceReport(**compliance_dict) if compliance_dict else None
    return ScriptResponse(script=script, compliance=compliance)


@router.post("/compliance", response_model=ComplianceReport)
def run_compliance(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    if not script_dict:
        raise HTTPException(status_code=400, detail="No script draft. Generate script first.")

    script = Script(**script_dict)
    compliance = check_compliance(script)
    store.update(project_id, {"compliance_report": compliance.model_dump()})
    return compliance


@router.post("/approve", response_model=Script)
def approve_script(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    if not script_dict:
        raise HTTPException(status_code=400, detail="No script draft. Generate script first.")

    script_dict["status"] = "approved"
    store.update(project_id, {
        "script_draft": script_dict,
        "current_step": "voiceover",
    })
    return Script(**script_dict)
