# 品牌配置指南

## 概述

品牌配置文件 `assets/brand-config.json` 是零售营销材料生成的核心配置。生成推文和海报时，读取此文件获取品牌视觉和文案信息，自动套用到输出中。

## 配置字段说明

### brand — 品牌基础信息

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 品牌中文名称，用于标题、水印等位置 |
| slogan | string | 否 | 品牌口号，可用于推文底部签名区 |
| logo_url | string | 否 | Logo 图片 URL（支持 http/https） |
| logo_alt_text | string | 否 | Logo 图片加载失败时的替代文本 |

### colors — 品牌色系

| 字段 | 说明 | 用途 |
|------|------|------|
| primary | 主色 | 按钮、标题强调、CTA 区域 |
| primary_light | 主色浅色 | 背景色块、标签 |
| primary_dark | 主色深色 | 渐变色终点、hover 态 |
| secondary | 辅色 | 次要强调元素 |
| accent | 强调色 | 价格标签、卖点图标 |
| background | 页面背景 | 推文/海报整体背景 |
| text | 正文文字 | 段落文字 |
| text_light | 浅色文字 | 辅助说明、时间日期 |
| white | 白色 | 卡片背景、留白区域 |
| border | 边框色 | 分割线、卡片边框 |

### typography — 字体配置

所有字段均为 CSS font-family 格式。默认使用苹方/微软雅黑，适配中文阅读。

| 字段 | 说明 | 默认值 |
|------|------|--------|
| title_font | 标题字体 | PingFang SC, Microsoft YaHei, sans-serif |
| body_font | 正文字体 | 同上 |
| title_size | 主标题字号 | 20px |
| heading_size | 小标题字号 | 17px |
| body_size | 正文字号 | 15px |
| caption_size | 辅助文字字号 | 12px |

### contact — 联系与转化

| 字段 | 说明 | 用途 |
|------|------|------|
| phone | 客服电话 | 推文底部 |
| wechat_qr_url | 公众号/企微二维码 | 海报引导关注区 |
| mini_program_name | 小程序名称 | CTA 跳转提醒 |
| mini_program_path | 小程序路径 | 跳转链接（文章内使用文本提示） |
| store_address | 门店地址 | 到店引导 |

### social — 社交媒体

| 字段 | 说明 |
|------|------|
| official_account_name | 公众号名称，用于推文顶部引导关注 |

## 使用流程

1. **首次使用**：将 `brand-config.json` 中的示例值替换为实际品牌信息
2. **多品牌切换**：可创建多个配置副本，如 `brand-config-品牌A.json`
3. **生成时读取**：skill 触发时自动读取品牌配置并注入模板
4. **品牌色策略**：如果主色过亮（HSL lightness > 80），正文文字自动避让为深色；主色过暗（< 20），标题区自动使用浅色文字

## 配置示例（运动服饰品牌）

```json
{
  "brand": {
    "name": "跃动体育",
    "slogan": "每一步都精彩",
    "logo_url": "https://example.com/yuedong-logo.png"
  },
  "colors": {
    "primary": "#FF6B35",
    "secondary": "#004E89",
    "accent": "#FFD166"
  }
}
```
