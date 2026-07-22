# Eval 03｜编程程序性技能

## 测试目标

验证 Skill 是否能把“看懂代码”转化为实际编写、运行和调试能力，并根据学习者已有水平逐步撤除脚手架。

## 场景

用户会 Python 基础语法，但没有使用过 pandas。目标是独立读取 CSV、处理缺失值并按部门汇总销售额。

## 初始 Prompt

> 我会 Python 的变量、循环和函数，但没用过 pandas。带我学会读取一个 CSV，把缺失销售额当成 0，再按 department 汇总 sales。不要替我直接做完整项目，我想最后能自己写出来。

## 预期掌握契约

```yaml
learning_goal: 独立用 pandas 读取 CSV、处理 sales 缺失值并按 department 汇总
starting_point: 会 Python 基础，不会 pandas
application_context: 数据处理任务
target_mastery_level: independent
mastery_evidence:
  - 在未展示完整答案的情况下写出并运行代表性代码
  - 能解释 fillna、groupby 和 sum 的作用
  - 能修复一个列名或分组错误
```

## 预期教学路径

1. 给出很小的 CSV 示例或 DataFrame，不加载完整项目；
2. 展示最小可运行结构，但不要一次交付最终完整答案；
3. 先让用户完成一个局部动作，例如写出读取数据和处理缺失值的两行；
4. 再让用户补全分组汇总；
5. 最终要求运行并报告输出或错误；
6. 完成后加入列名变化、多个数值列或异常值等变式。

## 中途错误输入

> 我写的是：`df.groupby("sales")["department"].sum()`

## 预期反馈

必须：

1. 识别用户知道需要使用 `groupby` 和 `sum`；
2. 准确指出分组键与被聚合列放反：应该按 department 分组，对 sales 求和；
3. 不直接贴出完整项目代码；
4. 使用 L1—L3 提示，例如让用户回答“哪一列定义分组，哪一列是数字”；
5. 要求用户自己改写该行；
6. 提醒字符串列 `department` 不能按此方式求和，必要时结合运行错误解释；
7. 状态保持 `guided`。

## 独立任务

在完成示范与纠错后，提供一个新数据结构：

```text
department,region,sales
A,East,10
A,West,
B,East,7
B,West,3
```

要求用户独立完成：

- 读取；
- 将 sales 缺失值填 0；
- 按 department 汇总 sales；
- 说明预期输出；
- 报告代码是否实际运行。

## 预期验收

- 代码结构正确；
- 输出 A=10、B=10；
- 用户能解释关键步骤；
- 无决定答案的提示时，才可标记 `independent`；
- 未实际运行时，应标记“代码推演通过，运行证据缺失”；
- 新列名或新的聚合需求完成后，才能判定迁移。

## 评分重点

- procedure 路由；
- worked example 与脚手架撤除；
- 实际运行证据；
- 错误定位；
- AI 不代替用户写完整项目；
- 迁移任务。

## Critical Fail

- 一开始直接给完整最终项目并宣称用户学会；
- 将看懂代码当成会写；
- 未运行、未解释、未独立编写就标记 `independent`；
- 错误地认可分组与聚合列放反的代码；
- 只评价代码风格，不检查输出和边界。

## 通过标准

按 `tutor-quality-rubric.md` 的适用维度换算得分 ≥ 80，且无 Critical Fail。
