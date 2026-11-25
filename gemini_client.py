"""Gemini integration: upload a video, wait until ACTIVE, extract JSON analysis.

Uses the current `google-genai` SDK (NOT the deprecated `google-generativeai`).
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

import config

log = logging.getLogger(__name__)

NOT_MENTIONED = "Not mentioned in the video."


class ConfigError(RuntimeError):
    """Missing/invalid configuration (e.g. API key not set)."""


class GeminiProcessingError(RuntimeError):
    """Gemini failed to process the file or returned unusable output."""


# --- Response schema ----------------------------------------------------------
class CompanyInfo(BaseModel):
    company_name: str = Field(default="Not mentioned", description="Exact company name mentioned or implied")
    award_category: str = Field(default="Not mentioned", description="Award category nominated, e.g. Best Company to Work For – Medium")
    awards_edition: str = Field(default="Employee Happiness Awards UAE 2026", description="Awards edition")
    industry: str = Field(default="Not specified", description="Industry or sector, e.g. Real Estate, Retail, IT Services")
    employee_headcount: str = Field(default="Not specified", description="Employee headcount / company size")
    year_of_establishment: str = Field(default="Not specified", description="Year company was established")
    presenter_name_and_designation: str = Field(default="Not specified", description="Presenter name and designation/job title")


class PillarAnalysisItem(BaseModel):
    pillar_name: str = Field(description="Name of the employee lifecycle pillar, e.g. Attraction & Onboarding, Learning & Growth, Well-being, Leadership & Strategy, Culture, Retention & Exit")
    initiatives_and_practices: str = Field(description="Evidence-based analysis of the initiatives, programmes, leadership involvement, employee feedback mechanisms, and policies presented under this pillar")
    supporting_evidence: str = Field(default="", description="Specific supporting evidence citing presentation slides or verbal discussion highlights without raw timestamps")


class MeasurableOutcome(BaseModel):
    metric_name: str = Field(description="Name of metric or KPI, e.g. Employee Retention Rate, eNPS, Training Hours")
    baseline_or_previous: str = Field(default="Not stated", description="Baseline, previous figure, or target benchmark")
    achieved_result: str = Field(description="Achieved outcome or current metric figure")
    context_and_significance: str = Field(default="", description="What the result demonstrates in relation to the initiatives")


class KeyFindingsAndImpact(BaseModel):
    measurable_outcomes: list[MeasurableOutcome] = Field(default_factory=list, description="Measurable outcomes and comparative metrics")
    survey_and_qualitative_feedback: str = Field(default="", description="Employee survey results, satisfaction levels, and qualitative testimonials")
    progress_against_objectives: str = Field(default="", description="Progress against stated targets (organisation-reported findings)")


class JuryObservation(BaseModel):
    jury_topic_or_question: str = Field(description="Key question, challenge, or topic raised by the jury during Q&A")
    organisation_response: str = Field(default="", description="How the presenter addressed the question")
    key_observation: str = Field(default="", description="Jury observation or area where additional evidence was discussed")


class FeedbackAndNextSteps(BaseModel):
    jury_observations: list[JuryObservation] = Field(default_factory=list, description="Explicit jury observations and Q&A findings")
    presentation_evidence_gaps: list[str] = Field(default_factory=list, description="Areas where additional data or evidence could strengthen the presentation")
    ai_recommendations_and_sustainability: list[str] = Field(default_factory=list, description="Constructive AI-generated recommendations and sustainability next steps")


class EHAReportAnalysis(BaseModel):
    company_info: CompanyInfo = Field(default_factory=CompanyInfo)
    executive_overview: str = Field(description="Executive narrative introducing presentation rationale, objectives, execution approach, and jury Q&A context")
    pillars_analysis: list[PillarAnalysisItem] = Field(default_factory=list, description="Pillar-by-pillar analysis of initiatives and practices")
    key_findings_and_impact: KeyFindingsAndImpact = Field(default_factory=KeyFindingsAndImpact)
    feedback_and_next_steps: FeedbackAndNextSteps = Field(default_factory=FeedbackAndNextSteps)
    conclusion: str = Field(description="Executive conclusion summarizing key strengths, achievements, and lifecycle pillar alignment")
    transcript: str = Field(default="", description="Full verbatim transcript with speaker labels")


# Legacy compatibility schema
class TimelineSegment(BaseModel):
    timestamp_range: str = Field(description="e.g. '00:00 - 05:10'")
    topic: str = Field(description="Topic discussed in this segment")
    has_slides: bool = Field(default=False, description="Whether presentation slides or screen shares are visible")


class QAItem(BaseModel):
    question: str = Field(description="The question, copied verbatim.")
    answer: str = Field(description="Concise answer synthesized from spoken dialogue and on-screen slides.")
    reasoning: str = Field(description="Evidence citing visual slides and spoken quotes.")
    timestamp: str = Field(default="", description="Relevant timestamp range in the video, e.g. '05:10 - 08:30'.")


class VideoAnalysis(BaseModel):
    company_name: str = Field(description="Company name mentioned or implied, or 'Not mentioned'.")
    company_category: str = Field(default="Not mentioned", description="Industry or category of the company.")
    video_duration: str = Field(default="Not available", description="Approximate video length as mm:ss.")
    language: str = Field(default="Not available", description="Main language(s) spoken.")
    summary: str = Field(default="", description="Neutral overview of the video.")
    timeline: list[TimelineSegment] = Field(default_factory=list)
    transcript: str = Field(default="", description="Full verbatim transcript.")
    qa: list[QAItem] = Field(default_factory=list)


PROMPT_FILE = config.BASE_DIR / "gemini_prompt_file.txt"


def build_prompt() -> str:
    """Load prompt template from file, or fall back to internal default."""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return "You are an expert evaluator for the Employee Happiness Awards. Analyze the presentation video and return EHAReportAnalysis JSON."


# --- Client / file handling ----------------------------------------------------
_CLIENT: genai.Client | None = None


def get_client() -> genai.Client:
    """Return one shared client with bounded HTTP timeouts."""
    global _CLIENT
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY.startswith("paste-"):
        raise ConfigError("GEMINI_API_KEY is not set. Add it to the .env file (see .env.example).")
    if _CLIENT is None:
        _CLIENT = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(client_args={"timeout": 60.0}),
        )
    return _CLIENT


def _state_name(file_obj: Any) -> str:
    state = getattr(file_obj, "state", None)
    if state is None:
        return "STATE_UNSPECIFIED"
    return str(getattr(state, "name", state)).upper().replace("FILESTATE.", "")


def upload_and_wait(client: genai.Client, path: Path, ref: dict) -> Any:
    """Upload `path` via the File API and block until it is ACTIVE.

    `ref["name"]` is set as soon as the upload succeeds so the caller can delete
    the remote file in a `finally` block even if a later step fails.
    """
    mime = config.VIDEO_MIME_TYPES.get(path.suffix.lower(), "video/mp4")
    log.info("Uploading %s to Gemini File API (%s)...", path.name, mime)
    file_obj = client.files.upload(file=str(path), config=types.UploadFileConfig(mime_type=mime))
    ref["name"] = file_obj.name
    log.info("Uploaded as %s; waiting for processing...", file_obj.name)

    deadline = time.monotonic() + config.FILE_PROCESSING_TIMEOUT_S
    while True:
        state = _state_name(file_obj)
        if state == "ACTIVE":
            log.info("File is ACTIVE.")
            return file_obj
        if state == "FAILED":
            raise GeminiProcessingError(f"Gemini failed to process the video: {getattr(file_obj, 'error', None)}")
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"Video was not ready after {config.FILE_PROCESSING_TIMEOUT_S}s (last state: {state})."
            )
        time.sleep(config.POLL_INTERVAL_S)
        file_obj = client.files.get(name=file_obj.name)


def delete_remote_file(name: str | None) -> None:
    if not name:
        return
    try:
        get_client().files.delete(name=name)
        log.info("Deleted Gemini file %s", name)
    except Exception as exc:  # cleanup must never raise
        log.warning("Could not delete Gemini file %s: %s", name, exc)


# --- JSON parsing ----------------------------------------------------------------
_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)\s*```", re.DOTALL)


def parse_model_json(text: str) -> dict:
    """Parse the model's JSON robustly (handles ```json fences / stray prose)."""
    if not text or not text.strip():
        raise GeminiProcessingError("Gemini returned an empty response.")
    candidates = [text.strip()]
    candidates += [m.group(1) for m in _FENCE_RE.finditer(text)]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise GeminiProcessingError(f"Could not parse JSON from Gemini response: {text[:300]!r}")


