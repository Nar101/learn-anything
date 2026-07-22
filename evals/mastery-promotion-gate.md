# Eval 13｜提示后完成与掌握升级闸门

## 测试目标

验证最后一次答对不会覆盖此前的提示依赖，也不会把 `guided` 错升为 `independent`。

## 已有表现

学习者连续三次混淆“商品是什么”和“商品是否有效”。Tutor 已给出 L2 判据和 L4 示例。随后学习者在相近题中答对“这里应该补使用证据”。

## 必须行为

- 本次判分可以为 `correct`，但提示历史使当前状态保持 `guided`；
- promotion evidence 记录 L4、已满足标准、仍待验证的独立辨别和活跃误区；
- `historical_highest_status` 与 `current_status` 分开保存；
- `advance_allowed: false`；
- 给一个不复用原措辞、答案不可见的代表性新场景，只有无关键提示完成且依据可靠才重新取得 `independent` 证据。

## Critical Fail

- 因最后一题答对直接宣布 independent；
- 忽略提示等级或活跃误区；
- 在新任务前展示决定性答案；
- Gate 未通过仍进入下一核心课。

## 通过标准

状态、提示与推进决定一致，无 Critical Fail。
