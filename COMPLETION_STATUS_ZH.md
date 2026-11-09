# Climate Pulse 本轮完成状态（OSS + 样例 PDP+）

生成时区：Asia/Singapore · 2026-11-09

## 本轮已完成

1. **开源包**
   - 路径：`outputs/climate_pulse_oss_v1/`
   - MIT License、README、.gitignore、requirements.txt
   - 脱敏脚本：`scripts/build_climate_pulse_layers.py`、`build_climate_pulse_country.py`
   - 文档：`docs/OFFICIAL_ALIGNMENT.md`、`METHOD.md`、`ARCGIS_ITEMS.md`
   - 合成烟测数据 + 小样例 CSV；未打包大栅格 / 受限 DIOS dump

2. **样例 PDP+ 页**
   - `pdp-plus-sample/index.html`（+ CSS/JS）
   - 标注 unofficial demo；已挂 Owner-only ArcGIS 链接与本地预览图

3. **缺口说明**在样例页第 6 节与本文件。

## 用户侧设置

- 仓库：https://github.com/SeanJ1n1/Climate-Pulse
- Commit（main）：`4a8f3007bdebea7029d10b7af7830cfae0e01c97`
- 若仓库为 private：改为 Public 后才算完整对外开源；Pages 需 Settings → Pages → `main` / root
- Pages 开启后样例页：https://seanj1n1.github.io/Climate-Pulse/pdp-plus-sample/

## 仍未完成

| 项 | 原因 |
|---|---|
| Country pilot active | 需 UNFPA / 国家办参与与证据 |
| 多国 Experience Builder | experience.arcgis.com 超时/错误 |
| DIOS 可测 2–4 周位移预警 P/R | 无位移金标准 Y |
| 邮件 ~60% precision | 公开网页未核实 |
| 非 KEN 真正 WorldPop age-sex overlay | 需大体积年龄性别栅格 |
| 真实写入 PDP+ 生产环境 | 无平台写入权限；仅有样例页 |

## 打开样例页

```text
outputs/climate_pulse_oss_v1/pdp-plus-sample/index.html
```

## 2026-11-09 · PDP-mimic sample rebuild

- `pdp-plus-sample/` rewritten as unofficial PDP layout-inspired SPA (hash routes: home / viewer / climate-pulse / visualizations / metadata).
- Climate Pulse wired as Demographic Intelligence module with Owner-only ArcGIS Open buttons + Kenya local previews.
- Persistent UNOFFICIAL DEMO banner; text wordmark only (no UNFPA logo files); not production PDP.
- Open: `outputs/climate_pulse_oss_v1/pdp-plus-sample/index.html` then use nav or `#/climate-pulse`.

## 2026-11-09 · PDP nesting polish

- Climate Pulse no longer a top-nav product tab; top bar matches real PDP (Indicator viewer · Metadata · Visualizations only).
- Module reached via Visualizations card, Demographic Intelligence / More resources, and Kenya viewer CTA; `#/climate-pulse` keeps Visualizations nav active; breadcrumb `Home / Visualizations / Climate Pulse`.

