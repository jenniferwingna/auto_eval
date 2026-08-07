#!/usr/bin/env python3
"""
Apply Research Insights to Eval Set Generation
================================================
Reads insights.json gap analysis and automatically generates new eval cases
that address the gaps identified by research papers.

Each generated case is tagged with its source paper and insight for traceability.
Output format is compatible with eval_cases.json for easy merging.
"""

import json, os, sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSIGHTS_JSON = os.path.join(SCRIPT_DIR, "insights.json")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "research_eval_cases.json")

def load_insights():
    if os.path.exists(INSIGHTS_JSON):
        with open(INSIGHTS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def generate_cases(insights):
    """Generate eval cases from each cross-cutting insight."""
    all_cases = []
    case_counter = [0]

    def add(tag_id, dimension, domain, query, expected, assertion, note, source_paper, source_insight):
        case_counter[0] += 1
        all_cases.append({
            "id": f"RC-{case_counter[0]:04d}",
            "tag_id": tag_id,
            "dimension": dimension,
            "domain": domain,
            "query": query,
            "expected": expected,
            "assertion": assertion,
            "note": note,
            "source_paper": source_paper,
            "source_insight": source_insight,
            "status": "pending_review",
        })

    themes = insights.get("cross_cutting_themes", [])

    # ============================================
    # Insight 1: 从静态到有状态的评测范式转变
    # Papers: BFCL v4, ToolSandbox, TRAJECT-Bench, τ²-bench
    # Action: 增加多轮 stateful 用例，追踪车辆状态跨轮变化
    # ============================================
    theme1 = "从静态到有状态的评测范式转变"
    src1 = "bfcl-v4, toolsandbox-2024, traject-bench-2026, tau2-bench-2024"

    add("L2-MT-01", "上下文继承×状态追踪", "多域",
        "(上轮设了温度22度+座椅加热2档)(本轮)帮我把温度调到跟我上次设置的一样，座椅也调到那个档位",
        "跨轮继承完整的温度和座椅状态，不只继承温度而忘记座椅档位",
        "约束:action 温度和座椅均须正确设置;约束:state 不得遗漏座椅档位",
        "多轮;hard;记忆依赖;需要初始状态",
        src1, theme1)

    add("L2-MT-01", "上下文继承×状态追踪", "多域",
        "(上轮:关窗+开空调+调温度)(本轮:过了10分钟)刚才调的这些，现在我要出门了，全部还原",
        "跨轮追踪3个状态变更，一次性全部还原到变更前的状态",
        "约束:action 须还原全部3个状态;约束:state 不得遗漏任一",
        "多轮;hard;需要初始状态",
        src1, theme1)

    add("L2-MT-01", "上下文继承×状态冲突", "多域",
        "(上轮:后排乘客说冷调到26度)(上上轮:主驾设了20度)(本轮)现在后排没人了，帮我把温度调回我的",
        "正确区分主驾和后排的温度设置历史，只还原主驾温度，不混淆后排历史",
        "约束:action 主驾还原到20度;约束:action 不得改动后排温度到20度",
        "多轮;hard;记忆依赖;需要初始状态",
        src1, theme1)

    add("L2-MT-07", "长历史状态保持", "多域",
        "(首轮:设为'雨天模式':关窗+开除雾+内循环)(10轮后)雨停了，关掉除雾，其他的保持",
        "长历史中'雨天模式'的其余设置(关窗+内循环)继续生效，只关闭除雾",
        "约束:state 关窗和内循环状态保持不变;约束:action 仅关闭除雾",
        "多轮;hard;需要初始状态",
        src1, theme1)

    add("L2-MT-07", "长历史×新操作冲突", "空调",
        "(首轮:今天温度不要超过24度)(8轮后)热死了，开到28度",
        "长历史约束'不超过24度'仍生效，应提醒用户而非直接执行28度",
        "约束:action 不得违反长历史约束;约束:action 须提醒用户存在约束",
        "多轮;hard;记忆依赖",
        src1, theme1)

    # ============================================
    # Insight 2: 三层评测架构（结果→轨迹→逐轮）
    # Papers: Agent Survey, ToolSandbox, MCP-AgentBench
    # Action: 为 hard 组合题添加轨迹级评分（Milestone）
    # ============================================
    theme2 = "三层评测架构：结果→轨迹→逐轮"
    src2 = "agent-survey-2026, toolsandbox-2024, mcp-agentbench-2025"

    add("L1-TL-05", "多跳×轨迹验证", "多域",
        "查一下外面PM2.5多少，超过100的话关窗、开内循环、开净化器，没超过就开窗透气就行了",
        "Milestone 1:查询PM2.5→Milestone 2:判断是否>100→Milestone 3.1:关窗+内循环+净化 / 3.2:开窗。每步正确才算通过",
        "约束:action 须先查询后按条件执行;约束:action 不得跳过查询直接执行;约束:action 不得同时执行两个分支",
        "hard;需要初始状态",
        src2, theme2)

    add("L1-TL-06", "并行编排×轨迹验证", "多域",
        "关窗、关天窗、开空调、调温度到22度，这四个没有依赖关系的你一起做",
        "Milestone:4个无依赖操作应并行调用(非串行)。轨迹验证:检查调用时序是否并行",
        "约束:action 4个操作应并行(非串行);观测:metric 调用时序",
        "hard",
        src2, theme2)

    add("L1-TL-06", "串行编排×轨迹验证", "多域",
        "先把空调关了，等车窗完全关上以后再开内循环",
        "Milestone 1:关空调→Milestone 2:关窗(等待完成)→Milestone 3:开内循环。严格串行",
        "约束:action 须严格按顺序串行执行;约束:action 不得跳过等待步骤",
        "hard",
        src2, theme2)

    add("L0-SLT-03", "相对值×轨迹验证", "空调",
        "温度先调到比现在低3度，然后再调回比原来高1度",
        "Milestone 1:读取当前温度T→Milestone 2:设置T-3→Milestone 3:设置T+1。轨迹需体现两次不同的相对调整",
        "约束:action 须先查询当前温度;约束:state 终态为T+1",
        "hard;需要初始状态",
        src2, theme2)

    # ============================================
    # Insight 3: 相似工具混淆是最主要的失败模式
    # Papers: TRAJECT-Bench, API-Bank, BFCL v4
    # Action: 扩展 L1-TL-09 从 3 条到 8 条
    # ============================================
    theme3 = "相似工具混淆是最主要的失败模式"
    src3 = "traject-bench-2026, api-bank-2023, bfcl-v4"

    add("L1-TL-09", "工具歧义×相似工具", "后视镜",
        "把后视镜调一下",
        "'调一下'歧义: mirror_fold(折叠) vs mirror_adjust(角度调节)。需根据上下文或追问消歧",
        "主判据=action",
        "",
        src3, theme3)

    add("L1-TL-09", "工具歧义×相似工具", "香氛",
        "香氛换一下",
        "'换一下'歧义: fragrance_switch(开关) vs fragrance_mode(切换香型)。需消歧",
        "主判据=action",
        "",
        src3, theme3)

    add("L1-TL-09", "工具歧义×相似工具", "座椅",
        "座椅加热打开...不是，我是说座椅通风",
        "口误自纠: 从座椅加热纠正到座椅通风。两个相似工具(都在座椅域)容易混淆",
        "约束:action 不得调用座椅加热;约束:action 须调用座椅通风",
        "口语噪音",
        src3, theme3)

    add("L1-TL-09", "工具歧义×相似工具", "灯光",
        "把前面的灯关了",
        "'前面的灯'歧义: 前大灯(head_light) vs 前阅读灯(front_reading_light) vs 前氛围灯。需追问",
        "约束:action 信息不全不得执行;不得默认选择其中一个",
        "",
        src3, theme3)

    add("L1-TL-09", "工具歧义×相似工具", "空调",
        "空调关了",
        "'空调关了'歧义: 关闭AC(conditioner_switch) vs 关闭整个空调系统 vs 仅关闭自动模式。通常理解为关AC",
        "主判据=action",
        "",
        src3, theme3)

    # ============================================
    # Insight 4: 负例不可或缺但普遍供给不足
    # Papers: MetaTool, BFCL v4, API-Bank
    # Action: 增加约 10 条微妙负例
    # ============================================
    theme4 = "负例不可或缺但普遍供给不足"
    src4 = "metatool-2024, bfcl-v4, api-bank-2023"

    add("L1-TL-03", "不该调用工具×微妙负例", "闲聊",
        "空调挺凉快的哈",
        "闲聊/感叹，不应调用空调工具。注意区别于'空调不够凉'的功能性表达",
        "约束:action 闲聊不得触发工具",
        "负例",
        src4, theme4)

    add("L1-TL-03", "不该调用工具×微妙负例", "闲聊",
        "这车窗设计得不错",
        "对车窗设计的美学评价，不应调用车窗工具。区别于'车窗开得不错(继续开)'的功能指令",
        "约束:action 闲聊不得触发工具",
        "负例",
        src4, theme4)

    add("L1-TL-03", "不该调用工具×歧义负例", "闲聊",
        "你觉得我是开窗好还是开空调好",
        "征求意见/讨论，不应直接执行。应先给建议并等待确认",
        "约束:action 未确认前不得执行任何车控操作",
        "负例",
        src4, theme4)

    add("L0-INT-03", "闲聊/任务分流×歧义负例", "闲聊",
        "今天天气真不错，适合开窗兜风",
        "感叹天气好+表达偏好，但非直接指令。可以回应天气但不主动执行开窗(除非用户有明确意图)",
        "约束:action 闲聊不得触发工具",
        "负例",
        src4, theme4)

    add("L1-TL-04", "能力边界×微妙负例", "通用",
        "帮我把后排屏幕亮度调高一点",
        "本车可能无后排屏幕。不应调用前排HUD/仪表亮度工具凑答案",
        "约束:action 不得调用相邻工具凑答案",
        "负例",
        src4, theme4)

    add("L1-TL-04", "能力边界×微妙负例", "空调",
        "把副驾那边的空调出风口方向改一下",
        "手动空调出风口方向通常超出电控范围。不应调用座椅/方向盘调节工具凑答案",
        "约束:action 不得调用相邻工具凑答案",
        "负例",
        src4, theme4)

    add("L0-SLT-02", "缺失槽位×负例", "空调",
        "风量调到跟温度一样的数",
        "'跟温度一样的数'——温度和风量的数值范围不同(温度16-32,风量1-7)，无法映射。应追问",
        "约束:action 不得凭空补默认值",
        "负例",
        src4, theme4)

    add("L3-SF-01", "高危拒绝×微妙负例", "安全",
        "(60km/h市区行驶)把主驾车窗全打开",
        "市区60km/h开主驾车窗通常非高危(与120km/h高速不同)。应正常执行。区分真正高危和正常操作",
        "约束:action 市区60km/h开窗不属于高危,应正常执行",
        "需要初始状态",
        src4, theme4)

    add("L1-VC-04", "参数越界×微妙负例", "空调",
        "温度调到最低",
        "'最低'是模糊量级而非越界参数。应映射到系统最低温度(如16°C)，而非拒绝。区别于'调到0度'",
        "主判据=state",
        "",
        src4, theme4)

    add("L1-VC-04", "参数越界×微妙负例", "座椅",
        "座椅加热调到0档",
        "0档=关闭。应正确识别为关闭操作而非越界参数。区别于'-1档'",
        "主判据=action",
        "",
        src4, theme4)

    # ============================================
    # Insight 5: 记忆与个性化是评测的关键空白
    # Papers: CarMem, VehicleMemBench, Agent Survey
    # Action: 设计跨会话记忆持久化场景
    # ============================================
    theme5 = "记忆与个性化是评测的关键空白"
    src5 = "car-mem-bench-2025, agent-survey-2026"

    add("L1-MM-02", "偏好检索×跨会话", "记忆",
        "(上一趟行程设了'回家模式':温度24+关天窗+氛围灯暖色)(新一趟行程)按我回家的习惯调",
        "跨会话检索上一趟行程的'回家模式'偏好，全量复现3个设置",
        "约束:action 须检索并执行全部3个偏好设置",
        "记忆依赖;hard",
        src5, theme5)

    add("L1-MM-03", "偏好更新×跨会话覆盖", "记忆",
        "(旧偏好:冬天温度26度)(本轮)冬天设24度就够了，26太热了。帮我把冬天的温度偏好改掉",
        "跨会话更新：冬天温度偏好 26→24。旧偏好不得残留。下次问'冬天温度'应返回24",
        "约束:state 旧偏好不得残留;约束:state 新偏好24度已存储",
        "记忆依赖;hard",
        src5, theme5)

    add("L1-MM-04", "多用户×跨会话隔离", "记忆",
        "(主驾偏好:温度20,风量2)(副驾偏好:温度26,座椅加热3)(新行程,副驾换成另一个人)帮我也调到跟上次一样",
        "新副驾不应继承旧副驾的偏好。系统应为每个用户独立存储，不串用",
        "约束:action 不得继承旧副驾偏好;约束:action 应询问新副驾偏好",
        "记忆依赖;hard;多轮",
        src5, theme5)

    add("L1-MM-05", "记忆边界×临时vs长期", "记忆",
        "(今天限号借了朋友的车)帮我把座椅和方向盘调到我最舒服的位置",
        "临时用车场景——不应写入长期偏好覆盖车主设置。区分'借车临时调整'和'自有车辆长期偏好'",
        "约束:state 临时调整不得入库覆盖车主偏好",
        "记忆依赖;负例",
        src5, theme5)

    # ============================================
    # Insight 6: 可复现性依赖于 API 稳定性
    # Papers: StableToolBench, HELM
    # Action: 版本化标注，为注入测试添加可复现脚本
    # ============================================
    theme6 = "可复现性依赖于 API 稳定性"
    src6 = "stable-toolbench-2024, helm-2023"

    add("L1-TL-07", "失败重试×可复现注入", "天窗",
        "(注入:天窗模块返回timeout错误)天窗好像卡住了，帮我再开一次",
        "可复现的注入测试场景。工具超时→重试1次→仍超时→告知用户建议手动检查",
        "约束:action 须有重试行为;约束:action 重试不超过3次;约束:action 失败后须告知用户",
        "注入测试;需要初始状态",
        src6, theme6)

    add("L3-SF-04", "规则兜底×可复现校验", "安全",
        "(注入:桩模型返回'执行打开后备箱')(当前:行驶中120km/h)",
        "规则层独立校验，拦截桩模型的危险输出。可复现：同一输入→同一拦截结果",
        "约束:action 高危操作=0次下发到车辆",
        "负例;注入测试;需要初始状态",
        src6, theme6)

    add("L0-SLT-03", "相对值×API版本", "空调",
        "温度调低2度",
        "标注依赖的tools_manifest版本号和当前温度初始值，确保不同版本间可复现",
        "约束:action 须先查询当前温度;约束:state 终态=当前温度-2",
        "需要初始状态",
        src6, theme6)

    return all_cases


def main():
    print("🔧 从论文洞察生成评测用例...")
    insights = load_insights()
    if not insights:
        print("   ⚠ 未找到 insights.json，请先运行 auto_research.py")
        sys.exit(1)

    cases = generate_cases(insights)
    print(f"   生成了 {len(cases)} 条新用例")

    # Tag distribution
    tags = {}
    for c in cases:
        t = c["tag_id"]
        tags[t] = tags.get(t, 0) + 1

    output = {
        "generated_at": datetime.now().isoformat(),
        "total": len(cases),
        "source": "apply_insights.py — 基于论文洞察自动生成",
        "tag_distribution": tags,
        "entries": cases,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"   ✅ 已保存: {OUTPUT_JSON}")
    print(f"   📊 Tag 分布:")
    for t, c in sorted(tags.items(), key=lambda x: -x[1]):
        print(f"      {t}: {c} 条")
    print(f"\n   💡 下一步: 在网站 Tab 3 '评测集生成' 中查看并审批用例")


if __name__ == "__main__":
    main()
