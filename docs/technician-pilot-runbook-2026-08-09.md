# Technician Pilot Runbook · 2026-08-09

## Purpose

This is the operating guide for the first controlled technician trial. It tests whether a technician can select a known model, enter the correct source-supported task, follow the existing repair flow, recover after a refresh, and return a privacy-reduced record. It does not test automatic diagnosis, visual-defect recognition, or photo upload.

## Controlled Entry

- Production URL: `https://cccsat.top/mb-repair-beta/assets/technician-pilot/`
- Access: use the individually issued restricted pilot account. Do not share credentials.
- Supported browsers: current Chrome or Edge on desktop or mobile.
- The technician must already know the phone model and motherboard version. The system does not identify or guess them.

## First Trial Task

Use a board whose symptom is already known. KM4 `不开机 / 小电流` is the preferred first executable path because its reviewed measurement flow is present. If the fault is unknown, choose `不确定，先做初步排查` in the same selector.

1. Select the confirmed phone model and check the displayed motherboard version.
2. Select the known symptom, or select the initial inspection option when the symptom is unknown.
3. Open the motherboard repair workbench.
4. Follow only the displayed detection steps. Record the real measurement or choice requested by the current step.
5. Use the point map, 2.5D board, component isolation and source panels to locate the target. Do not infer a repair action when the page states that the reviewed source boundary has been reached.
6. Refresh once during a non-terminal KM4 task and confirm that the session shows `已恢复` and returns to the same step.
7. Complete the executable flow, record the action and post-action check when requested, then choose `结束本次排查`.
8. Select one location result and one source-usability result in the feedback area, then save the feedback.
9. Export both JSON files before leaving the browser:
   - `technician-repair-session-YYYY-MM-DD.json`
   - `technician-pilot-feedback-YYYY-MM-DD.json`

## Return Package

Return the two exported JSON files to Milo through the existing controlled work channel. Add only these operational facts in the accompanying message:

- country and service site;
- technician role or level, without personal phone/customer data;
- phone model and motherboard version used;
- whether the task was completed;
- one blocker category when incomplete: access, model selection, target location, instruction clarity, measurement entry, session recovery, export, or source boundary.

Do not return customer name, phone number, IMEI, device photos, motherboard photos, credentials, or an unreviewed technical conclusion. Real visual photos continue to enter only through Milo and the separate controlled visual-data path.

## Trial Acceptance

The first trial loop is considered operationally complete when one technician can:

- authenticate and open the unified entry;
- reach the intended known-symptom or initial-inspection path;
- locate the requested target or truthfully report that it was not found;
- follow one reviewed executable flow without inventing a step;
- recover the same unfinished session after refresh;
- finish or stop at a declared source boundary;
- export both valid JSON records and return them through the controlled channel.

Field feedback remains usability evidence. It does not update the knowledge base, repair logic, visual-QC labels or training data automatically. Codex reviews returned records, removes invalid or cross-task data, groups blockers, and proposes source or interface changes for Milo's approval.

## 海外维修员简版说明

1. 使用分配给你的内测账号打开统一入口。
2. 选择你已经确认的手机机型和主板版本；系统不会自动识别机型。
3. 已知故障时直接选择故障现象；不确定时选择“先做初步排查”。
4. 只执行页面显示的检测步骤，并填写真实检测结果。
5. 页面提示资料到达边界时停止，不自行推断维修结论。
6. 中途刷新一次，确认维修记录能够恢复。
7. 完成或停止后，填写“是否找到位置”和“资料是否足够继续”。
8. 导出维修记录和试用反馈两个 JSON 文件，交回项目负责人。
9. 不上传客户信息、IMEI、照片、账号密码或未经确认的技术结论。

## Short English Instructions

1. Open the controlled pilot entry with your assigned account.
2. Select the phone model and motherboard version that you have already confirmed; the system does not identify the board.
3. Select the known symptom, or choose the initial inspection option when the symptom is unknown.
4. Follow only the displayed checks and enter the actual result requested by each step.
5. Stop when the page says the reviewed source boundary has been reached. Do not invent a repair conclusion.
6. Refresh once during the task and confirm that the same repair session is restored.
7. Finish or stop the task, record whether the target was found and whether the source was sufficient, then export both JSON records.
8. Return the files through the controlled work channel. Do not include customer data, IMEI, photos, credentials or unreviewed conclusions.
