# 自适应课程运行时协议

本文件规定长期课程如何保存、推进、调整和恢复。目标是用少量稳定状态支撑逐课教学，不把长对话或预生成课件当作运行时。

## 一、最小状态模型

课程运行时由五类对象组成：

```text
Course Contract  学习目标、应用场景、结业证据
Course Route     可调整课程地图和版本记录
Current Lesson   当前课计划、当前学习段长文、题目前冻结评测
Learner State    掌握证据、误区、当前位置
Review Queue     到期回忆和迁移复习
```

`00-课程入口.md` 是用户可见投影，不是唯一真相源。结构化状态以 YAML 文件为准，入口页可随状态重新生成。

## 二、逐课生成原则

### 建课时生成

- 掌握契约；
- 3—12 课的可调整路线；
- 每课目标、前置、掌握证据和暂定顺序；
- 当前第一课的 3—4 段计划；
- 当前第一学习段的教学长文与来源记录。

### 建课时不生成

- 第二课及以后教材正文；
- 当前课尚未进入的学习段正文；
- 未来课的例题、图片、评测和总结；
- 未知来源的全文解析；
- 基于假设学习表现写出的补救课。

未来课用 `route_status: provisional` 和 `material_status: not_generated` 表示。只有成为当前课后才创建目录。当前课目录只为已经进入的学习段创建长文文件。

## 三、状态枚举

### 路线状态 `route_status`

- `active`：当前正在准备或教学的一课；
- `provisional`：未来路线占位，可自由调整；
- `completed`：已经完成教学，历史版本保留；
- `skipped`：基于已有证据跳过，并记录理由。

同一时间最多一课为 `active`。

### 教材状态 `material_status`

- `not_generated`：只有路线条目；
- `draft`：当前课已生成，但来源或评测尚未就绪；
- `source_checked`：实际采用的来源已由主 Tutor 核验，关键结论可以定位；
- `fact_checked`：教材对来源的转述、综合、数字、条件和争议已经核对；
- `pedagogy_checked`：教材已经通过老师式长文、案例、边界和主动练习检查；
- `verified`：旧版聚合状态，兼容读取；新教材不再用它代替三段审校；
- `frozen`：已开始对用户教学或已用于评测；
- `invalidated`：发现来源或标准问题，停止继续使用；
- `legacy_prebuilt`：旧课程提前生成的未来教材；到当前课之前不加载、不视为已确认版本。

### 教学状态 `delivery_status`

- `not_started`；
- `in_progress`；
- `completed`。

### 掌握状态 `mastery_status`

只使用 `unknown / exposed / guided / independent / transferable / durable`。定义读取 `../rubrics/mastery-rubric.md`。

## 四、版本与冻结

“冻结”用于保证可追溯，不表示课程不能调整。

### 路线基线

确认目标后写入：

```yaml
route:
  version: 1
  status: provisional
  confirmed_scope:
    - learning_goal
    - application_context
    - final_mastery_evidence
    - active_lesson
  future_lessons_are_provisional: true
```

用户修改目标、方向、难度或顺序时，只改未来课，并将 `route.version` 加一。

### 当前课与学习段冻结

当前课依次经过：

```text
plan draft
→ part 1 source checked
→ part 1 facts checked
→ part 1 pedagogy checked
→ part 1 delivery and practice
→ adapt ungenerated parts
→ next part
→ assessment frozen immediately before delivery
```

每个学习段交付前还要准备用户可见导航，并按顺序交付：

```text
位置与前后衔接
→ 当前来源的简化教材
→ Tutor 综合与适用边界
→ 用户场景中的应用假设
→ 已通过 preflight 且已冻结的主动输出
```

学习段计划和教材元数据从 v4 起必须包含 `source_layer / tutor_synthesis / application_layer`。旧课包缺少这些字段时按 legacy 读取，不改写历史；尚未开始的新学习段按 v4 补齐。

每个学习段教学开始后保留自己的 `material_version`。尚未生成的学习段可以根据反馈直接改计划；已经教学的学习段需要修正时创建新版本，标明受影响题目并撤销旧判分。

### 评测冻结

题目展示前固定 `correct_answer` 或 rubric、理由、可接受变体、常见错误和提示阶梯。用户回答后只允许：按标准判分；或因题目/来源问题标记 `ungradable` 并撤销。

## 五、用户控制事件

把下列自然语言归一化为事件：

```yaml
continue: 继续、下一段
question: 我有问题、这里是什么意思
too_hard: 太难了、讲简单点、我跟不上
change_direction: 不是我想学的、换个方向、调整课程
pause: 先停一下、下次继续
note: 这是我的理解、帮我记一下
```

### `continue`

只有当前学习段 Gate 允许推进时，才进入下一学习段。若已到本课末尾，先完成即时主动回忆、变化场景迁移、误区检查和状态更新，不直接生成下一课。核心节点未达到前置状态时，`继续` 表示进入补强，而不是绕过 Gate。

### `question`

回答当前范围内的问题，记录返回位置。问题暴露前置缺口时，插入最小补充，不自动扩展成新课程分支。

### `too_hard`

按顺序尝试：降低抽象度、缩小任务、换用户熟悉的例子、给完整示范、补前置。记录提示等级。高提示完成不得记为独立掌握。

