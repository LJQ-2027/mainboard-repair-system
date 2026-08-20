# KM4/F151 Repair-Flow Source Audit

## Scope

Source reviewed visually and through text extraction:

- `TECNO-L6735-KM4-F151手机维修通用操作指导书V1.0_20250331.pdf`
- Pages 9, 10, 11, 14, and 15

This audit distinguishes source-proven graph edges from branches that remain incomplete or ambiguous. The runtime must not infer missing directions from general repair experience.

## Page 9: No-Current No-Power

The chart proves this order:

1. Connect a dummy battery and repair supply, press power, and observe current.
2. If there is no current, check whether `POWER_KEY` has supply.
3. A positive `POWER_KEY` result routes to system/memory/CPU/crystal inspection.
4. A negative result routes to the `VSYS` voltage question.
5. Positive `VSYS` routes to the power-management IC; negative routes to the charging IC.

Deferred: the current dataset does not yet contain a reviewed `POWER_KEY` or `VSYS` measurement profile and component identity for every terminal.

## Page 10: Small-Current No-Power

The chart proves this order for current below 100 mA:

1. Check whether `VDDCORE` and `VDDEMMCCORE` are normal.
2. An abnormal result routes to rework or replacement of the power-management IC.
3. A normal result routes to the X2100 26 MHz question.
4. An abnormal X2100 result routes to crystal rework or replacement.
5. A normal X2100 result routes to CPU/DDR rework or replacement.

Implemented: step 1 is preserved as one composite decision with two required measurements. The runtime records both `VDDCORE` (1.15 V nominal) and `VDDEMMCCORE` (3.3 V nominal) before enabling the normal/abnormal choice. Because the source supplies no tolerance, neither value is auto-classified.

The reviewed runtime path is:

1. Focus U4000 and require both rail measurements.
2. A normal technician judgment advances to X2100 and requires a 26 MHz measurement.
3. An abnormal rail judgment focuses U2001 and presents the source action to rework or replace the power-management IC.
4. At X2100, an abnormal judgment presents crystal rework or replacement; a normal judgment presents CPU/DDR rework or replacement.

Model focus follows the current step or terminal target. Back and reset restore the corresponding component target as well as the graph state.

## Page 11: Large-Current No-Power

The chart proves a `VBAT` short-to-ground question followed by short-path inspection and thermal-imaging or rosin-based localization. The same page supplies reference values:

- `VBAT`: 3.4 V to 4.35 V
- `VDDCORE`: 1.15 V
- `VDDEMMCCORE`: 3.3 V, 600 mA

Dataset correction: `VDDEMMCCORE` is now represented as a 3.3 V nominal reference without tolerance instead of record-only.

Deferred: voltage range compliance is not equivalent to the chart's short-to-ground condition. A resistance/continuity observation and explicit short result are required before this flow can be modeled faithfully.

## Page 14: Not-Charging Structural Checks

The first three decisions are visually unambiguous and are implemented:

1. Is the charger working normally?
   - No: replace the charger.
   - Yes: continue to USB connector inspection.
2. Is the USB connector poorly soldered?
   - Yes: re-solder the USB connector.
   - No: continue to FPC seating inspection.
3. Is the FPC cable correctly seated?
   - No: reseat the FPC cable.
   - Yes: enter the FPC-defect question.

The subsequent `FPC 排线是否不良` Y/N labels conflict with the displayed `更换 FPC` and battery-check directions. The reviewed flow therefore stops at an explicit source-boundary terminal before choosing either edge.

## Page 15: No Clock Output

The chart proves solder-condition and crystal-damage checks followed by solder repair, crystal replacement, or work on the corresponding clock IC.

Deferred: the first question concerns solder condition, not measured frequency. A visual/solder observation must be represented separately from the existing X2100 frequency field before the graph can be implemented without conflation.

## Runtime Rule

- Only explicit source edges become `next` or `action` outcomes.
- An ambiguous edge becomes a `boundary` outcome with the reviewed note.
- A terminal action repeats source wording; it is not an AI-generated diagnosis.
- Later source review may extend a partial flow, but must update both dataset validation and regression evidence.
