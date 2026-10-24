import pandas as pd
from dataclasses import dataclass
from typing import Optional, List


AIRPORT_BASELINE = {
    "海陵国际机场": {"completion_rate": 0.94, "note": "晴好天气下放行完成率约94%，机位周转稳定"},
    "北岭机场":     {"completion_rate": 0.93, "note": "正常时段完成率93%，登机口周转顺畅"},
    "云川国际机场": {"completion_rate": 0.95, "note": "常态下双监控数据源保持一致"},
    "南湾机场":     {"completion_rate": 0.94, "note": "夏季傍晚易出现对流雷雨"},
    "高原机场":     {"completion_rate": 0.92, "note": "场地资源紧张，人工调度频繁"},
}


def get_baseline(airport: str) -> dict:
    return AIRPORT_BASELINE.get(airport, {"completion_rate": 0.93, "note": "通用基准：完成率约93%"})


def detect_signals(text_blob: dict) -> dict:
    """把事件所有文本字段揉在一起扫描，提取扰动信号"""
    all_text = " ".join([
        str(text_blob.get("事件名称", "")),
        str(text_blob.get("天气描述", "")),
        str(text_blob.get("运行情况描述", "")),
        str(text_blob.get("现场备注", "")),
        str(text_blob.get("数据标记", "")),
        str(text_blob.get("事件状态", "")),
    ])

    signals = {}

    weather_keywords = ["雨", "雷", "暴雨", "雷雨", "强对流", "阵风", "大风", "雾", "雪", "冰雹"]
    signals["weather_alert"] = any(k in all_text for k in weather_keywords)

    capacity_keywords = ["完成率下降", "积压", "机位紧张", "登机口", "周转", "延误",
                         "效率下降", "资源紧张", "容量", "压力", "晚点", "等待时间"]
    signals["capacity_stress"] = any(k in all_text for k in capacity_keywords)

    conflict_keywords = ["冲突", "不一致", "矛盾", "两套数据", "多源", "数据差异",
                         "读数不同", "口径", "来源不同", "信息不一致", "数据冲突",
                         "两个来源", "数据对不上", "数据来源"]
    signals["data_conflict"] = any(k in all_text for k in conflict_keywords)

    override_keywords = ["人工否决", "否决", "人工判断", "override", "人工决定", "现场人员判断"]
    signals["human_overrule"] = any(k in all_text for k in override_keywords)

    comm_keywords = ["旅客通知", "沟通", "话术", "告知", "通知草稿", "旅客沟通"]
    signals["needs_communication"] = any(k in all_text for k in comm_keywords)

    return signals, all_text


def classify_risk(signals: dict, baseline: dict) -> dict:
    """
    优先级：人工否决 > 数据冲突 > 气象扰动 > 容量扰动 > 正常
    这是通用规则，不绑定任何事件编号
    """
    if signals["human_overrule"]:
        return {
            "disruption_type": "人工否决复盘",
            "risk_level": "低（以人工判断为准）",
            "reasoning": "检测到人工否决信号：现场专业人员判断优先级高于AI指标评估，AI跟随人工结论。",
            "gap_hint": "人工掌握的现场临时调配细节",
            "priority_actions": [
                "完整记录本次否决案例及全部观测数据，存入复盘台账",
                "持续跟踪运行指标，若恶化则重新触发评估",
                "复盘后校准系统评估阈值"
            ],
            "rules_ref": "RULE006"
        }

    if signals["data_conflict"]:
        return {
            "disruption_type": "数据可信性扰动",
            "risk_level": "无法判断",
            "reasoning": "检测到数据冲突信号：多源信息不一致，缺少可信单一事实来源，AI不输出确定性结论。",
            "gap_hint": "各数据源采集时间差、校验逻辑差异、权威数据源归属",
            "priority_actions": [
                "最高优先级：联系数据维护方核对口径，对齐数据定义",
                "口径对齐前，暂停基于冲突数据的调度决策，不对外发布风险结论",
                "30分钟内无法对齐则升级至数据负责人"
            ],
            "rules_ref": "RULE001"
        }

    if signals["weather_alert"]:
        return {
            "disruption_type": "气象扰动",
            "risk_level": "中",
            "reasoning": f"检测到气象预警信号：天气条件偏离机场正常基线（{baseline['note']}），存在潜在保障压力，但尚未确认已发生航班延误。",
            "gap_hint": "预警精确起止窗口、空管放行预案、高峰航班密度",
            "priority_actions": [
                "与气象及地面保障团队持续更新天气实况",
                "统计高峰时段航班流量，评估人力设备余量",
                "提前准备旅客沟通草稿，等待官方确认后再下发"
            ],
            "rules_ref": "RULE002, RULE005"
        }

    if signals["capacity_stress"]:
        return {
            "disruption_type": "容量/资源扰动",
            "risk_level": "中",
            "reasoning": f"检测到运行压力信号：航班放行效率偏离正常基线（{baseline['note']}），机位/登机口周转承压，非气象因素导致。",
            "gap_hint": "备用登机口数量、地勤人员剩余工时、机位实时占用率",
            "priority_actions": [
                "核查机位、登机口实时占用状态，识别瓶颈环节",
                "调整地面保障顺序，优先保障晚高峰航班",
                "设置30分钟观察阈值，指标持续恶化则升级至运营负责人"
            ],
            "rules_ref": "RULE003, RULE004"
        }

    return {
        "disruption_type": "无显著扰动",
        "risk_level": "低",
        "reasoning": "运行指标接近机场正常基线，未识别到明显扰动信号。",
        "gap_hint": "无关键信息缺口",
        "priority_actions": ["维持常规监控节奏，持续观测运行指标"],
        "rules_ref": "通用监控"
    }


