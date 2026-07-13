const EPSILON = 1e-12;

export function validateNormalizedPoint(point) {
  if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)
    || point.x < 0 || point.x > 1 || point.y < 0 || point.y > 1) {
    throw new RangeError('Point must use normalized coordinates between 0 and 1.');
  }
  return { x: point.x, y: point.y };
}

function solveLinearSystem(matrix, values) {
  const rows = matrix.map((row, index) => [...row, values[index]]);
  const size = values.length;

  for (let column = 0; column < size; column += 1) {
    let pivot = column;
    for (let row = column + 1; row < size; row += 1) {
      if (Math.abs(rows[row][column]) > Math.abs(rows[pivot][column])) pivot = row;
    }
    if (Math.abs(rows[pivot][column]) < EPSILON) throw new Error('Registration anchors are degenerate.');
    [rows[column], rows[pivot]] = [rows[pivot], rows[column]];

    const divisor = rows[column][column];
    for (let index = column; index <= size; index += 1) rows[column][index] /= divisor;
    for (let row = 0; row < size; row += 1) {
      if (row === column) continue;
      const factor = rows[row][column];
      for (let index = column; index <= size; index += 1) {
        rows[row][index] -= factor * rows[column][index];
      }
    }
  }
  return rows.map((row) => row[size]);
}

export function solveHomography(source, target) {
  if (!Array.isArray(source) || !Array.isArray(target) || source.length !== 4 || target.length !== 4) {
    throw new Error('A homography requires exactly four source and target anchors.');
  }
  const coefficients = [];
  const values = [];
  source.forEach((point, index) => {
    const { x, y } = validateNormalizedPoint(point);
    const destination = target[index];
    if (!destination || !Number.isFinite(destination.x) || !Number.isFinite(destination.y)) {
      throw new Error('Target anchors must contain finite image coordinates.');
    }
    coefficients.push([x, y, 1, 0, 0, 0, -destination.x * x, -destination.x * y]);
    values.push(destination.x);
    coefficients.push([0, 0, 0, x, y, 1, -destination.y * x, -destination.y * y]);
    values.push(destination.y);
  });
  const solved = solveLinearSystem(coefficients, values);
  return [...solved, 1];
}

export function projectPoint(matrix, point) {
  if (!Array.isArray(matrix) || matrix.length !== 9) throw new Error('Homography must contain nine values.');
  const denominator = matrix[6] * point.x + matrix[7] * point.y + matrix[8];
  if (Math.abs(denominator) < EPSILON) throw new Error('Point cannot be projected by this homography.');
  return {
    x: (matrix[0] * point.x + matrix[1] * point.y + matrix[2]) / denominator,
    y: (matrix[3] * point.x + matrix[4] * point.y + matrix[5]) / denominator,
  };
}

export function invertHomography(matrix) {
  const [a, b, c, d, e, f, g, h, i] = matrix;
  const determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
  if (Math.abs(determinant) < EPSILON) throw new Error('Homography is not invertible.');
  return [
    (e * i - f * h) / determinant,
    (c * h - b * i) / determinant,
    (b * f - c * e) / determinant,
    (f * g - d * i) / determinant,
    (a * i - c * g) / determinant,
    (c * d - a * f) / determinant,
    (d * h - e * g) / determinant,
    (b * g - a * h) / determinant,
    (a * e - b * d) / determinant,
  ];
}

export function projectPolygon(matrix, polygon) {
  return polygon.map((point) => projectPoint(matrix, point));
}
