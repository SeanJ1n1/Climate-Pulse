# Official alignment (web-verified)
Source of truth for this table: `sources/gap_matrix_webverified.json` (revision `v2_webverified`, generated from live fetch of https://pdp.unfpa.org/popInthackathon/).

Do not treat rows marked 来源未核实 as official public requirements.

## Official components (verbatim)

- Climate Risk Layer — EO datasets standardised into Admin-2 grid
- Population Exposure Engine — WorldPop age-sex overlay
- DIOS Early Signal Layer — 2–4 week displacement warning
- Esri Operational Dashboard — ArcGIS Experience Builder

**Four-month deliverable:** Climate-Demographic Risk Score at Admin-2, Esri dashboard deployed, Country pilot active, Code open-sourced

## Status table

| # | Requirement | Status | Current | Gap |
|---|---|---|---|---|
| 1 | Climate Risk Layer — EO → Admin-2 | 部分满足 | CHIRPS/SPI-3 等本地 hazard；KEN/NGA/MEX/IND 有层；ADM2 部分仍继承/非全覆盖独立长参考 | 官网要求 EO 标准化到 Admin-2；独立 ADM2 hazard + available_at 未全覆盖；IND SPI 缺长气候态 |
| 2 | WorldPop age-sex Exposure | 部分满足 | KEN scientific_v2 有空间化年龄性别栅格；NGA/MEX/IND 多为全国份额×总量 | 非肯尼亚国家仍非真正 WorldPop age-sex overlay |
| 3 | DIOS Early Signal（2–4 week displacement warning） | 部分满足 | KEN 有 all-topics DIOS 媒体量信号；NGA/MEX fertility-only；IND 无 DIOS。位移预警 P/R 未建立 | 官网写的是 2–4 周 displacement warning；当前 DIOS 是媒体早期信号层，尚未验证为可测位移预警 |
| 4 | Esri Operational Dashboard / Experience Builder | 部分满足 | 私人 Dashboard：KE/NGA/MEX/IND/Multi4/KE Stress 已上线；Experience 仅 KE 有，其余 site_error | 官网把 Dashboard 与 Experience Builder 写在同一条；多国 Experience 因 experience.arcgis.com 超时未建 |
| 5 | Climate-Demographic Risk Score at Admin-2 | 部分满足 | 有 H×E×S 合成分与 Stress 层（演示权重）；主要可交付为 ADM1/部分 ADM2 | 分数为原型加权，不得标概率；Admin-2 完整独立评分未全覆盖 |
| 6 | Esri dashboard deployed | 已满足 | 多套 Owner-only Dashboard 已部署（Xin Jin） | 仍为私人部署；公开/国家办可见部署需另定分享 |
| 7 | Country pilot active | 缺口 | 无私有证据表明国家办/试点用户正在使用并反馈 | 官网要求 Country pilot active；私人 Demo ≠ 已启动国家试点 |
| 8 | Code open-sourced | 缺口 | 本地有脚本与 packs；无已核实公开 GitHub/license | 官网交付与 Restitution 写 Open-source code submission；公开仓未发布 |
| 9 | 接入 PDP+ / country workflows | 缺口 | 现为 Africa GeoPortal 私人 App，未接入 PDP+ | 官网全局表述要求进 PDP+ 与国家工作流；尚未建立 |
| 10 | 县域 lead / P/R / ~60% precision 等 | 来源未核实 | NDMA 代理窗有 P/R；位移全国 P/R=NOT_ELIGIBLE；lead_weeks_claim=false | 2026-11-09 检索：官网与 Esri 博文均无 precision≈60%/recall-first 原文；邮箱原件此前亦未获。不得当硬门槛，需你提供邮件原文才能升格 |

## Top gaps (official only)

- Country pilot active（官网交付）无证据
- Code open-sourced（官网交付）未发布公开仓
- integrated into PDP+ / country workflows 未建立
- DIOS 条目要求 2–4 week displacement warning，位移预警尚未可测验证
- WorldPop age-sex overlay 在非 KEN 仍为国家份额代理
- Experience Builder 多国未建（官网同条含 Experience Builder）

## Excluded as not public-site requirements

- 四国合图 Multi4（用户产品选择，非官网条款）
- DIOS ablation M0/M1/M2（我方实验设计）
- PDFM 分块消融（我方实验设计）
- PIT/防泄漏协议细节（我方方法约束）
- Owner-only 分享策略（用户约束，非官网）
- NDMA/IPC 双验证框架（我方为缺位移真值而设）
- Climate Change DIOS 主题导出（细化数据源，非官网逐字条款）