### `change_direction`

暂停当前教学，先总结偏差属于目标、难度、案例、节奏还是路线。给出最小调整方案，只修改 `provisional` 课程。若当前课目标也要改变，创建新版本并说明原版本如何处理。

### `pause`

保存当前课、当前学习段、未决问题和下一步。不要为了制造“结课感”强行完成总结或判定掌握。

### `note`

将用户原话追加到 `02-user-notes.md`。需要整理时，把原话与 AI 整理分区保存。

## 六、课程调整记录

每次路线变化写入：

```yaml
course_adjustments:
  - adjustment_id: CA-001
    changed_at: ""
    trigger: user_feedback | performance_evidence | source_change | constraint_change
    evidence: ""
    route_version_from: 1
    route_version_to: 2
    affected_lessons: [L02, L03]
    before: ""
    after: ""
    reason: ""
    user_confirmed: false
```

不为纯措辞修改制造版本。会改变目标、顺序、难度、掌握证据或课次增删的变化才记录。

## 七、双进度投影

课程入口至少展示：

| 课次 | 路线状态 | 内容进度 | 掌握进度 | 下一步 |
|---|---|---|---|---|
| L01 | 当前 | 第 2/4 段 | guided | 完成无提示变式 |
| L02 | 暂定 | 未生成 | unknown | 等 L01 证据后确认 |

内容进度回答“课程讲到哪里”；掌握进度回答“用户能做到什么”。禁止用内容完成百分比推导掌握百分比。

## 八、来源接入与按需解析

用户材料不是建课前置条件。没有用户材料时使用 `agent_researched`，只围绕当前学习段制定研究范围、搜集权威资料、建立关键结论—来源对应，再进入教材写作。详细 Gate 读取 `safety-and-sources.md`。

### PDF 与本地文件

记录 `original_location`、文件哈希或稳定标识、实际使用页码、解析状态和限制。先定位当前课需要的范围，再读取对应页。只有用户授权且复制有价值时，才放入 `sources/originals/`。

### 网页

记录 URL、访问日期、标题、作者或机构和使用范围。近期事实重新访问官方来源。不要为了保存课程而复制整篇受版权保护内容。

### 视频或音频

优先使用发布者字幕、平台字幕或可靠转录。记录 `time_range`。没有转录或无法访问时标为 `unavailable`，向用户说明需要字幕、转录或本地文件。

### 外部笔记或课程系统

用户明确要求且当前运行时具备相应读取工具时，可以接入其中的课程、笔记、PDF 页面或视频转录作为 `user_material`。保留稳定对象标识或原始链接；不要把旧 Tutor 的总结自动当成事实或掌握证据。具体产品连接方式属于部署适配层，不写入通用学习协议。

## 九、Token 成本控制

按 `cost-routing.md` 在质量约束下优化总成本。先用确定性工具，再考虑低成本资料 Agent；默认最多一个，只处理候选资料与元数据，主 Tutor 保留来源批准、教材综合、事实审校和评测权。

每轮只加载：

1. 课程入口的当前位置；
2. 学习者状态中的当前节点和到期复习；
3. 当前课计划与当前学习段；
4. 判分时对应 assessment；
5. 当前问题需要的来源片段。

禁止：加载全部未来教材、每轮重写完整课程总结、重复解析同一大文件、在用户未确认目标前生成长课件。

同时禁止：为了省 Token 并行多个重叠研究 Agent；把低成本模型的摘要直接当作来源；在便宜模型失败后反复重试而不升级；只统计主线程而忽略子 Agent 与返工成本。

## 十、旧课程包兼容

旧版可能使用：

```text
lessons/01-title.md
lessons/L01-title/assessment.yaml
```

兼容处理：

1. 不移动或删除旧文件；
2. 在 outline 中补充路线、教材、教学和掌握四类状态；
3. 当前课继续读取旧路径；
4. 未开始的旧教材标记 `legacy_prebuilt`，在成为当前课之前不加载；
5. 新增课程使用每课独立目录，并把同一课的评测统一写入课程级 `assessments/01-title.yaml`；
6. 不把旧教材存在视为已经教学或已经掌握。

## 十一、结束一课的原子更新

结束、暂停或调整当前课时，按一次原子动作更新：

1. 当前学习段和内容进度；
2. learner state 中的证据、提示、误区和掌握状态；
3. 用户笔记和 Tutor 总结；
4. review queue；
5. 课程入口投影；
6. 如需调整，更新路线版本和 change log。

其中 review queue 必须包含本课即时复习记录：`review_type: immediate`、`retrieval_before_summary: true`、迁移任务、结果、复发误区和 `next_action`。即时复习未完成或核心迁移失败时，下一课保持 `provisional + not_generated`。

每次 mastery 变化必须先保存 promotion evidence：节点、任务、判分、提示等级、已满足与未满足标准、活跃误区、历史最高状态、当前状态和是否允许推进。最后一次正确不能覆盖同一节点上的引导依赖；迁移失败保留历史最高证据，同时把当前状态和阻断原因写实。

如果任一关键文件写入失败，不宣称状态已保存。说明失败范围并保留下一步恢复动作。
