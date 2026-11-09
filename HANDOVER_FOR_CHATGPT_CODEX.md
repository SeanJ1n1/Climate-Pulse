# Climate Pulse — 交接给 ChatGPT / Codex（系统总结）

- **生成时间**：2026-11-09（Asia/Singapore）
- **交出方**：Population Intelligence（Grok Bot）
- **接收方**：ChatGPT / Codex（或任意续作 agent）
- **用户**：Xin Jin / Kin Seann（CUHK）· 偏好中文；代码、metrics 键名、文件名保持英文
- **比赛**：UNFPA PopIntel Hack · Track 1 Climate Pulse  
  官网：https://pdp.unfpa.org/popInthackathon/  
  真 PDP：https://pdp.unfpa.org/

---

## 0. 一页启动指令（可原样粘贴）

```
你在接着做 UNFPA PopIntel Hack Track 1：Climate Pulse。
用户 Xin Jin / Kin Seann（CUHK）。写说明用中文；代码/metrics/路径用英文。

先读并遵守：
1) 本文件全文（HANDOVER_FOR_CHATGPT_CODEX.md）
2) 官网 Track 1 原文：https://pdp.unfpa.org/popInthackathon/
3) 开源包 README + docs/OFFICIAL_ALIGNMENT.md + docs/METHOD.md
4) 缺口唯一对照（仅公开可核）：outputs/climate_pulse_gap_matrix_v2_webverified/gap_matrix_webverified.json

硬规则：
- 数字只从代码 → metrics.json；MD 表由脚本从 JSON 生成；禁止手写数字。
- 不得声称未测量指标；CI∋0 不得写成 lift。
- 训练窗拟合；滚动原点；防泄漏断言必须过。
- 肯尼亚为主；association ≠ causation；可解释方法优先。
- DIOS = 媒体早期信号弱标签，不是位移金标准 Y。
- 缺口表只许对照官网/已核公开材料；禁止自加条款（用户纠正：检索网上信息，不要盲目瞎加）。
- 不擅自公开仓库、改分享、发邮件、购买、对外提交；需用户单独授权。
- ArcGIS 现为 Owner-only；样例 PDP+ 是 unofficial 静态壳，不是真 PDP+。
- 仓 https://github.com/SeanJ1n1/Climate-Pulse 当前 private、has_pages=false；改 Public/开 Pages 只能用户在 GitHub UI 做。

当前 HEAD（main）：3873e9426bb856f50b7f9226ef7a9453e67d0bc6
（Nest Climate Pulse under Visualizations；顶栏仅 Indicator viewer | Metadata | Visualizations）

默认：先确认已接上 + 列出你建议的下一刀；等用户点头再改大范围。
```

---

## 1. 产品主张（可对外说什么 / 不能说什么）

| 可主张 | 不可主张 |
|---|---|
| Admin-2（及 ADM1）人口压力 / climate-demographic **risk score**（原型加权） | 已验证的 **位移** 2–4 周预警 P/R |
| Hazard（EO/SPI）× Exposure（WorldPop）× Signal（DIOS 媒体 + modes）融合演示 | 因果、概率、业务操作阈值已校准 |
| Esri Dashboard 已部署（Owner-only） | Country pilot active |
| 样例门户把 Climate Pulse **嵌进仿 PDP 壳** | 已写入真实 PDP+ / 国家工作流 |
| 代码已在 GitHub（MIT），内容在仓 | 对外开源已完成（仓仍 private） |

产品一句话：**Admin-2 人口压力升级信号（2–4 周视野）**；气候–人口风险 **有**；NDMA 压力代理 **条件可测**；实际位移 **尚未**。

---

## 2. 官网 Track 1 原文（必须对齐）

**四组件：**
1. Climate Risk Layer — EO datasets standardised into Admin-2 grid  
2. Population Exposure Engine — WorldPop age-sex overlay  
3. DIOS Early Signal Layer — 2–4 week displacement warning  
4. Esri Operational Dashboard — ArcGIS Experience Builder  

**四月交付：** Climate-Demographic Risk Score at Admin-2, Esri dashboard deployed, Country pilot active, Code open-sourced  

（全局：tools integrated into PDP+ and country workflows）

---

## 3. 当前完成度（对照官网，2026-11-09 核对）

| # | 要求 | 状态 | 现状要点 |
|---|---|---|---|
| 1 | EO → Admin-2 | 部分满足 | CHIRPS/SPI-3；KEN 较完整；ADM2 未全覆盖独立长气候态；IND SPI 弱 |
| 2 | WorldPop age-sex | 部分满足 | KEN 有空间化 age-sex；NGA/MEX/IND ≈ 全国份额×总量 |
| 3 | DIOS 2–4w displacement | 部分满足 | KEN all-topics 媒体信号；NGA/MEX fertility-only；IND 无 DIOS；**位移 P/R 未建** |
| 4 | Dashboard / Experience | 部分满足 | Dashboard：KE/NGA/MEX/IND/Multi4/KE Stress；Experience **仅 KE**（他国 site_error） |
| 5 | Risk Score Admin-2 | 部分满足 | H×E×S 原型分；ADM1 为主、ADM2 部分 |
| 6 | Dashboard deployed | **已满足** | Owner-only 多套已上线 |
| 7 | Country pilot active | **缺口** | 无国家办使用证据 |
| 8 | Code open-sourced | **缺口/部分** | 仓有 MIT 内容；**private + has_pages=false** |
| 9 | 接入 PDP+ | **缺口** | 仅仿 PDP 样例壳 + ArcGIS 链 |
| 10 | 邮件 ~60% P 等 | 来源未核实 | 公开网页无原文；勿当硬门槛 |