def normalize_analysis(data: dict) -> dict:
    """Normalize and validate arbitrary model output into the EHA 6-section analysis format."""
    def _clean(val: Any, default: str = "") -> str:
        s = str(val or "").strip()
        return s if s else default

    raw_comp = data.get("company_info") or {}
    if not isinstance(raw_comp, dict):
        raw_comp = {}

    company_name = _clean(raw_comp.get("company_name") or data.get("company_name"), "Not mentioned")
    award_category = _clean(raw_comp.get("award_category") or data.get("company_category"), "Not mentioned")
    awards_edition = _clean(raw_comp.get("awards_edition"), config.DEFAULT_AWARDS_EDITION)
    industry = _clean(raw_comp.get("industry"), "Not specified")
    employee_headcount = _clean(raw_comp.get("employee_headcount"), "Not specified")
    year_of_establishment = _clean(raw_comp.get("year_of_establishment"), "Not specified")
    presenter_name_and_designation = _clean(raw_comp.get("presenter_name_and_designation"), "Not specified")

    company_info = {
        "company_name": company_name,
        "award_category": award_category,
        "awards_edition": awards_edition,
        "industry": industry,
        "employee_headcount": employee_headcount,
        "year_of_establishment": year_of_establishment,
        "presenter_name_and_designation": presenter_name_and_designation,
    }

    # Section 2: Executive Overview
    executive_overview = _clean(data.get("executive_overview") or data.get("summary"))

    # Section 3: Employee Initiatives & Practices (Pillar-wise)
    raw_pillars = data.get("pillars_analysis") or []
    pillars_analysis = []
    if isinstance(raw_pillars, list):
        for p in raw_pillars:
            if isinstance(p, dict):
                p_name = _clean(p.get("pillar_name"))
                p_init = _clean(p.get("initiatives_and_practices"))
                p_evid = _clean(p.get("supporting_evidence"))
                if p_name and p_init:
                    pillars_analysis.append({
                        "pillar_name": p_name,
                        "initiatives_and_practices": p_init,
                        "supporting_evidence": p_evid,
                    })

    # If no structured pillars were parsed, fall back to extracting from legacy QA if present
    if not pillars_analysis and data.get("qa"):
        for q_item in data.get("qa", []):
            if isinstance(q_item, dict):
                q_text = str(q_item.get("question") or "")
                topic = q_text.split(":")[0].strip() if ":" in q_text else q_text[:30]
                pillars_analysis.append({
                    "pillar_name": topic,
                    "initiatives_and_practices": _clean(q_item.get("answer")),
                    "supporting_evidence": _clean(q_item.get("reasoning")),
                })

    # Section 4: Key Findings & Impact
    raw_impact = data.get("key_findings_and_impact") or {}
    if not isinstance(raw_impact, dict):
        raw_impact = {}

    measurable_outcomes = []
    for mo in raw_impact.get("measurable_outcomes") or []:
        if isinstance(mo, dict):
            m_name = _clean(mo.get("metric_name"))
            if m_name:
                measurable_outcomes.append({
                    "metric_name": m_name,
                    "baseline_or_previous": _clean(mo.get("baseline_or_previous"), "Not stated"),
                    "achieved_result": _clean(mo.get("achieved_result"), "Demonstrated"),
                    "context_and_significance": _clean(mo.get("context_and_significance")),
                })

    key_findings_and_impact = {
        "measurable_outcomes": measurable_outcomes,
        "survey_and_qualitative_feedback": _clean(raw_impact.get("survey_and_qualitative_feedback")),
        "progress_against_objectives": _clean(raw_impact.get("progress_against_objectives")),
    }

    # Section 5: Feedback & Next Steps
    raw_fb = data.get("feedback_and_next_steps") or {}
    if not isinstance(raw_fb, dict):
        raw_fb = {}

    jury_observations = []
    for jo in raw_fb.get("jury_observations") or []:
        if isinstance(jo, dict):
            j_q = _clean(jo.get("jury_topic_or_question"))
            if j_q:
                jury_observations.append({
                    "jury_topic_or_question": j_q,
                    "organisation_response": _clean(jo.get("organisation_response")),
                    "key_observation": _clean(jo.get("key_observation")),
                })

    presentation_evidence_gaps = [
        _clean(g) for g in raw_fb.get("presentation_evidence_gaps") or [] if _clean(g)
    ]
    ai_recommendations = [
        _clean(r) for r in raw_fb.get("ai_recommendations_and_sustainability") or [] if _clean(r)
    ]

    feedback_and_next_steps = {
        "jury_observations": jury_observations,
        "presentation_evidence_gaps": presentation_evidence_gaps,
        "ai_recommendations_and_sustainability": ai_recommendations,
    }

    # Section 6: Conclusion
    conclusion = _clean(data.get("conclusion"))

    # Transcript
    transcript = _clean(data.get("transcript"), "[No transcript returned]")

    # Legacy QA synthesis for older consumers
    qa = []
    for p in pillars_analysis:
        qa.append({
            "question": f"Pillar: {p['pillar_name']}",
            "answer": p["initiatives_and_practices"],
            "reasoning": p["supporting_evidence"],
            "timestamp": "",
        })

    return {
        "company_info": company_info,
        "executive_overview": executive_overview,
        "pillars_analysis": pillars_analysis,
        "key_findings_and_impact": key_findings_and_impact,
        "feedback_and_next_steps": feedback_and_next_steps,
        "conclusion": conclusion,
        "transcript": transcript,
        # Top-level legacy aliases for maximum backward compatibility
        "company_name": company_name,
        "company_category": award_category,
        "summary": executive_overview,
        "qa": qa,
        "timeline": data.get("timeline") or [],
        "video_duration": _clean(data.get("video_duration"), "Not available"),
        "language": _clean(data.get("language"), "Not available"),
    }


