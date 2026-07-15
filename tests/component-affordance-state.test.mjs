import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildCornerSegments,
  buildHitArea,
  buildLabelLeaderSegment,
  buildScreenLabelPositions,
  buildScreenAwareHitScale,
  placeHoverTooltip,
  resolveAffordancePresentation,
} from '../assets/cross-source-registration/component-affordance-state.js';

test('interactive frame uses eight short segments outside the package footprint', () => {
  const segments = buildCornerSegments({ x: 0.1, y: 0.06 });
  assert.equal(segments.length, 8);
  assert.equal(segments.every((segment) => segment.length === 2), true);
  assert.equal(segments.every((segment) => segment.every((point) => Math.abs(point.x) > 0.05 || Math.abs(point.y) > 0.03)), true);
});

test('screen-space label layout stays inside a narrow canvas without collisions', () => {
  const items = [
    ['U2001', 170, 250], ['U4000', 80, 280], ['X2100', 185, 220],
    ['U0600', 220, 255], ['J6101', 200, 330], ['VBAT1', 302, 315], ['VBUS1', 288, 300],
  ].map(([id, x, y]) => ({ id, anchor: { x, y } }));
  const positions = buildScreenLabelPositions(items, {
    viewport: { width: 320, height: 440 },
  });
  const rectangles = positions.map((position) => ({
    left: position.x - 38,
    right: position.x + 38,
    top: position.y - 11,
    bottom: position.y + 11,
  }));

  rectangles.forEach((rectangle) => {
    assert.ok(rectangle.left >= 8 && rectangle.right <= 312);
    assert.ok(rectangle.top >= 8 && rectangle.bottom <= 432);
  });
  rectangles.forEach((rectangle, index) => {
    rectangles.slice(index + 1).forEach((other) => {
      assert.ok(rectangle.right <= other.left || other.right <= rectangle.left
        || rectangle.bottom <= other.top || other.bottom <= rectangle.top);
    });
  });
  positions.forEach((position, index) => {
    assert.ok(Math.hypot(position.x - items[index].anchor.x, position.y - items[index].anchor.y) < 150);
  });
});

test('screen-space label layout defers when the canvas cannot fit one tag', () => {
  assert.deepEqual(buildScreenLabelPositions([
    { id: 'U2001', anchor: { x: 0, y: 0 } },
  ], {
    viewport: { width: 1, height: 1 },
  }), []);
});

test('screen-space label layout preserves a previously valid compass slot', () => {
  const [position] = buildScreenLabelPositions([
    { id: 'U2001', anchor: { x: 160, y: 220 } },
  ], {
    viewport: { width: 320, height: 440 },
    preferredSlots: new Map([['U2001', 1]]),
  });

  assert.equal(position.slot, 1);
  assert.equal(position.x, 160);
  assert.equal(position.y, 246);
});

test('screen-space labels stay outside their own projected package footprint', () => {
  const [position] = buildScreenLabelPositions([
    {
      id: 'U4000',
      anchor: { x: 160, y: 220 },
      exclusion: { left: 118, right: 202, top: 178, bottom: 262 },
    },
  ], {
    viewport: { width: 320, height: 440 },
  });
  const label = {
    left: position.x - 38,
    right: position.x + 38,
    top: position.y - 11,
    bottom: position.y + 11,
  };

  assert.equal(
    label.right <= 114 || label.left >= 206 || label.bottom <= 174 || label.top >= 266,
    true,
  );
});

test('screen-space labels change side when clamping would cover the package', () => {
  const [position] = buildScreenLabelPositions([
    {
      id: 'U2001',
      anchor: { x: 160, y: 38 },
      exclusion: { left: 112, right: 208, top: 6, bottom: 70 },
    },
  ], {
    viewport: { width: 320, height: 200 },
  });

  assert.ok(position.y >= 85);
});

test('screen-space labels avoid neighboring interactive packages', () => {
  const obstacle = { left: 100, right: 220, top: 40, bottom: 92 };
  const [position] = buildScreenLabelPositions([
    {
      id: 'U4000',
      anchor: { x: 160, y: 140 },
      exclusion: { left: 118, right: 202, top: 108, bottom: 172 },
    },
  ], {
    viewport: { width: 320, height: 300 },
    obstacles: [obstacle],
  });
  const label = {
    left: position.x - 38,
    right: position.x + 38,
    top: position.y - 11,
    bottom: position.y + 11,
  };

  assert.equal(
    label.left < obstacle.right && label.right > obstacle.left
      && label.top < obstacle.bottom && label.bottom > obstacle.top,
    false,
  );
});