**一句话：** 演示链（Dashboard + 嵌套 PDP 样例 + 代码仓）基本齐；卡点是 **Public/Pages、评审可见 ArcGIS、Country pilot、真 PDP+、位移金标准**。

---

## 4. 风险分公式（原型权重）

```
climate_demographic_risk_score =
    0.40 * hazard_score
  + 0.35 * exposure_score
  + 0.25 * signal_score

signal_score = 0.70 * signal_dios + 0.30 * signal_modes   # 有 DIOS 时
```

细节：`docs/METHOD.md`（开源包内）。

---

## 5. 关键路径与仓库

### 5.1 GitHub（权威开源交付物）

- URL：https://github.com/SeanJ1n1/Climate-Pulse  
- Branch：`main`  
- HEAD：`3873e9426bb856f50b7f9226ef7a9453e67d0bc6`  
- License：MIT  
- **private=true，has_pages=false**（API 改可见性/Pages → 403；**必须用户在 GitHub Settings 改**）  
- Pages 开启后样例 URL（预期）：  
  https://seanj1n1.github.io/Climate-Pulse/pdp-plus-sample/  
  设置：Settings → Pages → Deploy from branch → `main` / root（仓库根，非 /docs）

### 5.2 用户本机（Mac，machine `73eba990-…`）

根目录（注意 Windows 风格嵌在 macOS 路径里）：

```
/Users/jinxin/D:/Jin_Xin/unfpa-dios/
```

关键子路径：

| 路径 | 内容 |
|---|---|
| `outputs/climate_pulse_oss_v1/` | 开源包（与 GH 同步源） |
| `outputs/climate_pulse_oss_v1/pdp-plus-sample/` | 仿 PDP 嵌套样例 |
| `outputs/climate_pulse_oss_v1.zip` | 打包副本 |
| `outputs/climate_pulse_gap_matrix_v2_webverified/` | 官网核对缺口表 |
| `outputs/climate_pulse_dashboard/` | KE 本地层 / 预览 |
| `prototype/` | 肯尼亚验证原型（metrics、滚动评估） |
| `HANDOVER_FOR_NEXT_AGENT.md` | 旧交接（偏 main_cc_checks；**勿当最新产品状态**） |
| `HANDOVER_FOR_CHATGPT_CODEX.md` | **本文件** |

打开样例：

```bash
open "/Users/jinxin/D:/Jin_Xin/unfpa-dios/outputs/climate_pulse_oss_v1/pdp-plus-sample/index.html"
```

### 5.3 开发机 / 共享 box（若仍可访问）

```
/workspace/unfpa-dios/
```

结构同上。旧实验交接仍见 `HANDOVER_FOR_NEXT_AGENT.md`（原型尺子、`main_cc_checks_v1`）。

---

## 6. ArcGIS（全部 Owner-only · Africa GeoPortal）

| Item | URL |
|---|---|
| KE Dashboard | https://africageoportal.maps.arcgis.com/apps/dashboards/d1fd5155dc8c49c5b3873671fedc4c29 |
| KE Experience | https://experience.arcgis.com/experience/6da4c9d0cee24a54b7ddf310d64f456f |
| KE Stress Dashboard | https://africageoportal.maps.arcgis.com/apps/dashboards/4ac53ce375a5458a8a9d60d5ef609d95 |
| IND Dashboard | https://africageoportal.maps.arcgis.com/apps/dashboards/e50244312abd4e6188f477745aa0a538 |
| NGA Dashboard | https://africageoportal.maps.arcgis.com/apps/dashboards/e171cde9fdbb4e7c90aabf6c763bd71e |
| MEX Dashboard | https://africageoportal.maps.arcgis.com/apps/dashboards/5c115185be254e958da415b32e89ea56 |
| Multi4 Dashboard | https://africageoportal.maps.arcgis.com/apps/dashboards/875dcdccb58c4cd68add56a34d301d91 |
| Multi4 Web Map | https://africageoportal.maps.arcgis.com/home/item.html?id=5c054a072dd14ffcadcfc7b35cc9a53b |

评审可见需用户放宽分享。多国 Experience：`experience.arcgis.com` 曾持续 site_error / 超时，勿空转硬建。

---

## 7. 样例 PDP+（unofficial）架构要点

- 静态 SPA：`index.html` + `styles.css` + `app.js`，hash 路由  
- **顶栏仅三项**（对齐真 PDP）：Indicator viewer | Metadata | Visualizations  
- Climate Pulse **不**占顶栏；入口：  
  - Visualizations 卡片  
  - Demographic Intelligence / More resources  
  - Kenya viewer CTA  
