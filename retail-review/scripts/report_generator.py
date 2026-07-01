#!/usr/bin/env python3
"""
零售经营复盘报告生成器
零售一站式经营复盘 Skill — 步骤三

功能：
1. 整合数据结果、指标、异常、归因
2. 自动组装结构化 HTML 复盘报告
3. 支持日报/周报/月报三种周期
4. 支持单店独立复盘和多门店横向对比

输入：处理结果 JSON + 诊断结果 JSON
输出：HTML 复盘报告文件
"""

import json
import sys
from datetime import datetime
from pathlib import Path


class ReportGenerator:
    """零售经营复盘报告生成器"""

    REPORT_SECTIONS = [
        "业绩总览",
        "核心三要素拆解",
        "品类结构分析",
        "门店盈利分析",
        "经营风险提示",
        "会员经营复盘",
        "核心问题汇总",
        "落地改善动作",
    ]

    def __init__(
        self,
        processor_result: dict,
        detector_result: dict | None = None,
        report_type: str = "月报",
        mode: str = "单店",
    ):
        self.data = processor_result
        self.indicators = processor_result.get("经营指标", {})
        self.diagnosis = detector_result or {}
        self.anomalies = self.diagnosis.get("异常清单", [])
        self.attributions = self.diagnosis.get("归因分析", [])
        self.conclusion = self.diagnosis.get("综合结论", {})
        self.report_type = report_type
        self.mode = mode

    # ─── 各板块生成 ───

    def _section_overview(self) -> str:
        """1. 业绩总览"""
        achievement = self.indicators.get("业绩达成率", {})
        margin_data = self.indicators.get("毛利率", {})

        rate = achievement.get("达成率", 0) if isinstance(achievement, dict) else achievement
        target = achievement.get("目标销售额", 0) if isinstance(achievement, dict) else 0
        actual = achievement.get("实际销售额", 0) if isinstance(achievement, dict) else 0
        margin = margin_data.get("毛利率", "N/A") if isinstance(margin_data, dict) else margin_data

        total_sales = self.indicators.get("总销售额", 0)
        total_qty = self.indicators.get("总销量", 0)
        orders = self.indicators.get("成交笔数", 0)
        avg_order = self.indicators.get("客单价", 0)

        rate_class = "positive" if isinstance(rate, (int, float)) and rate >= 100 else "negative"
        rate_label = "超额完成" if isinstance(rate, (int, float)) and rate >= 100 else "未达标" if isinstance(rate, (int, float)) and rate < 100 else "—"

        return f"""
        <div class="section" id="section-overview">
            <h2>📊 一、业绩总览</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">总销售额</div>
                    <div class="kpi-value">¥{total_sales:,.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">总销量</div>
                    <div class="kpi-value">{total_qty:,}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">成交笔数</div>
                    <div class="kpi-value">{orders:,}</div>
                </div>
                <div class="kpi-card highlight">
                    <div class="kpi-label">客单价</div>
                    <div class="kpi-value">¥{avg_order:,.2f}</div>
                </div>
            </div>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">目标达成率</div>
                    <div class="kpi-value {rate_class}">{rate}% <span class="tag">{rate_label}</span></div>
                    <div class="kpi-sub">目标：¥{target:,.2f} / 实际：¥{actual:,.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">毛利率</div>
                    <div class="kpi-value">{margin}%</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">统计周期</div>
                    <div class="kpi-value" style="font-size:16px;">{self.indicators.get('数据起始日期', '—')} ~ {self.indicators.get('数据截止日期', '—')}</div>
                    <div class="kpi-sub">共 {self.indicators.get('统计天数', '—')} 天</div>
                </div>
            </div>
        </div>
        """

    def _section_three_factors(self) -> str:
        """2. 核心三要素拆解"""
        traffic = self.indicators.get("客流量", 0)
        conversion = self.indicators.get("成交转化率", 0)
        avg_order = self.indicators.get("客单价", 0)
        link_rate = self.indicators.get("连带率", 0)
        traffic_note = self.indicators.get("客流量_备注", "")

        rows = ""
        for name, value, note in [
            ("客流量", f"{traffic:,}人", traffic_note),
            ("成交转化率", f"{conversion}%", ""),
            ("客单价", f"¥{avg_order:,.2f}", ""),
            ("连带率", f"{link_rate}", "件/单"),
        ]:
            rows += f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{value}</td>
                <td class="muted">{note}</td>
            </tr>
            """

        return f"""
        <div class="section" id="section-factors">
            <h2>🔍 二、核心三要素拆解</h2>
            <p class="desc">销售额 = 客流量 × 转化率 × 客单价，逐项拆解如下：</p>
            <table>
                <thead><tr><th>维度</th><th>数值</th><th>备注</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            <div class="formula-box">
                <strong>三要素公式：</strong>
                ¥{self.indicators.get("总销售额", 0):,.2f} ≈ {traffic:,} × {conversion}% × ¥{avg_order:,.2f}
            </div>
        </div>
        """

    def _section_category(self) -> str:
        """3. 品类结构分析"""
        cat_data = self.indicators.get("品类分析", [])
        if not cat_data:
            return """
            <div class="section"><h2>📦 三、品类结构分析</h2>
            <p class="muted">暂无品类维度数据</p></div>
            """

        max_width = max(c["占比"] for c in cat_data) if cat_data else 1
        bars = ""
        for c in cat_data[:10]:
            bar_width = (c["占比"] / max_width * 100) if max_width > 0 else 0
            bars += f"""
            <div class="bar-row">
                <span class="bar-label">{c['品类']}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{bar_width}%"></div></div>
                <span class="bar-value">¥{c['销售额']:,.2f} ({c['占比']}%)</span>
            </div>
            """

        top_cat = cat_data[0]
        return f"""
        <div class="section" id="section-category">
            <h2>📦 三、品类结构分析</h2>
            <p class="desc">TOP1品类：<strong>{top_cat['品类']}</strong>，贡献 {top_cat['占比']}% 业绩</p>
            <div class="bar-chart">{bars}</div>
        </div>
        """

    def _section_profit(self) -> str:
        """4. 门店盈利分析"""
        margin_data = self.indicators.get("毛利率", {})
        margin = margin_data.get("毛利率", "N/A") if isinstance(margin_data, dict) else margin_data
        cost = margin_data.get("销售成本", "N/A") if isinstance(margin_data, dict) else "N/A"
        promo = self.indicators.get("促销让利总额", 0)
        promo_ratio = self.indicators.get("促销让利占比", 0)
        sales = self.indicators.get("总销售额", 0)

        return f"""
        <div class="section" id="section-profit">
            <h2>💰 四、门店盈利分析</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">毛利率</div>
                    <div class="kpi-value">{margin}%</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">销售成本</div>
                    <div class="kpi-value">¥{cost:,.2f}</div>
                </div>
                <div class="kpi-card {'highlight' if promo_ratio > 15 else ''}">
                    <div class="kpi-label">促销让利总额</div>
                    <div class="kpi-value">¥{promo:,.2f}</div>
                    <div class="kpi-sub">占销售额 {promo_ratio}%</div>
                </div>
            </div>
        </div>
        """

    def _section_risks(self) -> str:
        """5. 经营风险提示"""
        risks = []

        # 基于异常清单生成风险提示
        for anomaly in self.anomalies:
            if anomaly.get("优先级") == "P0":
                risks.append({
                    "风险等级": "🔴 高风险",
                    "风险项": anomaly["异常类型"],
                    "说明": anomaly["判定依据"],
                })
            elif anomaly.get("优先级") == "P1":
                risks.append({
                    "风险等级": "🟡 中风险",
                    "风险项": anomaly["异常类型"],
                    "说明": anomaly["判定依据"],
                })

        if not risks:
            risks = [{"风险等级": "🟢 低风险", "风险项": "暂无明显经营风险", "说明": "各项指标处于正常范围"}]

        rows = ""
        for r in risks:
            rows += f"""
            <tr>
                <td>{r['风险等级']}</td>
                <td>{r['风险项']}</td>
                <td class="muted">{r['说明']}</td>
            </tr>
            """

        return f"""
        <div class="section" id="section-risks">
            <h2>⚠️ 五、经营风险提示</h2>
            <table>
                <thead><tr><th>风险等级</th><th>风险项</th><th>说明</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """

    def _section_member(self) -> str:
        """6. 会员经营复盘"""
        member = self.indicators.get("会员分析", {})
        if not member:
            return """
            <div class="section"><h2>👤 六、会员经营复盘</h2>
            <p class="muted">暂无会员维度数据</p></div>
            """

        return f"""
        <div class="section" id="section-member">
            <h2>👤 六、会员经营复盘</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">会员消费占比</div>
                    <div class="kpi-value">{member.get('会员消费占比', 0)}%</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">会员客单价</div>
                    <div class="kpi-value">¥{member.get('会员客单价', 0):,.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">会员数量</div>
                    <div class="kpi-value">{member.get('会员数量', 0):,}</div>
                </div>
            </div>
        </div>
        """

    def _section_issues(self) -> str:
        """7. 核心问题汇总"""
        issues = self.conclusion.get("核心问题总结", [])
        if not issues:
            issues = ["未检测到明显经营异常"]

        items = "".join(f"<li>{i}</li>" for i in issues)

        return f"""
        <div class="section" id="section-issues">
            <h2>📋 七、核心问题汇总</h2>
            <div class="health-badge">{self.conclusion.get('经营健康度', '—')}</div>
            <ul class="issue-list">{items}</ul>
        </div>
        """

    def _section_actions(self) -> str:
        """8. 落地改善动作"""
        actions = []
        for attr in self.attributions:
            for idx, action in enumerate(attr.get("整改方向", []), 1):
                actions.append({
                    "归因": attr["归因维度"],
                    "优先级": attr["归因优先级"],
                    "动作": action,
                })

        if not actions:
            actions = [
                {"归因": "—", "优先级": "—", "动作": "当前经营状况良好，建议维持现有策略并持续监控核心指标"},
            ]

        rows = ""
        for i, a in enumerate(actions, 1):
            priority_tag = "p0-tag" if a["优先级"] == "P0" else "p1-tag" if a["优先级"] == "P1" else ""
            rows += f"""
            <tr>
                <td>{i}</td>
                <td><span class="priority-tag {priority_tag}">{a['优先级']}</span> {a['归因']}</td>
                <td>{a['动作']}</td>
            </tr>
            """

        return f"""
        <div class="section" id="section-actions">
            <h2>🎯 八、落地改善动作</h2>
            <table>
                <thead><tr><th>#</th><th>归因维度</th><th>具体改善动作</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """

    # ─── 组装完整报告 ───
    def generate_html(self) -> str:
        """生成完整 HTML 报告"""
        sections = [
            self._section_overview(),
            self._section_three_factors(),
            self._section_category(),
            self._section_profit(),
            self._section_risks(),
            self._section_member(),
            self._section_issues(),
            self._section_actions(),
        ]

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        body = "\n".join(sections)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>零售经营{self.report_type} — {self.mode}复盘</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #2c3e50; line-height:1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 40px 30px; border-radius: 16px; margin-bottom: 24px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .sub {{ font-size: 14px; opacity: 0.85; }}
        .section {{ background: #fff; border-radius: 12px; padding: 28px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
        .section h2 {{ font-size: 20px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #f0f0f0; }}
        .desc {{ color: #7f8c8d; font-size: 14px; margin-bottom: 16px; }}
        .muted {{ color: #95a5a6; font-size: 13px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 16px; }}
        .kpi-card {{ background: #f8f9fb; border-radius: 10px; padding: 20px; text-align: center; border: 1px solid #eef0f4; }}
        .kpi-card.highlight {{ background: #fef9e7; border-color: #f9e79f; }}
        .kpi-label {{ font-size: 13px; color: #7f8c8d; margin-bottom: 6px; }}
        .kpi-value {{ font-size: 24px; font-weight: 700; color: #2c3e50; }}
        .kpi-value.positive {{ color: #27ae60; }}
        .kpi-value.negative {{ color: #e74c3c; }}
        .kpi-sub {{ font-size: 12px; color: #95a5a6; margin-top: 4px; }}
        .tag {{ display: inline-block; font-size: 12px; padding: 2px 8px; border-radius: 4px; margin-left: 8px; vertical-align: middle; }}
        .positive .tag {{ background: #d5f5e3; color: #27ae60; }}
        .negative .tag {{ background: #fadbd8; color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th {{ background: #f8f9fb; padding: 12px; text-align: left; font-size: 13px; color: #7f8c8d; border-bottom: 2px solid #eef0f4; }}
        td {{ padding: 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
        .formula-box {{ background: #eaf2f8; border-left: 4px solid #3498db; padding: 16px; margin-top: 20px; border-radius: 6px; font-size: 14px; }}
        .bar-chart {{ margin-top: 16px; }}
        .bar-row {{ display: flex; align-items: center; margin-bottom: 10px; gap: 12px; }}
        .bar-label {{ width: 100px; font-size: 13px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .bar-track {{ flex: 1; height: 22px; background: #eef0f4; border-radius: 11px; overflow: hidden; }}
        .bar-fill {{ height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 11px; transition: width 0.5s ease; }}
        .bar-value {{ width: 140px; font-size: 13px; text-align: right; flex-shrink: 0; }}
        .health-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-weight: 600; font-size: 15px; margin-bottom: 16px; background: #fef9e7; color: #b7950b; }}
        .issue-list {{ padding-left: 20px; }}
        .issue-list li {{ margin-bottom: 8px; font-size: 14px; line-height: 1.7; }}
        .priority-tag {{ display: inline-block; font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: 600; margin-right: 6px; }}
        .p0-tag {{ background: #fadbd8; color: #c0392b; }}
        .p1-tag {{ background: #fef9e7; color: #b7950b; }}
        .footer {{ text-align: center; padding: 30px; color: #bdc3c7; font-size: 12px; }}
        @media print {{ body {{ background: #fff; }} .section {{ box-shadow: none; break-inside: avoid; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏪 零售经营{self.report_type}</h1>
            <div class="sub">{self.mode}复盘 · 生成时间：{now}</div>
        </div>
        {body}
        <div class="footer">
            <p>本报告由 WorkBuddy 零售一站式经营复盘助手自动生成</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def save(self, output_path: str) -> str:
        """生成并保存 HTML 报告"""
        html = self.generate_html()
        out_path = Path(output_path)
        out_path.write_text(html, encoding="utf-8")
        print(f"✅ 报告已保存: {out_path.resolve()}")
        return str(out_path.resolve())


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python report_generator.py <result.json> [--diagnosis diagnosis.json] [--type 月报] [--mode 单店] [--output report.html]")
        sys.exit(1)

    result_path = sys.argv[1]
    diagnosis_path = None
    report_type = "月报"
    mode = "单店"
    output = "retail_report.html"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--diagnosis" and i + 1 < len(sys.argv):
            diagnosis_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
            report_type = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    with open(result_path, "r", encoding="utf-8") as f:
        processor_result = json.load(f)

    diagnosis = None
    if diagnosis_path:
        with open(diagnosis_path, "r", encoding="utf-8") as f:
            diagnosis = json.load(f)

    generator = ReportGenerator(processor_result, diagnosis, report_type, mode)
    generator.save(output)


if __name__ == "__main__":
    main()