# --- Main entry point -----------------------------------------------------------
def analyze_video(path: Path, ref: dict) -> dict:
    """Upload the video, ask Gemini for transcript + answers, return parsed dict."""
    client = get_client()
    file_obj = upload_and_wait(client, path, ref)

    candidate_models = [config.GEMINI_MODEL]
    fallback = getattr(config, "GEMINI_FALLBACK_MODEL", "").strip()
    if fallback and fallback != config.GEMINI_MODEL:
        candidate_models.append(fallback)

    response = None
    used_model = config.GEMINI_MODEL
    last_err = None

    for m_idx, current_model in enumerate(candidate_models):
        has_fallback = (m_idx < len(candidate_models) - 1)
        max_attempts = 1 if has_fallback else 2

        log.info("Requesting analysis from %s (attempt limit: %d)...", current_model, max_attempts)

        model_succeeded = False
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=[file_obj, build_prompt()],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EHAReportAnalysis,
                        temperature=0.1,
                    ),
                )
                used_model = current_model
                model_succeeded = True
                log.info("Successfully received analysis from %s!", current_model)
                break
            except errors.APIError as e:
                last_err = e
                status_code = getattr(e, "code", None)
                err_msg = getattr(e, "message", str(e))
                is_transient = (status_code in (503, 429, 500) or "high demand" in err_msg.lower() or "unavailable" in err_msg.lower())
                if is_transient and has_fallback:
                    log.warning("Gemini %s is experiencing high demand (status %s). Switching immediately to fallback model %s...",
                                current_model, status_code, candidate_models[m_idx + 1])
                    break
                elif is_transient and attempt < max_attempts:
                    backoff = attempt * 3
                    log.warning("Gemini %s returned %s on attempt %d/%d ('%s'). Retrying in %ds...",
                                current_model, status_code, attempt, max_attempts, err_msg, backoff)
                    time.sleep(backoff)
                else:
                    if not has_fallback:
                        raise GeminiProcessingError(f"Gemini API error ({status_code}): {err_msg}") from e
                    break
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                is_transient = ("503" in err_str or "429" in err_str or "high demand" in err_str or "unavailable" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str)
                if is_transient and has_fallback:
                    log.warning("Gemini %s transient error / timeout (%s). Switching immediately to fallback model %s...",
                                current_model, e, candidate_models[m_idx + 1])
                    break
                elif is_transient and attempt < max_attempts:
                    backoff = attempt * 3
                    log.warning("Gemini transient error on attempt %d/%d (%s). Retrying in %ds...", attempt, max_attempts, e, backoff)
                    time.sleep(backoff)
                else:
                    if not has_fallback:
                        raise
                    break

        if model_succeeded:
            break

    if response is None:
        raise GeminiProcessingError(f"Gemini analysis failed across models ({', '.join(candidate_models)}): {last_err}")

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, (EHAReportAnalysis, VideoAnalysis)):
        data = parsed.model_dump()
    else:
        data = parse_model_json(response.text or "")
    analysis = normalize_analysis(data)
    analysis["model"] = used_model

    usage = getattr(response, "usage_metadata", None)
    if usage:
        analysis["usage"] = {
            "prompt_token_count": getattr(usage, "prompt_token_count", 0),
            "candidates_token_count": getattr(usage, "candidates_token_count", 0),
            "total_token_count": getattr(usage, "total_token_count", 0),
        }
    else:
        analysis["usage"] = {}
    return analysis
