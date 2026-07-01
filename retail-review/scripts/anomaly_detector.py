#!/usr/bin/env python3
"""
零售经营异动智能归因诊断引擎
零售一站式经营复盘 Skill — 步骤二

功能：
1. 基于处理后的经营指标数据，自动扫描识别异常
2. 依托零售知识库，完成七维度归因分析
3. 输出异常清单 + 归因解读 + 初步整改方向

输入：data_processor.py 输出的 JSON
输出：异常诊断报告 JSON
"""

import json
import sys
from datetime import datetime
from typing import Any


class RetailAnomalyDetector:
    """零售经营异常检测与归因引擎"""

    # 异常阈值配置
    THRESHOLDS = {
        "客流量_环比下降_严重": 0.20,   # 下降超20%
        "客流量_环比下降_关注": 0.10,   # 下降超10%
        "转化率_异常": 5.0,             # 变化超5个百分点
        "客单价_环比异常": 0.08,        # 变化超8%
        "毛利率_环比下降": 3.0,         # 下降超3个百分点
        "促销让利_占比过高": 15.0,      # 让利占比超15%
        "目标达成_差距大": 80.0,        # 达成率低于80%
        "目标达成_差距小": 90.0,        # 达成率低于90%
        "SKU动销率_偏低": 70.0,         # 低于70%
    }

    # 七大归因维度 → 判定逻辑 + 建议
    ATTRIBUTION_RULES = [
        {
            "归因维度": "客流不足",
            "优先级": "P0",
            "判定逻辑": "客流量环比下降超过10%，且非节假日/天气等外部因素",
            "典型整改方向": [
                "增加门店外立面/橱窗曝光度",
                "加大周边社区/商圈地推引流",
                "优化线上平台（美团/大众点评）曝光和评分",
                "策划小型引流活动（试吃/体验/限时特价）",
                "检查周边是否有新竞品开业",
            ],
        },
        {
            "归因维度": "成交转化率偏低",
            "优先级": "P0",
            "判定逻辑": "转化率低于行业基准或环比下降超5个百分点",
            "典型整改方向": [
                "加强导购服务培训，提升接待和促成能力",
                "优化商品陈列和动线设计",
                "检查价格竞争力，与竞品对标定价",
                "丰富SKU选择，避免顾客'找不到想要的'",
                "改善门店环境体验（灯光/音乐/整洁度）",
            ],
        },
        {
            "归因维度": "客单价下滑",
            "优先级": "P1",
            "判定逻辑": "客单价环比下降超8%",
            "典型整改方向": [
                "增加高单价/高毛利商品陈列和推荐",
                "设计套餐/组合装提升连带率",
                "检查核心高单价商品是否缺货",
                "减少不必要的低客单价促销",
                "针对高价值顾客推送专属优惠",
            ],
        },
        {
            "归因维度": "促销活动到期",
            "优先级": "P1",
            "判定逻辑": "促销期间业绩虚高，促销结束后显著回落",
            "典型整改方向": [
                "设计过渡期'软着陆'营销策略",
                "将促销客流转化为会员/私域",
                "优化促销节奏，避免大起大落",
                "评估促销ROI，淘汰低效促销",
            ],
        },
        {
            "归因维度": "商品缺货",
            "优先级": "P1",
            "判定逻辑": "核心品类/畅销品销量异常下降",
            "典型整改方向": [
                "紧急补货畅销品，缩短补货周期",
                "建立畅销品安全库存预警机制",
                "与供应商协商优先供货",
                "临时寻找替代品缓解缺货影响",
            ],
        },
        {
            "归因维度": "品类结构不合理",
            "优先级": "P2",
            "判定逻辑": "品类销售占比与行业标准或历史数据偏差大",
            "典型整改方向": [
                "缩减滞销品类SKU，释放陈列面积",
                "增加高增长品类SKU数和陈列面积",
                "优化品类组合，提升连带销售",
                "参考行业标杆调整品类结构",
            ],
        },
        {
            "归因维度": "折扣促销过度",
            "优先级": "P2",
            "判定逻辑": "促销让利占销售额超15%，毛利率显著下降",
            "典型整改方向": [
                "收紧促销折扣力度，设置底线折扣率",
                "限制折扣叠加（如折上折）",
                "将促销资源向高毛利品类倾斜",
                "用满减代替直接折扣，保护客单价",
            ],
        },
    ]

    def __init__(self, indicators: dict, summary: dict | None = None):
        self.indicators = indicators
        self.summary = summary or {}
        self.anomalies: list[dict] = []
        self.attributions: list[dict] = []

    # ─── 异常扫描 ───
    def scan_anomalies(self) -> list[dict]:
        """扫描所有异常"""
        self.anomalies = []

        # 1. 客流量异常
        self._check_traffic()

        # 2. 转化率异常
        self._check_conversion()

        # 3. 客单价异常
        self._check_avg_order()

        # 4. 毛利率异常
        self._check_margin()

        # 5. 促销让利异常
        self._check_promotion()

        # 6. 目标达成异常
        self._check_achievement()

        # 7. 品类异常（联动零售知识库）
        self._check_category()

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        self.anomalies.sort(key=lambda x: priority_order.get(x.get("优先级", "P2"), 2))

        return self.anomalies

    def _check_traffic(self):
        """检测客流量异常"""
        traffic = self.indicators.get("客流量", 0)
        conversion = self.indicators.get("成交转化率", 0)
        # 简化：若无基准数据，基于转化率判断
        if traffic == 0:
            return

        if conversion < 30:
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "客流量偏低（基于转化率反推）",
                "严重程度": "严重" if conversion < 20 else "关注",
                "优先级": "P0",
                "当前值": f"客流量约{traffic}人，转化率{conversion}%",
                "判定依据": f"转化率{conversion}%远低于行业基准",
            })

    def _check_conversion(self):
        """检测转化率异常"""
        conversion = self.indicators.get("成交转化率", 0)
        if conversion == 0:
            return

        # 行业基准参考
        benchmark = 40  # 默认基准40%
        if conversion < benchmark - 10:
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "成交转化率偏低",
                "严重程度": "严重" if conversion < benchmark - 15 else "关注",
                "优先级": "P0",
                "当前值": f"{conversion}%",
                "判定依据": f"转化率{conversion}%低于行业基准{benchmark}%超10个百分点",
            })

    def _check_avg_order(self):
        """检测客单价异常"""
        avg_order = self.indicators.get("客单价", 0)
        if avg_order == 0:
            return

        # 无历史基准时，标记数据以供后续分析
        self.indicators["_客单价_数据可用"] = True

    def _check_margin(self):
        """检测毛利率异常"""
        margin_data = self.indicators.get("毛利率", {})
        if isinstance(margin_data, dict):
            margin = margin_data.get("毛利率", 0)
        else:
            margin = margin_data

        if isinstance(margin, (int, float)) and 0 < margin < 25:
            cost_note = margin_data.get("成本_备注", "") if isinstance(margin_data, dict) else ""
            notes = f"（{cost_note}）" if cost_note and "估算" in cost_note else ""
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "毛利率偏低",
                "严重程度": "严重" if margin < 20 else "关注",
                "优先级": "P1",
                "当前值": f"{margin}%{notes}",
                "判定依据": f"毛利率{margin}%处于较低水平，需关注盈利能力",
            })

    def _check_promotion(self):
        """检测促销让利异常"""
        promo_ratio = self.indicators.get("促销让利占比", 0)
        if promo_ratio > self.THRESHOLDS["促销让利_占比过高"]:
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "促销让利占比过高",
                "严重程度": "严重" if promo_ratio > 25 else "关注",
                "优先级": "P1",
                "当前值": f"{promo_ratio}%",
                "判定依据": f"促销让利占比{promo_ratio}%超过安全线{self.THRESHOLDS['促销让利_占比过高']}%",
            })

    def _check_achievement(self):
        """检测目标达成异常"""
        achievement = self.indicators.get("业绩达成率", {})
        if isinstance(achievement, dict):
            rate = achievement.get("达成率", 0)
        else:
            rate = achievement

        if isinstance(rate, (int, float)) and 0 < rate < self.THRESHOLDS["目标达成_差距大"]:
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "业绩目标达成率严重偏低",
                "严重程度": "严重",
                "优先级": "P0",
                "当前值": f"{rate}%",
                "判定依据": f"达成率{rate}%低于{self.THRESHOLDS['目标达成_差距大']}%",
            })
        elif isinstance(rate, (int, float)) and rate < self.THRESHOLDS["目标达成_差距小"]:
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "业绩目标达成率偏低",
                "严重程度": "关注",
                "优先级": "P1",
                "当前值": f"{rate}%",
                "判定依据": f"达成率{rate}%低于{self.THRESHOLDS['目标达成_差距小']}%",
            })

    def _check_category(self):
        """检测品类结构异常"""
        cat_analysis = self.indicators.get("品类分析", [])
        if not cat_analysis or len(cat_analysis) < 2:
            return

        total = sum(c["销售额"] for c in cat_analysis)
        if total == 0:
            return

        # 检测品类集中度：TOP1品类占比超50%
        if cat_analysis[0]["占比"] > 50:
            self.anomalies.append({
                "异常编号": f"ANO-{len(self.anomalies)+1:03d}",
                "异常类型": "品类集中度过高",
                "严重程度": "关注",
                "优先级": "P2",
                "当前值": f"TOP1品类「{cat_analysis[0]['品类']}」占比{cat_analysis[0]['占比']}%",
                "判定依据": "单一品类占比超50%，经营风险分散不足",
            })

    # ─── 归因分析 ───
    def run_attribution(self) -> list[dict]:
        """基于异常和知识库进行归因分析"""
        self.attributions = []

        for anomaly in self.anomalies:
            # 匹配归因维度
            matched = self._match_attribution(anomaly)
            if matched:
                self.attributions.append({
                    "关联异常编号": anomaly["异常编号"],
                    "异常类型": anomaly["异常类型"],
                    "严重程度": anomaly["严重程度"],
                    "归因维度": matched["归因维度"],
                    "归因优先级": matched["优先级"],
                    "判定逻辑": matched["判定逻辑"],
                    "当前表现": anomaly["当前值"],
                    "整改方向": matched["典型整改方向"],
                })

        return self.attributions

    def _match_attribution(self, anomaly: dict) -> dict | None:
        """匹配异常到归因维度"""
        anomaly_type = anomaly.get("异常类型", "")

        mapping = {
            "客流量": "客流不足",
            "成交转化率": "成交转化率偏低",
            "客单价": "客单价下滑",
            "促销让利": "折扣促销过度",
            "毛利率": "折扣促销过度",
            "品类": "品类结构不合理",
            "目标达成": None,  # 目标达成需综合归因
        }

        for key, attribution_type in mapping.items():
            if key in anomaly_type and attribution_type:
                for rule in self.ATTRIBUTION_RULES:
                    if rule["归因维度"] == attribution_type:
                        return rule

        # 默认返回客流不足（业绩下滑主因）
        for rule in self.ATTRIBUTION_RULES:
            if rule["归因维度"] == "客流不足":
                return rule

        return None

    # ─── 综合结论 ───
    def generate_conclusion(self) -> dict:
        """生成综合诊断结论"""
        total_anomalies = len(self.anomalies)
        p0_count = sum(1 for a in self.anomalies if a.get("优先级") == "P0")
        p1_count = sum(1 for a in self.anomalies if a.get("优先级") == "P1")
        p2_count = sum(1 for a in self.anomalies if a.get("优先级") == "P2")

        # 判定整体经营健康度
        if p0_count >= 3:
            health = "预警 — 多项关键指标异常，需立即干预"
        elif p0_count >= 1:
            health = "关注 — 存在核心指标异常，需重点整改"
        elif p1_count >= 2:
            health = "一般 — 存在若干待优化项"
        else:
            health = "健康 — 经营状况总体正常"

        return {
            "经营健康度": health,
            "异常总数": total_anomalies,
            "P0严重异常": p0_count,
            "P1关注异常": p1_count,
            "P2提示异常": p2_count,
            "核心问题总结": self._summarize_core_issues(),
        }

    def _summarize_core_issues(self) -> list[str]:
        """总结核心问题"""
        issues = []
        for attr in self.attributions:
            issues.append(f"【{attr['归因优先级']}】{attr['归因维度']}：{attr['当前表现']}")
        return issues if issues else ["未检测到明显经营异常"]

    def run(self) -> dict:
        """执行全流程：扫描 → 归因 → 结论"""
        print("=" * 60)
        print("  零售经营异动智能归因诊断引擎")
        print("=" * 60)

        print("\n[SCAN] 扫描经营异常...")
        self.scan_anomalies()
        print(f"  发现 {len(self.anomalies)} 个异常")

        print("\n[ATTRIBUTION] 执行归因分析...")
        self.run_attribution()
        print(f"  完成 {len(self.attributions)} 项归因")

        conclusion = self.generate_conclusion()

        result = {
            "诊断时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "异常清单": self.anomalies,
            "归因分析": self.attributions,
            "综合结论": conclusion,
        }

        print(f"\n✅ 诊断完成！经营健康度: {conclusion['经营健康度']}")
        return result


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python anomaly_detector.py <indicators.json>")
        print("输入: data_processor.py 输出的 JSON 文件路径")
        print("输出: 异常诊断报告 JSON")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    indicators = data.get("经营指标", data)
    summary = data.get("数据汇总", {})

    detector = RetailAnomalyDetector(indicators, summary)
    result = detector.run()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