test('only displaced labels receive a leader ending at the label edge', () => {
  assert.equal(buildLabelLeaderSegment({
    anchor: { x: 100, y: 100 },
    label: { x: 120, y: 100 },
  }), null);

  assert.deepEqual(buildLabelLeaderSegment({
    anchor: { x: 20, y: 100 },
    label: { x: 120, y: 100 },
  }), {
    start: { x: 28, y: 100 },
    end: { x: 82, y: 100 },
  });
});

test('package-aware leaders start outside the component and skip adjacent labels', () => {
  const exclusion = { left: 118, right: 202, top: 178, bottom: 262 };
  assert.equal(buildLabelLeaderSegment({
    anchor: { x: 160, y: 220 },
    label: { x: 160, y: 163 },
    exclusion,
  }), null);

  assert.deepEqual(buildLabelLeaderSegment({
    anchor: { x: 160, y: 220 },
    label: { x: 160, y: 120 },
    exclusion,
  }), {
    start: { x: 160, y: 174 },
    end: { x: 160, y: 131 },
  });
});

test('reviewed components receive bounded hit areas without inheriting complex mesh bounds', () => {
  assert.deepEqual(buildHitArea({ x: 0.1, y: 0.06 }), { x: 0.112, y: 0.072 });
  assert.deepEqual(buildHitArea({ x: 0.008, y: 0.006 }), { x: 0.047, y: 0.047 });
});

test('small hit areas keep a screen-space minimum without enlarging visible markers', () => {
  const mobile = buildScreenAwareHitScale(
    { x: 0.047, y: 0.047 },
    { x: 2.16 / 320, y: 1.38 / 500 },
    36,
  );
  assert.equal(Math.round(0.047 * mobile.x / (2.16 / 320)), 36);
  assert.equal(Math.round(0.047 * mobile.y / (1.38 / 500)), 36);
  assert.deepEqual(
    buildScreenAwareHitScale({ x: 0.2, y: 0.2 }, { x: 0.001, y: 0.001 }, 24),
    { x: 1, y: 1 },
  );
});

test('affordance states reserve coral for faults instead of ordinary selection', () => {
  const idle = resolveAffordancePresentation({});
  const hovered = resolveAffordancePresentation({ hovered: true });
  const selected = resolveAffordancePresentation({ selected: true });

  assert.equal(idle.opacity < hovered.opacity, true);
  assert.equal(selected.opacity, 1);
  assert.notEqual(selected.color, 0xef5b3f);
  assert.equal(selected.labelOpacity, 1);
  assert.equal('emissiveIntensity' in idle, false);
  assert.equal('emissiveIntensity' in hovered, false);
  assert.equal('emissiveIntensity' in selected, false);
});

test('reviewed component tags keep a readable fixed screen size', () => {
  const idle = resolveAffordancePresentation({});
  const hovered = resolveAffordancePresentation({ hovered: true });
  const selected = resolveAffordancePresentation({ selected: true });

  assert.deepEqual(idle.labelPixels, { width: 68, height: 20 });
  assert.deepEqual(selected.labelPixels, { width: 76, height: 22 });
  assert.equal(idle.labelVariant, 'idle');
  assert.equal(hovered.labelVariant, 'hovered');
  assert.equal(selected.labelVariant, 'selected');
});

test('hover tooltip flips away from canvas edges and stays fully visible', () => {
  assert.deepEqual(placeHoverTooltip({
    pointer: { x: 310, y: 12 },
    viewport: { width: 320, height: 240 },
    tooltip: { width: 156, height: 48 },
  }), { x: 142, y: 24, horizontal: 'left', vertical: 'below' });

  assert.deepEqual(placeHoverTooltip({
    pointer: { x: 80, y: 120 },
    viewport: { width: 320, height: 240 },
    tooltip: { width: 156, height: 48 },
  }), { x: 92, y: 60, horizontal: 'right', vertical: 'above' });
});

test('selection takes precedence over hover presentation', () => {
  assert.deepEqual(
    resolveAffordancePresentation({ selected: true, hovered: true }),
    resolveAffordancePresentation({ selected: true }),
  );
});
