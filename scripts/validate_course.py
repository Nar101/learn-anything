#!/usr/bin/env python3
"""Validate a learn-anything v2 course runtime."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment failure
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


REQUIRED_FILES = (
    "00-course-outline.yaml",
    "00-source-manifest.yaml",
    "learner-state.yaml",
    "review-queue.yaml",
)

ROUTE_STATUSES = {"active", "provisional", "completed", "skipped"}
MATERIAL_STATUSES = {
    "not_generated",
    "draft",
    "source_checked",
    "fact_checked",
    "pedagogy_checked",
    "verified",
    "frozen",
    "invalidated",
    "legacy_prebuilt",
}
DELIVERY_STATUSES = {"not_started", "in_progress", "completed"}
MASTERY_STATUSES = {
    "unknown",
    "exposed",
    "guided",
    "independent",
    "transferable",
    "durable",
}
READY_PART_STATUSES = {
    "ready",
    "in_progress",
    "completed",
    "source_checked",
    "fact_checked",
    "pedagogy_checked",
    "verified",
    "frozen",
}
SOURCE_MODES = {"agent_researched", "source_bounded", "source_augmented"}
PASSED_REVIEW = {"passed", "complete", "completed"}
FIXED_OUTLINE_HEADINGS = ("核心教材", "正例与反例", "容易混淆的边界")
REQUIRED_GRADING_RULES = ("correct", "partially_correct", "incorrect", "ungradable")
REQUIRED_PREFLIGHT = (
    "target_node_is_explicit",
    "source_support_is_sufficient",
    "answer_or_rubric_frozen",
    "options_are_mutually_exclusive",
    "question_is_realistic",
    "learner_has_required_prerequisites",
)
REQUIRED_TEACHING_LAYERS = ("source_layer", "tutor_synthesis", "application_layer")
MASTERY_RANK = {
    "unknown": 0,
    "exposed": 1,
    "guided": 2,
    "independent": 3,
    "transferable": 4,
    "durable": 5,
}


def load_yaml(path: Path, errors: list[str]):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except Exception as exc:  # noqa: BLE001 - validator must collect all failures
        errors.append(f"YAML parse failed: {path}: {exc}")
        return None


def resolve(course_dir: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    return (course_dir / relative_path).resolve()


def markdown_frontmatter(text: str) -> dict:
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            data = yaml.safe_load(parts[1])
            return data if isinstance(data, dict) else {}
    return {}


def body_without_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def validate_longform(
    path: Path,
    errors: list[str],
    warnings: list[str],
    require_v4_protocol: bool = False,
) -> None:
    raw_text = path.read_text(encoding="utf-8")
    metadata = markdown_frontmatter(raw_text)
    text = body_without_frontmatter(raw_text)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    prose_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith(("#", "-", "*", ">", "|", "```"))
    ]
    table_lines = [line for line in text.splitlines() if line.lstrip().startswith("|")]

    if chinese_chars < 1200:
        warnings.append(
            f"Longform may be too thin ({chinese_chars} Chinese chars): {path}"
        )
    if len(prose_lines) < 12:
        errors.append(f"Material lacks sustained prose: {path}")
    if table_lines and len(table_lines) >= len(prose_lines):
        errors.append(f"Tables appear to replace explanation: {path}")
    if all(f"## {heading}" in text for heading in FIXED_OUTLINE_HEADINGS):
        errors.append(f"Fixed outline template detected instead of narrative: {path}")
    if "## 轮到你" not in text:
        errors.append(f"Missing active learner output: {path}")
    if "来源" not in text:
        errors.append(f"Missing source anchors or limits: {path}")
    if require_v4_protocol:
        navigation = metadata.get("navigation")
        if not isinstance(navigation, dict):
            errors.append(f"v4 material is missing navigation metadata: {path}")
        for layer in REQUIRED_TEACHING_LAYERS:
            if not isinstance(metadata.get(layer), dict):
                errors.append(f"v4 material is missing {layer} metadata: {path}")
        output_position = text.find("## 轮到你")
        for label in (
            "当前位置：",
            "本课总问题：",
            "上一段已经解决：",
            "这一段为什么接着学：",
            "原教材这一段主要讲：",
            "本段结束时你要能做到：",
        ):
            label_position = text.find(label)
            if label_position < 0:
                errors.append(f"v4 material is missing visible navigation {label}: {path}")
            elif output_position >= 0 and label_position > output_position:
                errors.append(f"v4 material shows {label} after learner task: {path}")


def validate_assessments(
    plan: dict,
    plan_path: Path,
    plan_version: int,
    errors: list[str],
) -> None:
    assessment_config = plan.get("assessment")
    if not isinstance(assessment_config, dict):
        if plan_version >= 3:
            errors.append("v3 lesson plan is missing assessment configuration")
        return

    assessment_path = resolve(plan_path.parent, assessment_config.get("path"))
    if not assessment_path or not assessment_path.is_file():
        errors.append("Assessment file is missing")
        return

    assessment_data = load_yaml(assessment_path, errors) or {}
    assessment_version = assessment_data.get("version", 1)
    assessments = assessment_data.get("assessments")
    if not isinstance(assessments, list) or not assessments:
        errors.append("Assessment file must contain a non-empty assessments list")
        return

    assessment_ids = [item.get("assessment_id") for item in assessments]
    if any(not assessment_id for assessment_id in assessment_ids):
        errors.append("Assessment is missing assessment_id")
    if len(assessment_ids) != len(set(assessment_ids)):
        errors.append("Duplicate assessment_id values")

    delivered_ids = set(assessment_config.get("delivered_assessment_ids") or [])
    pending_ids = set(assessment_config.get("pending_assessment_ids") or [])
    referenced_ids = delivered_ids | pending_ids
    missing_ids = referenced_ids - set(assessment_ids)
    for assessment_id in sorted(missing_ids):
        errors.append(f"Lesson plan references missing assessment: {assessment_id}")

    for item in assessments:
        assessment_id = item.get("assessment_id", "<missing>")
        for field in ("correct_answer", "rationale"):
            if not item.get(field):
                errors.append(f"{assessment_id}: missing {field}")
        if not isinstance(item.get("acceptable_variants"), list):
            errors.append(f"{assessment_id}: acceptable_variants must be a list")
        grading_rule = item.get("grading_rule")
        if not isinstance(grading_rule, dict):
            errors.append(f"{assessment_id}: grading_rule must be a mapping")
        else:
            for rule in REQUIRED_GRADING_RULES:
                if not isinstance(grading_rule.get(rule), list) or not grading_rule.get(rule):
                    errors.append(f"{assessment_id}: grading_rule.{rule} must be non-empty")

        if isinstance(assessment_version, int) and assessment_version >= 4:
            if not item.get("target_node_id"):
                errors.append(f"{assessment_id}: missing target_node_id")
            preflight = item.get("preflight")
            if not isinstance(preflight, dict):
                errors.append(f"{assessment_id}: missing preflight")
            else:
                for field in REQUIRED_PREFLIGHT:
                    if preflight.get(field) is not True:
                        errors.append(f"{assessment_id}: preflight.{field} must be true")
            if item.get("question_type") in {"multiple_choice", "single_choice"}:
                options = item.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    errors.append(f"{assessment_id}: closed question needs at least two options")
            invalidation = item.get("invalidation")
            if not isinstance(invalidation, dict):
                errors.append(f"{assessment_id}: missing invalidation record")
            elif invalidation.get("invalidated"):
                if not invalidation.get("reason_type") or not invalidation.get("reason"):
                    errors.append(f"{assessment_id}: invalidated assessment needs a reason")
                if not invalidation.get("prior_grading_withdrawn"):
                    errors.append(f"{assessment_id}: invalidated assessment must withdraw grading")
                if not invalidation.get("mastery_evidence_removed"):
                    errors.append(f"{assessment_id}: invalidated assessment must remove mastery evidence")

        if assessment_id in delivered_ids:
            if not item.get("frozen_before_delivery") or not item.get("frozen_at"):
                errors.append(f"{assessment_id}: delivered assessment was not frozen")
            status = str(item.get("status", ""))
            if not status.startswith("delivered"):
                errors.append(
                    f"{assessment_id}: delivered assessment has incompatible status {status!r}"
                )


def validate_course(course_dir: Path, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        if not (course_dir / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    if errors:
        return errors, warnings

    outline = load_yaml(course_dir / "00-course-outline.yaml", errors) or {}
    learner_state = load_yaml(course_dir / "learner-state.yaml", errors) or {}
    source_manifest = load_yaml(course_dir / "00-source-manifest.yaml", errors) or {}
    review_queue = load_yaml(course_dir / "review-queue.yaml", errors) or {}

    source_version = source_manifest.get("version", 1)
    if isinstance(source_version, int) and source_version >= 3:
        research = source_manifest.get("research")
        if not isinstance(research, dict):
            errors.append("v3 source manifest is missing research policy")
        elif research.get("source_mode") not in SOURCE_MODES:
            errors.append(
                f"v3 source manifest has invalid source_mode {research.get('source_mode')!r}"
            )
        if not isinstance(source_manifest.get("claim_source_matrix"), list):
            errors.append("v3 source manifest is missing claim_source_matrix")
        if not isinstance(source_manifest.get("review_log"), list):
            errors.append("v3 source manifest is missing review_log")

    lessons = outline.get("lessons") or []
    if not lessons:
        errors.append("Course outline has no lessons")
        return errors, warnings

    lesson_ids = [lesson.get("lesson_id") for lesson in lessons]
    if len(lesson_ids) != len(set(lesson_ids)):
        errors.append("Duplicate lesson_id values")

    active_lessons = [lesson for lesson in lessons if lesson.get("route_status") == "active"]
    if len(active_lessons) != 1:
        errors.append(f"Expected exactly one active lesson, found {len(active_lessons)}")

    for lesson in lessons:
        lesson_id = lesson.get("lesson_id", "<missing>")
        route_status = lesson.get("route_status")
        material_status = lesson.get("material_status")
        delivery_status = lesson.get("delivery_status")
        mastery_status = lesson.get("mastery_status")

        if route_status not in ROUTE_STATUSES:
            errors.append(f"{lesson_id}: invalid route_status {route_status!r}")
        if material_status not in MATERIAL_STATUSES:
            errors.append(f"{lesson_id}: invalid material_status {material_status!r}")
        if delivery_status not in DELIVERY_STATUSES:
            errors.append(f"{lesson_id}: invalid delivery_status {delivery_status!r}")
        if mastery_status not in MASTERY_STATUSES:
            errors.append(f"{lesson_id}: invalid mastery_status {mastery_status!r}")

        if route_status == "provisional" and material_status not in {
            "not_generated",
            "legacy_prebuilt",
        }:
            errors.append(
                f"{lesson_id}: provisional future lesson has generated material ({material_status})"
            )
        if (
            route_status == "provisional"
            and lesson.get("assessment_ids")
            and material_status != "legacy_prebuilt"
        ):
            errors.append(
                f"{lesson_id}: provisional future lesson has pre-generated assessments"
            )

        for prerequisite in lesson.get("prerequisites") or []:
            if prerequisite not in lesson_ids:
                errors.append(f"{lesson_id}: unknown prerequisite {prerequisite}")

    if active_lessons:
        active = active_lessons[0]
        plan_path = resolve(course_dir, active.get("lesson_plan_path"))
        if not plan_path or not plan_path.is_file():
            errors.append("Active lesson plan is missing")
        else:
            plan = load_yaml(plan_path, errors) or {}
            plan_version = plan.get("version", 1)
            if isinstance(plan_version, int) and plan_version >= 3:
                source_policy = plan.get("source_policy")
                if not isinstance(source_policy, dict):
                    errors.append("v3 lesson plan is missing source_policy")
                elif source_policy.get("mode") not in SOURCE_MODES:
                    errors.append(
                        f"v3 lesson plan has invalid source mode {source_policy.get('mode')!r}"
                    )
                cost_policy = plan.get("cost_policy")
                if not isinstance(cost_policy, dict):
                    errors.append("v3 lesson plan is missing cost_policy")
                else:
                    if cost_policy.get("max_research_workers", 1) > 1:
                        warnings.append(
                            "Cost policy uses more than one research worker; verify that fan-out reduces total cost"
                        )
                    if cost_policy.get("parallel_research"):
                        warnings.append(
                            "Parallel research is enabled; record why source partitions are independent"
                        )
                validate_assessments(plan, plan_path, plan_version, errors)
                if isinstance(plan_version, int) and plan_version >= 4:
                    teaching_layers = plan.get("teaching_layers")
                    if not isinstance(teaching_layers, dict):
                        errors.append("v4 lesson plan is missing teaching_layers")
                    else:
                        for layer in REQUIRED_TEACHING_LAYERS:
                            if not isinstance(teaching_layers.get(layer), dict):
                                errors.append(f"v4 lesson plan is missing teaching_layers.{layer}")
                    completion_gate = plan.get("lesson_completion_gate")
                    if not isinstance(completion_gate, dict):
                        errors.append("v4 lesson plan is missing lesson_completion_gate")
                    elif completion_gate.get("next_lesson_generation_allowed"):
                        for field in (
                            "immediate_review_completed",
                            "retrieval_before_summary",
                            "transfer_task_completed",
                            "core_nodes_ready",
                        ):
                            if completion_gate.get(field) is not True:
                                errors.append(
                                    "v4 lesson gate allows next lesson without " + field
                                )
            parts = plan.get("parts") or []
            # Completed parts are historical evidence, not simultaneously active output.
            # Keep validating their material below, but exclude them from the
            # current-part-only concurrency check so a course can advance normally.
            current_ready_parts = [
                part
                for part in parts
                if part.get("status") in READY_PART_STATUSES
                and part.get("status") != "completed"
            ]
            if not parts:
                errors.append("Active lesson plan has no parts")
            if len(current_ready_parts) > 1:
                errors.append(
                    "More than one non-completed learning part generated/ready "
                    f"({len(current_ready_parts)}); expected current part only"
                )
            for part in parts:
                material_path = part.get("material_path")
                if part.get("status") in READY_PART_STATUSES:
                    if isinstance(plan_version, int) and plan_version >= 3:
                        status = part.get("status")
                        review = part.get("review") or {}
                        required_checks: list[str] = []
                        if status in {
                            "source_checked",
                            "fact_checked",
                            "pedagogy_checked",
                            "frozen",
                        }:
                            required_checks.append("source_check")
                        if status in {"fact_checked", "pedagogy_checked", "frozen"}:
                            required_checks.append("fact_check")
                        if status in {"pedagogy_checked", "frozen"}:
                            required_checks.append("pedagogy_check")
                        if status == "verified":
                            errors.append(
                                f"{part.get('part_id')}: v3 plan must use detailed review states instead of verified"
                            )
                        for check in required_checks:
                            if review.get(check) not in PASSED_REVIEW:
                                errors.append(
                                    f"{part.get('part_id')}: {status} requires {check}=passed"
                                )
                    if isinstance(plan_version, int) and plan_version >= 4:
                        navigation = part.get("navigation")
                        if not isinstance(navigation, dict):
                            errors.append(f"{part.get('part_id')}: missing navigation")
                        else:
                            for field in (
                                "position",
                                "lesson_question",
                                "previous_part_resolved",
                                "why_this_part_now",
                                "source_focus",
                                "success_criterion",
                            ):
                                if not navigation.get(field):
                                    errors.append(
                                        f"{part.get('part_id')}: navigation.{field} is empty"
                                    )
                        for layer in REQUIRED_TEACHING_LAYERS:
                            if not isinstance(part.get(layer), dict):
                                errors.append(f"{part.get('part_id')}: missing {layer}")
                    resolved = resolve(plan_path.parent, material_path)
                    if not resolved or not resolved.is_file():
                        errors.append(f"Ready part material is missing: {part.get('part_id')}")
                    else:
                        validate_longform(
                            resolved,
                            errors,
                            warnings,
                            require_v4_protocol=isinstance(plan_version, int)
                            and plan_version >= 4,
                        )
                elif material_path:
                    warnings.append(
                        f"Ungenerated part already has material_path: {part.get('part_id')}"
                    )

            user_notes = plan_path.parent / "02-user-notes.md"
            tutor_summary = plan_path.parent / "03-tutor-summary.md"
            if not user_notes.is_file():
                errors.append("Active lesson is missing 02-user-notes.md")
            if not tutor_summary.is_file():
                errors.append("Active lesson is missing 03-tutor-summary.md")
            if user_notes.resolve() == tutor_summary.resolve():
                errors.append("User notes and tutor summary must be separate files")

    if isinstance(source_version, int) and source_version >= 3:
        if not (course_dir / "课程入口.md").is_file():
            errors.append("v3 course is missing 课程入口.md")

    content_progress = learner_state.get("content_progress")
    if not isinstance(content_progress, dict):
        errors.append("learner-state.yaml is missing separate content_progress")
    if not learner_state.get("nodes"):
        errors.append("learner-state.yaml is missing mastery nodes")

    learner_version = learner_state.get("version", 1)
    if isinstance(learner_version, int) and learner_version >= 3:
        for node in learner_state.get("nodes") or []:
            node_id = node.get("id", "<missing>")
            for field in (
                "historical_highest_status",
                "current_status",
                "current_evidence",
                "active_misconceptions",
                "promotion_blockers",
                "advance_allowed",
            ):
                if field not in node:
                    errors.append(f"{node_id}: missing {field}")
            historical = node.get("historical_highest_status")
            current = node.get("current_status")
            if historical not in MASTERY_STATUSES:
                errors.append(f"{node_id}: invalid historical_highest_status {historical!r}")
            if current not in MASTERY_STATUSES:
                errors.append(f"{node_id}: invalid current_status {current!r}")
            if historical in MASTERY_RANK and current in MASTERY_RANK:
                if MASTERY_RANK[historical] < MASTERY_RANK[current]:
                    errors.append(f"{node_id}: historical status is below current status")
            if node.get("advance_allowed") and current in {"unknown", "exposed", "guided"}:
                errors.append(f"{node_id}: advance allowed before independent mastery")

        evidence_log = learner_state.get("evidence_log")
        if not isinstance(evidence_log, list):
            errors.append("v3 learner state is missing evidence_log")
        else:
            for entry in evidence_log:
                promotion = entry.get("promotion_evidence")
                if not isinstance(promotion, dict):
                    errors.append("evidence log entry is missing promotion_evidence")
                    continue
                required = (
                    "grading_result",
                    "criteria_met",
                    "criteria_unmet",
                    "active_misconceptions",
                    "historical_highest_status",
                    "current_status",
                    "advance_allowed",
                    "promotion_blockers",
                )
                for field in required:
                    if field not in promotion:
                        errors.append(f"promotion_evidence is missing {field}")
                hint_level = entry.get("hint_level")
                promoted_to = (entry.get("mastery_change") or {}).get("to")
                if hint_level in {1, 2, 3, 4, "L1", "L2", "L3", "L4"} and promoted_to in {
                    "independent",
                    "transferable",
                    "durable",
                }:
                    errors.append("hinted evidence cannot promote beyond guided")
                if hint_level in {5, "L5"} and promoted_to in {
                    "guided",
                    "independent",
                    "transferable",
                    "durable",
                }:
                    errors.append("L5 demonstrated task cannot promote beyond exposed")

        if review_queue.get("version", 1) >= 2:
            immediate_reviews = review_queue.get("immediate_reviews")
            if not isinstance(immediate_reviews, list) or not immediate_reviews:
                errors.append("v2 review queue is missing immediate_reviews")
            else:
                for review in immediate_reviews:
                    if review.get("review_type") != "immediate":
                        errors.append("immediate review has wrong review_type")
                    if review.get("retrieval_before_summary") is not True:
                        errors.append("immediate review must retrieve before summary")
                    if review.get("next_action") not in {"reinforce", "continue", "pause"}:
                        errors.append("immediate review has invalid next_action")

        active_plan_gate = None
        if active_lessons:
            active_plan_path = resolve(course_dir, active_lessons[0].get("lesson_plan_path"))
            if active_plan_path and active_plan_path.is_file():
                active_plan = load_yaml(active_plan_path, errors) or {}
                active_plan_gate = active_plan.get("lesson_completion_gate")
        if isinstance(active_plan_gate, dict) and active_plan_gate.get(
            "next_lesson_generation_allowed"
        ):
            core_nodes = [
                node
                for node in learner_state.get("nodes") or []
                if node.get("importance", "core") == "core"
            ]
            if any(node.get("advance_allowed") is not True for node in core_nodes):
                errors.append("next lesson allowed while a core node is blocked")
            completed_immediate = [
                review
                for review in review_queue.get("immediate_reviews") or []
                if review.get("review_type") == "immediate"
                and review.get("result") not in {None, "", "not_attempted"}
                and review.get("next_action") == "continue"
                and review.get("completed_at")
            ]
            if not completed_immediate:
                errors.append("next lesson allowed without completed immediate review evidence")

    if strict and warnings:
        errors.extend(f"Strict mode: {warning}" for warning in warnings)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_dir", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    course_dir = args.course_dir.expanduser().resolve()
    errors, warnings = validate_course(course_dir, args.strict)

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    print(f"PASS: course runtime valid ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