- 路由：`#/climate-pulse`；breadcrumb：Home / Visualizations / Climate Pulse  
- 强调色参考真站：`#ED6A1F`  
- 持久 **UNOFFICIAL DEMO** 横幅；无 UNFPA logo 文件  
- 内嵌 Owner-only ArcGIS 链接 + 本地 KE 预览图  
- **不是**生产 PDP+；无写入权限

真站导航对照：https://pdp.unfpa.org/#/ （仅三栏；Climate/Flood 等在 Visualizations 卡片里）

---

## 8. 开源包目录（Climate-Pulse 仓根）

```
README.md
LICENSE                 # MIT
requirements.txt
.gitignore
.nojekyll               # 为 Pages
COMPLETION_STATUS_ZH.md
scripts/
  build_climate_pulse_layers.py      # KE
  build_climate_pulse_country.py     # NGA/MEX/IND
docs/
  OFFICIAL_ALIGNMENT.md
  METHOD.md
  ARCGIS_ITEMS.md
pdp-plus-sample/
  index.html, styles.css, app.js, README.md, assets/
demo_data/              # 合成烟测
examples/               # 小样例表
sources/gap_matrix_webverified.json
```

**未打包：** AGOL token、大栅格/NetCDF、受限 DIOS dump、密钥。

---

## 9. 方法 / 验证侧（勿混进「官网缺口」）

这些是团队自加实验，**不是**官网逐字条款（已从 gap v2 剔除）：

- DIOS 消融 M0/M1/M2  
- 印度 PDFM Search/Maps/Weather 分块  
- NDMA/IPC 双验证（缺位移真值时的代理）  
- PIT / 防泄漏协议细节  
- Multi4 四国合图（产品选择）  

肯尼亚原型尺子与硬规则细节见旧文件 `HANDOVER_FOR_NEXT_AGENT.md`（`prototype/`，`main_cc_checks_v1`）。**产品交付状态以本文件 + gap v2 为准。**

位移全国级 P/R：`NOT_ELIGIBLE`（无可用金标准 Y）。  
`lead_weeks_claim=false`（未用带日期周尺度 EO 实测时不得报周提前量）。

---

## 10. 建议下一刀（按优先级）

### A. 仅用户能做（阻塞「开源完成」）

1. GitHub → Climate-Pulse → **Public**  
2. Settings → Pages → `main` / **root**  
3. 验证 https://seanj1n1.github.io/Climate-Pulse/pdp-plus-sample/  
4. （可选）ArcGIS 项对评审账号/组织只读分享  

### B. Codex 可继续做的技术项（需用户点头）

1. 加强 KEN **独立 ADM2** hazard + available_as_of 完整性  
2. 非 KEN 真 WorldPop age-sex overlay（体量大，先 KEN 加深也可）  
3. 样例页视觉/真地图交互（仍弱于真 PDP；假地球→可嵌入公开底图或 iframe 策略）  
4. 重试多国 Experience（若 Esri 站点恢复）  
5. 文档：把 gap 行 8 在 Public 后改为「已满足」，同步 OFFICIAL_ALIGNMENT / COMPLETION_STATUS  

### C. 外部 / 勿假装完成

- Country pilot（国家办）  
- 真 PDP+ 写入（UNFPA 平台权限）  
- DIOS 位移 2–4 周可测 P/R（需金标准）  
- 邮件 ~60% precision（需邮件原文才能升格）  

---

## 11. 禁区与用户约束

- 不购买、不公开分享、不对外发邮件/投稿，除非用户**单独**授权  
- 不把私人 ArcGIS / DIOS dump 塞进公开仓  
- 不复述 v0.1 泄漏前的虚高 P/R  
- 缺口表禁止「自加条款」；只核官网与已抓公开页  
- 解读：association ≠ causation；分数 ≠ 概率  

---

## 12. 给 Codex 的最小验收清单

接手前先勾：

- [ ] 已读官网 Track 1 四组件 + 四月交付原文  
- [ ] 已打开 `gap_matrix_webverified.json`，知道 缺口 vs 部分满足  
- [ ] 已确认 GH `private=true` / `has_pages=false` / HEAD=`3873e94…`  
- [ ] 已本地打开 `pdp-plus-sample/index.html`，确认顶栏三项、Climate Pulse 嵌套入口  
- [ ] 未把 Multi4/PDFM/邮件60% 当成官网硬要求  
- [ ] 下一动作已写成「建议」等用户确认（除非用户说直接做某项）  

---

## 13. 相关链接速查

- 官网 Track：https://pdp.unfpa.org/popInthackathon/  
- 真 PDP：https://pdp.unfpa.org/  
- 仓：https://github.com/SeanJ1n1/Climate-Pulse  
- 最新嵌套提交：https://github.com/SeanJ1n1/Climate-Pulse/commit/3873e9426bb856f50b7f9226ef7a9453e67d0bc6  
- DIOS Looker（补数用）：https://unfpa-looker-web-app-126183358624.us-east1.run.app/dashboard  

---

*本交接取代产品侧口头状态；旧 `HANDOVER_FOR_NEXT_AGENT.md` 仅保留原型实验语境。*
