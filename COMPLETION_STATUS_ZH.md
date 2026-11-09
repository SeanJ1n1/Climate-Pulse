# Climate Pulse 完成状态（OSS + 样例 PDP+）

生成时区：Asia/Singapore · 2026-11-09

## 已包含

1. **开源包**
   - MIT License、README、.gitignore、requirements.txt
   - 脚本：`scripts/build_climate_pulse_layers.py`、`build_climate_pulse_country.py`（相对路径，不含 token 或密码）
   - 文档：`docs/OFFICIAL_ALIGNMENT.md`（依据 webverified JSON）、`METHOD.md`、`ARCGIS_ITEMS.md`
   - 合成烟测数据与小样例 CSV。未包含大栅格和受限 DIOS dump。

2. **样例 PDP+ 页面**（unofficial demo）
   - `pdp-plus-sample/index.html`（及 CSS/JS）
   - 非 UNFPA 托管，不是生产 PDP+
   - Owner-only ArcGIS Dashboard / Experience / Multi4 链接
   - 本地预览 PNG 在 `assets/`

3. 缺口见下表，以及样例页第 6 节。

## 仍未完成

| 项 | 原因 |
|---|---|
| Country pilot active | 需 UNFPA / 国家办参与与证据 |
| 多国 Experience Builder | experience.arcgis.com 历史 site_error / 超时 |
| DIOS 作为可测 2–4 周位移预警的 precision/recall | 无位移金标准 |
| 邮件 ~60% precision | 公开网页未核实 |
| 非 KEN 的 WorldPop age-sex overlay | 需大体积年龄性别栅格；本轮未下载 |
| 写入 PDP+ 生产环境 | 无 UNFPA 平台写入权限；现有为样例页 |
| Code open-sourced（公开发布） | 代码在本仓库；仓库若仍为 private，则尚未构成公开开源 |

## 打开样例页

```text
pdp-plus-sample/index.html
```

浏览器直接打开，或任意静态站点托管。