def generate_messages(event: dict, classification: dict, signals: dict) -> dict:
    airport = event["机场名称"]
    d_type = classification["disruption_type"]
    risk = classification["risk_level"]
    reasoning = classification["reasoning"]
    gaps = classification["gap_hint"]
    weather = str(event.get("天气描述", "无"))
    ops_desc = str(event.get("运行情况描述", "无"))

    ops_msg = (
        f"【内部运营提示】{airport}｜扰动类别：{d_type}｜风险等级：{risk}\n"
        f"观测摘要：天气={weather[:50]}；运行={ops_desc[:50]}\n"
        f"评估依据：{reasoning}\n"
        f"注意：本内容仅为决策支持，不构成放行/取消指令。"
    )

    airport_msg = (
        f"【机场协同请求】{airport}\n"
        f"当前检测到{d_type}风险，需要协同核查以下事项：{gaps}\n"
        f"请同步现场资源状态与最新运行数据。"
    )

    passenger_msg = (
        f"【旅客沟通草稿】{airport}本场运行条件存在变化可能，"
        f"航班最终状态请以航空公司官方通知为准。"
        f"本草稿仅供内部准备使用，不可直接对外发送。"
    )

    return {"ops": ops_msg, "airport_team": airport_msg, "passenger": passenger_msg}

def main():
    file_name = "Track 3 Data.xlsx"
    df = pd.read_excel(file_name, sheet_name="04_模拟事件")

    print("=" * 60)
    print("  SkyGuard 规则引擎 — 运行报告")
    print("=" * 60)

    results = []

    for _, row in df.iterrows():
        evt = row.to_dict()
        eid = evt["事件编号"]
        airport = evt["机场名称"]

        signals, all_text = detect_signals(evt)

        baseline = get_baseline(airport)

        classification = classify_risk(signals, baseline)

        messages = generate_messages(evt, classification, signals)

        print(f"\n--- {eid} | {airport} ---")
        print(f"  命中信号: {[k for k,v in signals.items() if v]}")
        print(f"  扰动类型: {classification['disruption_type']}")
        print(f"  风险等级: {classification['risk_level']}")

        results.append({
            "事件编号": eid,
            "机场名称": airport,
            "风险等级": classification["risk_level"],
            "基线对比": f"正常基线：{baseline['note']}",
            "扰动类型": classification["disruption_type"],
            "评估依据": classification["reasoning"],
            "信息缺口": classification["gap_hint"],
            "优先级行动": "\n".join(classification["priority_actions"]),
            "给运营人员草稿": messages["ops"],
            "给机场协同组草稿": messages["airport_team"],
            "给旅客草稿": messages["passenger"],
            "仅人工可决定事项": "航班放行、取消、调度、维修、安全判定、赔偿及正式旅客通知，必须由持证航空专业人员决定。",
            "引用规则": classification["rules_ref"]
        })

    df_out = pd.DataFrame(results)
    with pd.ExcelWriter(file_name, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_out.to_excel(writer, sheet_name="06_智能助手输出", index=False)

    print("\n" + "=" * 60)
    print("全部事件评估完成，已写入【06_智能助手输出】")
    print("=" * 60)


if __name__ == "__main__":
    main()
