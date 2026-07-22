#!/usr/bin/env python3
"""Regression tests for learn-anything course runtime validation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml


VALIDATOR_PATH = Path(__file__).with_name("validate_course.py")
SPEC = importlib.util.spec_from_file_location("validate_course", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def valid_course_data() -> dict[str, dict]:
    outline = {
        "version": 4,
        "lessons": [
            {
                "lesson_id": "L01",
                "prerequisites": [],
                "lesson_plan_path": "lessons/L01/00-lesson-plan.yaml",
                "assessment_ids": ["A-L01-01"],
                "route_status": "active",
                "material_status": "not_generated",
                "delivery_status": "not_started",
                "mastery_status": "unknown",
            },
            {
                "lesson_id": "L02",
                "prerequisites": ["L01"],
                "lesson_plan_path": None,
                "assessment_ids": [],
                "route_status": "provisional",
                "material_status": "not_generated",
                "delivery_status": "not_started",
                "mastery_status": "unknown",
            },
        ],
    }
    source_manifest = {
        "version": 3,
        "research": {"source_mode": "source_bounded"},
        "claim_source_matrix": [],
        "review_log": [],
    }
    learner_state = {
        "version": 3,
        "content_progress": {"current_lesson_id": "L01", "current_part_id": "L01-P01"},
        "nodes": [
            {
                "id": "node-001",
                "historical_highest_status": "unknown",
                "current_status": "unknown",
                "current_evidence": [],
                "active_misconceptions": [],
                "promotion_blockers": ["representative task not attempted"],
                "advance_allowed": False,
            }
        ],
        "evidence_log": [],
    }
    review_queue = {
        "version": 2,
        "immediate_reviews": [
            {
                "id": "immediate-L01",
                "lesson_id": "L01",
                "review_type": "immediate",
                "retrieval_before_summary": True,
                "transfer_task": "new scenario",
                "result": "not_attempted",
                "misconceptions_reactivated": [],
                "next_action": "reinforce",
            }
        ],
    }
    plan = {
        "version": 4,
        "source_policy": {"mode": "source_bounded"},
        "cost_policy": {"max_research_workers": 1, "parallel_research": False},
        "teaching_layers": {
            "source_layer": {},
            "tutor_synthesis": {},
            "application_layer": {},
        },
        "parts": [
            {
                "part_id": "L01-P01",
                "status": "planned",
                "material_path": None,
                "navigation": {
                    "position": "L01-P01 / 当前课第 1 段",
                    "lesson_question": "核心问题",
                    "previous_part_resolved": "这是本课起点",
                    "why_this_part_now": "先建立前置判断",
                    "source_focus": "原教材当前主张",
                    "success_criterion": "能独立解释核心关系",
                },
                "source_layer": {},
                "tutor_synthesis": {},
                "application_layer": {},
            }
        ],
        "assessment": {
            "path": "../../assessments/01.yaml",
            "delivered_assessment_ids": [],
            "pending_assessment_ids": ["A-L01-01"],
        },
        "lesson_completion_gate": {
            "immediate_review_completed": False,
            "retrieval_before_summary": True,
            "transfer_task_completed": False,
            "core_nodes_ready": False,
            "next_lesson_generation_allowed": False,
            "blockers": ["lesson not complete"],
        },
    }
    assessment = {
        "version": 4,
        "assessments": [
            {
                "assessment_id": "A-L01-01",
                "target_node_id": "node-001",
                "question_type": "open_response",
                "question": "请解释核心关系。",
                "correct_answer": "按冻结 rubric 判断",
                "acceptable_variants": [],
                "rationale": "测量当前节点",
                "grading_rule": {
                    "correct": ["核心关系与依据均正确"],
                    "partially_correct": ["结论正确但依据不完整"],
                    "incorrect": ["核心关系错误"],
                    "ungradable": ["题目或标准不足"],
                },
                "preflight": {
                    "target_node_is_explicit": True,
                    "source_support_is_sufficient": True,
                    "answer_or_rubric_frozen": True,
                    "options_are_mutually_exclusive": True,
                    "question_is_realistic": True,
                    "learner_has_required_prerequisites": True,
                },
                "invalidation": {
                    "invalidated": False,
                    "reason_type": None,
                    "reason": "",
                    "prior_grading_withdrawn": False,
                    "mastery_evidence_removed": False,
                    "replacement_assessment_id": None,
                },
                "frozen_before_delivery": True,
                "frozen_at": "2026-07-22T00:00:00+08:00",
                "status": "frozen",
            }
        ],
    }
    return {
        "00-course-outline.yaml": outline,
        "00-source-manifest.yaml": source_manifest,
        "learner-state.yaml": learner_state,
        "review-queue.yaml": review_queue,
        "lessons/L01/00-lesson-plan.yaml": plan,
        "assessments/01.yaml": assessment,
    }


def build_course(root: Path, overrides: dict[str, dict] | None = None) -> Path:
    data = valid_course_data()
    for path, value in (overrides or {}).items():
        data[path] = value
    for relative, value in data.items():
        write_yaml(root / relative, value)
    (root / "课程入口.md").write_text("# 课程入口\n", encoding="utf-8")
    lesson_dir = root / "lessons/L01"
    (lesson_dir / "02-user-notes.md").write_text("# 用户笔记\n", encoding="utf-8")
    (lesson_dir / "03-tutor-summary.md").write_text("# Tutor 总结\n", encoding="utf-8")
    return root


class ValidateCourseV4Tests(unittest.TestCase):
    def validate(self, overrides: dict[str, dict] | None = None) -> list[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            course = build_course(Path(temp_dir), overrides)
            errors, _warnings = VALIDATOR.validate_course(course, strict=False)
            return errors

    def test_valid_v4_course_passes(self) -> None:
        self.assertEqual(self.validate(), [])

    def test_assessment_preflight_failure_is_blocked(self) -> None:
        assessment = deepcopy(valid_course_data()["assessments/01.yaml"])
        assessment["assessments"][0]["preflight"]["options_are_mutually_exclusive"] = False
        errors = self.validate({"assessments/01.yaml": assessment})
        self.assertTrue(any("preflight.options_are_mutually_exclusive" in error for error in errors))

    def test_hinted_attempt_cannot_promote_to_independent(self) -> None:
        learner = deepcopy(valid_course_data()["learner-state.yaml"])
        learner["evidence_log"] = [
            {
                "node_id": "node-001",
                "hint_level": "L4",
                "mastery_change": {"from": "guided", "to": "independent"},
                "promotion_evidence": {
                    "grading_result": "correct",
                    "criteria_met": ["final answer"],
                    "criteria_unmet": ["independent evidence"],
                    "active_misconceptions": [],
                    "historical_highest_status": "guided",
                    "current_status": "guided",
                    "advance_allowed": False,
                    "promotion_blockers": ["L4 hint used"],
                },
            }
        ]
        errors = self.validate({"learner-state.yaml": learner})
        self.assertIn("hinted evidence cannot promote beyond guided", errors)

    def test_next_lesson_requires_immediate_review_and_transfer(self) -> None:
        plan = deepcopy(valid_course_data()["lessons/L01/00-lesson-plan.yaml"])
        plan["lesson_completion_gate"]["next_lesson_generation_allowed"] = True
        errors = self.validate({"lessons/L01/00-lesson-plan.yaml": plan})
        self.assertTrue(any("allows next lesson" in error for error in errors))

    def test_next_lesson_requires_cross_file_review_evidence(self) -> None:
        data = valid_course_data()
        plan = deepcopy(data["lessons/L01/00-lesson-plan.yaml"])
        plan["lesson_completion_gate"].update(
            {
                "immediate_review_completed": True,
                "transfer_task_completed": True,
                "core_nodes_ready": True,
                "next_lesson_generation_allowed": True,
            }
        )
        learner = deepcopy(data["learner-state.yaml"])
        learner["nodes"][0].update(
            {
                "historical_highest_status": "independent",
                "current_status": "independent",
                "advance_allowed": True,
                "promotion_blockers": [],
            }
        )
        errors = self.validate(
            {
                "lessons/L01/00-lesson-plan.yaml": plan,
                "learner-state.yaml": learner,
            }
        )
        self.assertIn("next lesson allowed without completed immediate review evidence", errors)


if __name__ == "__main__":
    unittest.main()
