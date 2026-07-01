#!/usr/bin/env python3
"""
零售数据清洗整合与指标计算引擎
零售一站式经营复盘 Skill — 步骤一

功能：
1. 多表自动识别与字段对齐
2. 数据去重、缺失补全、脏数据剔除
3. 跨表数据合并归一
4. 全套核心经营指标批量计算

输入：多个 Excel 文件路径列表
输出：标准化数据汇总表 JSON + 指标计算结果 JSON
"""

import json
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")


class RetailDataProcessor:
    """零售数据清洗整合与指标计算处理器"""

    # 表类型识别规则（按列名关键词匹配）
    TABLE_TYPE_PATTERNS = {
        "销售明细": ["商品", "单价", "数量", "金额", "销售", "sku", "product", "price", "qty", "amount"],
        "品类销售": ["品类", "类别", "category", "占比", "销售占比"],
        "时段销售": ["时段", "时间", "小时", "hour", "time", "period"],
        "外卖账单": ["外卖", "平台", "配送", "delivery", "platform", "美团", "饿了么"],
        "会员订单": ["会员", "member", "等级", "积分", "vip"],
        "门店业绩": ["门店", "目标", "达成", "店", "store", "target", "achievement"],
    }

    # 字段别名映射（统一标准化列名）
    # 支持精确匹配和包含匹配
    FIELD_ALIAS_MAP = {
        # 销售额相关
        "销售额": [
            "销售额", "销售金额", "成交金额", "实收金额", "实收销售金额", "门店实收金额",
            "amount", "sales_amount", "revenue", "total",
        ],
        # 销量相关
        "销量": [
            "销量", "销售数量", "件数", "数量", "有效订单数", "消费订单数",
            "qty", "quantity", "sales_qty", "count",
        ],
        # 商品相关
        "商品名": ["商品名称", "商品", "品名", "名称", "product", "product_name", "name", "item"],
        # 品类相关
        "品类": [
            "品类", "类别", "分类", "商品品类", "产品品类",
            "category", "type", "class",
        ],
        # 日期相关
        "日期": [
            "日期", "销售日期", "交易日期",
            "date", "sales_date", "transaction_date", "时间", "time",
        ],
        # 门店相关
        "门店": [
            "门店", "店铺", "分店", "门店名称",
            "store", "shop", "branch", "location",
        ],
        # 单价相关
        "单价": [
            "单价", "售价", "商品单价", "客单价",
            "price", "unit_price", "selling_price",
        ],
        # 成本相关
        "成本": [
            "成本", "成本价", "成本金额", "商品成本金额",
            "cost", "unit_cost", "purchase_price",
        ],
        # 会员相关
        "会员ID": ["会员ID", "会员号", "member_id", "vip_id", "customer_id"],
        # 订单相关
        "订单号": [
            "订单号", "交易号", "流水号",
            "order_id", "transaction_id", "bill_no",
        ],
        # 平台相关
        "平台": [
            "平台", "渠道", "外卖平台",
            "platform", "channel", "source",
        ],
        # 时段相关
        "时段": [
            "时段", "时间段", "小时段", "时段划分", "时段类型",
            "period", "time_slot",
        ],
        # 促销相关
        "促销让利": [
            "促销让利", "优惠金额", "折扣金额", "折扣率",
            "discount", "promotion", "coupon_amount",
        ],
        # 目标相关
        "目标销售额": [
            "目标", "目标销售额", "业绩目标", "月度业绩目标",
            "target", "goal", "budget",
        ],
        # 原价
        "原价销售额": [
            "原价", "原价销售金额", "原价销售总额",
            "original", "original_price",
        ],
        # 毛利率
        "毛利率": [
            "毛利率", "当月毛利率", "品类毛利率",
            "gross_margin", "margin_rate",
        ],
        # 毛利金额
        "毛利金额": [
            "毛利", "毛利金额", "外卖订单毛利",
            "gross_profit",
        ],
        # 会员相关扩展
        "是否会员": [
            "是否会员", "是否会员订单",
            "is_member", "is_vip",
        ],
        "会员等级": [
            "会员等级", "member_level", "vip_level",
        ],
    }

    def __init__(self, file_paths: list[str]):
        self.file_paths = [Path(p) for p in file_paths]
        self.raw_tables: dict[str, pd.DataFrame] = {}
        self.merged_data: pd.DataFrame | None = None
        self.indicators: dict = {}

    # ─── 步骤1：读取所有Excel ───
    def load_all_tables(self) -> dict[str, pd.DataFrame]:
        """读取所有Excel文件的所有sheet"""
        tables = {}
        for fp in self.file_paths:
            if not fp.exists():
                print(f"[WARN] 文件不存在: {fp}", file=sys.stderr)
                continue
            try:
                xls = pd.ExcelFile(fp)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(fp, sheet_name=sheet)
                    if df.empty or len(df.columns) < 2:
                        continue
                    key = f"{fp.stem}_{sheet}"
                    tables[key] = df
                    print(f"[LOAD] {key}: {df.shape[0]}行 × {df.shape[1]}列")
            except Exception as e:
                print(f"[ERROR] 读取 {fp} 失败: {e}", file=sys.stderr)
        self.raw_tables = tables
        return tables

    # ─── 步骤2：识别表类型 ───
    @staticmethod
    def identify_table_type(df: pd.DataFrame) -> str:
        """根据列名识别表类型"""
        cols_lower = " ".join(df.columns.astype(str).str.lower())
        scores = {}
        for ttype, keywords in RetailDataProcessor.TABLE_TYPE_PATTERNS.items():
            score = sum(1 for kw in keywords if kw.lower() in cols_lower)
            scores[ttype] = score
        if max(scores.values()) == 0:
            return "未识别"
        return max(scores, key=scores.get)

    # ─── 步骤3：标准化列名 ───
    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """将各表列名统一为标准名称（支持精确匹配和包含匹配）"""
        df = df.copy()
        rename_map = {}
        for col in df.columns:
            col_str = str(col).strip()
            col_lower = col_str.lower()
            for std_name, aliases in self.FIELD_ALIAS_MAP.items():
                # 精确匹配优先级最高
                if col_lower in [a.lower() for a in aliases]:
                    rename_map[col] = std_name
                    break
                # 包含匹配（兜底）
                for alias in aliases:
                    if alias.lower() in col_lower:
                        rename_map[col] = std_name
                        break
                if col in rename_map:
                    break
        if rename_map:
            # 去重：同一标准名多次出现时加后缀
            seen = set()
            final_map = {}
            for orig, std in rename_map.items():
                if std in seen:
                    # 跳过重复映射（保留第一次出现）
                    continue
                seen.add(std)
                final_map[orig] = std
            df = df.rename(columns=final_map)
        return df

    # ─── 步骤4：数据清洗 ───
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗：去重、剔除空行、处理缺失值、类型转换"""
        df = df.copy()

        # 删除全空行
        df = df.dropna(how="all")

        # 删除完全重复行
        df = df.drop_duplicates()

        # 处理重复列名
        if df.columns.duplicated().any():
            # 保留第一个出现的列
            df = df.loc[:, ~df.columns.duplicated()]

        # 日期列标准化
        for col in df.columns:
            if "日期" in str(col) or "date" in str(col).lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass

        # 数值列清洗
        for col in df.columns:
            col_series = df[col]
            if col_series.dtype == object:
                # 尝试转为数值（去除千分位逗号、¥符号等）
                try:
                    cleaned = col_series.astype(str).str.replace(r"[¥,，\s%]", "", regex=True)
                    df[col] = pd.to_numeric(cleaned, errors="coerce")
                except Exception:
                    pass

        return df

    # ─── 步骤5：跨表合并 ───
    def merge_tables(self) -> pd.DataFrame:
        """基于相同字段对齐，合并所有表"""
        processed = []
        for key, df in self.raw_tables.items():
            table_type = self.identify_table_type(df)
            df = self.normalize_columns(df)
            df = self.clean_dataframe(df)
            df["_来源表"] = key
            df["_表类型"] = table_type
            processed.append(df)
            print(f"[CLEAN] {key} → 类型: {table_type}, {df.shape[0]}行")

        if not processed:
            raise ValueError("无有效数据表可合并")

        # 尝试基于共同列合并
        # 策略：先按"日期"+"门店"合并销售类表，再合并汇总类表
        merge_keys = []
        common_cols = set.intersection(*[set(df.columns) for df in processed]) if len(processed) > 1 else set()

        for candidate in ["日期", "门店", "商品名", "品类", "订单号"]:
            if candidate in common_cols:
                merge_keys.append(candidate)

        # 将结果暂存为合并表：concat 所有表（保留各自列），并标记来源
        merged = pd.concat(processed, ignore_index=True, sort=False)

        # 按日期排序
        date_cols = [c for c in merged.columns if "日期" in str(c)]
        if date_cols:
            merged = merged.sort_values(date_cols[0]).reset_index(drop=True)

        self.merged_data = merged
        return merged

    # ─── 步骤6：指标计算 ───
    def calculate_indicators(self) -> dict:
        """基于合并数据计算全套核心经营指标"""
        if self.merged_data is None:
            raise ValueError("请先执行 merge_tables()")

        df = self.merged_data
        indicators = {}

        # --- 基础汇总 ---
        indicators["总销售额"] = self._safe_sum(df, ["销售额", "金额"])
        indicators["总销量"] = self._safe_sum(df, ["销量", "数量"])
        indicators["成交笔数"] = self._safe_count_unique(df, ["订单号"])

        # --- 日期范围 ---
        date_col = self._find_col(df, ["日期"])
        if date_col and pd.api.types.is_datetime64_any_dtype(df[date_col]):
            indicators["数据起始日期"] = df[date_col].min().strftime("%Y-%m-%d")
            indicators["数据截止日期"] = df[date_col].max().strftime("%Y-%m-%d")
            indicators["统计天数"] = (df[date_col].max() - df[date_col].min()).days + 1

        # --- 客单价 ---
        indicators["客单价"] = (
            round(indicators["总销售额"] / indicators["成交笔数"], 2)
            if indicators["成交笔数"] > 0
            else 0
        )

        # --- 客流量（如有直接数据；否则基于转化率反推） ---
        traffic_col = self._find_col(df, ["客流量", "进店人数"])
        if traffic_col:
            indicators["客流量"] = self._safe_sum(df, ["客流量", "进店人数"])
        else:
            # 反推：假设行业平均转化率50%
            indicators["客流量"] = int(indicators["成交笔数"] / 0.5) if indicators["成交笔数"] > 0 else 0
            indicators["客流量_备注"] = "基于默认转化率50%反推，仅供参考"

        # --- 转化率 ---
        indicators["成交转化率"] = (
            round(indicators["成交笔数"] / indicators["客流量"] * 100, 2)
            if indicators["客流量"] > 0
            else 0
        )

        # --- 连带率 ---
        indicators["连带率"] = (
            round(indicators["总销量"] / indicators["成交笔数"], 2)
            if indicators["成交笔数"] > 0
            else 0
        )

        # --- 毛利率 ---
        indicators["毛利率"] = self._calc_gross_margin(df)

        # --- 促销让利 ---
        indicators["促销让利总额"] = self._safe_sum(df, ["促销让利", "优惠金额", "折扣金额"])
        indicators["促销让利占比"] = (
            round(indicators["促销让利总额"] / indicators["总销售额"] * 100, 2)
            if indicators["总销售额"] > 0
            else 0
        )

        # --- 品类分析 ---
        indicators["品类分析"] = self._calc_category_analysis(df)

        # --- 时段分析 ---
        indicators["时段分析"] = self._calc_period_analysis(df)

        # --- 门店维度 ---
        indicators["门店维度"] = self._calc_store_analysis(df)

        # --- 会员分析 ---
        indicators["会员分析"] = self._calc_member_analysis(df)

        # --- 业绩达成率 ---
        indicators["业绩达成率"] = self._calc_achievement_rate(df)

        self.indicators = indicators
        return indicators

    # ─── 辅助方法 ───
    def _find_col(self, df: pd.DataFrame, candidates: list[str]) -> str | None:
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def _safe_sum(self, df: pd.DataFrame, candidates: list[str]) -> float:
        col = self._find_col(df, candidates)
        if col:
            return round(df[col].sum(skipna=True), 2)
        return 0.0

    def _safe_count_unique(self, df: pd.DataFrame, candidates: list[str]) -> int:
        col = self._find_col(df, candidates)
        if col:
            return int(df[col].nunique())
        return 0

    def _calc_gross_margin(self, df: pd.DataFrame) -> dict:
        """计算毛利率"""
        result = {"毛利率": 0.0, "销售成本": 0.0}
        sales = self._safe_sum(df, ["销售额", "金额"])
        cost = self._safe_sum(df, ["成本"])

        if cost == 0 and sales > 0:
            # 无成本数据时，按行业标准估算
            cost_ratio = 0.55  # 默认55%成本率
            cost = sales * cost_ratio
            result["成本_备注"] = "无成本数据，按55%行业均值估算"

        result["销售成本"] = round(cost, 2)
        result["毛利率"] = round((sales - cost) / sales * 100, 2) if sales > 0 else 0.0
        return result

    def _calc_category_analysis(self, df: pd.DataFrame) -> list[dict]:
        """品类销售分析"""
        cat_col = self._find_col(df, ["品类"])
        sales_col = self._find_col(df, ["销售额", "金额"])
        if not cat_col or not sales_col:
            return []

        cat_data = df.groupby(cat_col)[sales_col].sum().sort_values(ascending=False)
        total = cat_data.sum()
        return [
            {
                "品类": str(cat),
                "销售额": round(val, 2),
                "占比": round(val / total * 100, 2) if total > 0 else 0,
            }
            for cat, val in cat_data.items()
        ]

    def _calc_period_analysis(self, df: pd.DataFrame) -> list[dict]:
        """时段销售分析"""
        period_col = self._find_col(df, ["时段"])
        sales_col = self._find_col(df, ["销售额", "金额"])
        if not period_col or not sales_col:
            return []

        period_data = df.groupby(period_col)[sales_col].sum().sort_values(ascending=False)
        total = period_data.sum()
        return [
            {
                "时段": str(p),
                "销售额": round(val, 2),
                "占比": round(val / total * 100, 2) if total > 0 else 0,
            }
            for p, val in period_data.items()
        ]

    def _calc_store_analysis(self, df: pd.DataFrame) -> list[dict]:
        """门店维度分析"""
        store_col = self._find_col(df, ["门店"])
        sales_col = self._find_col(df, ["销售额", "金额"])
        if not store_col or not sales_col:
            return []

        store_data = df.groupby(store_col)[sales_col].sum().sort_values(ascending=False)
        total = store_data.sum()
        return [
            {
                "门店": str(s),
                "销售额": round(val, 2),
                "占比": round(val / total * 100, 2) if total > 0 else 0,
            }
            for s, val in store_data.items()
        ]

    def _calc_member_analysis(self, df: pd.DataFrame) -> dict:
        """会员消费分析"""
        member_col = self._find_col(df, ["会员ID"])
        sales_col = self._find_col(df, ["销售额", "金额"])
        order_col = self._find_col(df, ["订单号"])

        result = {"会员消费占比": 0.0, "会员客单价": 0.0, "会员数量": 0}

        if member_col and sales_col:
            member_mask = df[member_col].notna() & (df[member_col] != "")
            member_sales = df.loc[member_mask, sales_col].sum()
            total_sales = self._safe_sum(df, ["销售额", "金额"])
            result["会员消费占比"] = round(member_sales / total_sales * 100, 2) if total_sales > 0 else 0.0
            result["会员数量"] = int(df.loc[member_mask, member_col].nunique())

            if order_col and member_mask.any():
                member_orders = df.loc[member_mask, order_col].nunique()
                result["会员客单价"] = round(member_sales / member_orders, 2) if member_orders > 0 else 0.0

        return result

    def _calc_achievement_rate(self, df: pd.DataFrame) -> dict:
        """业绩目标达成率"""
        sales = self._safe_sum(df, ["销售额", "金额"])
        target_col = self._find_col(df, ["目标销售额"])
        if target_col and not df[target_col].isna().all():
            target = df[target_col].sum()
            rate = round(sales / target * 100, 2) if target > 0 else 0
        else:
            target = 0
            rate = 0
        return {"目标销售额": round(target, 2), "实际销售额": round(sales, 2), "达成率": rate}

    # ─── 汇总输出 ───
    def export_summary(self) -> dict:
        """输出标准化汇总数据"""
        if self.merged_data is None:
            raise ValueError("请先执行 merge_tables()")

        df = self.merged_data
        return {
            "数据总行数": len(df),
            "数据总列数": len(df.columns),
            "涉及表数": df["_来源表"].nunique() if "_来源表" in df.columns else 0,
            "表类型分布": df["_表类型"].value_counts().to_dict() if "_表类型" in df.columns else {},
            "字段列表": [c for c in df.columns if not c.startswith("_")],
            "示例数据": df.head(5).to_dict(orient="records") if not df.empty else [],
        }

    def run(self) -> dict:
        """执行全流程：加载→清洗→合并→计算→输出"""
        print("=" * 60)
        print("  零售数据清洗整合与指标计算引擎")
        print("=" * 60)

        # 1. 加载
        print("\n[STEP 1] 加载数据表...")
        self.load_all_tables()
        if not self.raw_tables:
            return {"error": "未加载到任何有效数据表"}

        # 2. 合并
        print("\n[STEP 2] 清洗与合并...")
        self.merge_tables()

        # 3. 计算
        print("\n[STEP 3] 计算经营指标...")
        self.calculate_indicators()

        # 4. 汇总
        summary = self.export_summary()

        result = {
            "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "输入文件数": len(self.file_paths),
            "数据汇总": summary,
            "经营指标": self.indicators,
        }

        print("\n✅ 数据处理完成！")
        return result


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python data_processor.py <excel_file1> [excel_file2 ...]")
        print("输出: JSON 格式的汇总数据与指标计算结果")
        sys.exit(1)

    processor = RetailDataProcessor(sys.argv[1:])
    result = processor.run()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
