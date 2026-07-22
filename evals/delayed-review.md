# Eval 05｜跨会话延迟复习

## 测试目标

验证 Skill 是否能读取已有学习状态，以主动提取开始复习，根据延迟表现更新状态，而不是重新讲课或假装记得不存在的进度。

## 已有状态

```yaml
mastery_contract:
  learning_goal: 区分相关性与因果性，并能审查日常因果主张
  target_mastery_level: durable
nodes:
  - id: correlation-causation
    name: 相关性与因果性
    knowledge_type: concept
    status: independent
    evidence:
      - 三天前独立解释了共同原因可能制造相关性
    misconceptions:
      - description: 只要 A 先于 B 且二者相关，就能证明 A 导致 B
        status: corrected_but_fragile
    last_practiced: 2026-07-09
    next_review: 2026-07-12
review:
  due_now:
    - correlation-causation
```

## 初始 Prompt

> 继续上次学的相关性和因果性。

## 预期首轮行为

必须：

1. 复用已有目标和节点，不重新问“你想学什么”；
2. 不先展示上次总结或定义；
3. 直接给一个短回忆或新案例，例如“冰淇淋销量和溺水人数同时上升，能否说明前者导致后者，为什么”；
4. 可先让用户给信心评分；
5. 明确这是到期复习，不是新章节。

## 用户回答

> 两者相关，而且冰淇淋销量先上升，所以应该能说明冰淇淋导致溺水增加。我有 80% 把握。

## 预期反馈与状态更新

必须：

1. 判定核心误区复发，不能因为表达完整就判为正确；
2. 指出时间先后与相关性仍不足以排除共同原因；
3. 用“高温同时影响冰淇淋销量和游泳人数”作为最小反例或提示；
4. 要求用户重新解释，而不是立即完整重讲整章；
5. 将状态从 `independent` 下调为 `guided` 或标记待巩固；
6. 保留历史最高证据，同时记录本次延迟失败；
7. 将误区重新标记为 active；
8. 安排更近的复习，例如 1 天后；
9. 不授予 `durable`。

## 若用户修正成功

预期：

- 说明本次是在提示后修正，所以仍不能恢复为 `independent`；
- 再给一个不同表面形式的小案例；
- 新案例独立成功后可恢复 `independent`，但长期保持仍需下一次延迟确认。

## 状态更新示例

```yaml
status: guided
previous_highest_status: independent
downgrade_reason: delayed_retrieval_failure
misconception:
  description: 时间先后与相关性足以证明因果
  status: active
next_review: 1_day_later
durable_mastery_verified: false
```

## 没有状态文件时

Skill 必须说明当前只能根据可见对话恢复，不能假装已经读取历史状态。可用一个回忆任务重新定位。

## 评分重点

- 跨会话状态复用；
- 复习先提取；
- 高自信错误处理；
- 状态下调；
- 复习排期；
- durable 证据纪律。

## Critical Fail

- 复习开始先展示旧答案；
- 重新询问已经存在的学习目标；
- 将错误答案判为正确；
- 提示后修正立即标回 `durable`；
- 删除旧证据而不保留历史；
- 假装读取了不存在的状态。

## 通过标准

按 `tutor-quality-rubric.md` 的适用维度换算得分 ≥ 80，且无 Critical Fail。
