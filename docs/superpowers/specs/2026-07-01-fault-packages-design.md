# Fault Packages Design

## Goal

Create a fault-package layer above individual fault knowledge records. A fault package represents one high-priority repair enablement workstream, such as no power, no service, no charging, restart/logo, or leakage/current abnormality.

## Why

Technicians usually enter the workflow by symptom, not by source document. The project also needs a way to prioritize what Manufacturing Center and technical support should help complete next. Fault packages connect:

- L4 report high-frequency symptoms.
- related models.
- related modules and signals.
- required board images and point maps.
- SOP drafts.
- repair cases.
- material gaps and engineering confirmations.

## Scope

Included:

- `knowledge-base/fault-packages.json` with first five priority packages.
- Front-end `故障包` page with search, status filter, readiness, and expandable details.
- Links by id to existing SOPs, fault knowledge, L4 report, and future model assets.

Excluded:

- Interactive SOP execution.
- AI diagnosis.
- Case submission/editing.
- Automatic relation inference.

## First Packages

- 不开机故障包
- 不充电故障包
- 无服务 / 无网络故障包
- 重启 / 卡 Logo 故障包
- 漏电流 / 待机电流异常故障包

## Verification

- JSON parse.
- Front-end script parse.
- P3: open fault package page, search, filter, expand detail, mobile layout.
