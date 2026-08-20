const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function luminance(r, g, b) {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function pixelOffset(width, x, y) {
  return (y * width + x) * 4;
}

export function analyzeImageQuality(image) {
  const { data, width, height } = image;
  if (!data || width <= 0 || height <= 0 || data.length < width * height * 4) {
    throw new TypeError('Valid RGBA image data is required');
  }

  const count = width * height;
  const sourceWidth = image.sourceWidth || width;
  const sourceHeight = image.sourceHeight || height;
  let luminanceSum = 0;
  let luminanceSquareSum = 0;
  let shadows = 0;
  let highlights = 0;
  let gradientSum = 0;
  let gradientCount = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const offset = pixelOffset(width, x, y);
      const value = luminance(data[offset], data[offset + 1], data[offset + 2]);
      luminanceSum += value;
      luminanceSquareSum += value * value;
      if (value <= 8) shadows += 1;
      if (value >= 247) highlights += 1;

      if (x + 1 < width) {
        const right = pixelOffset(width, x + 1, y);
        const rightValue = luminance(data[right], data[right + 1], data[right + 2]);
        gradientSum += Math.abs(value - rightValue);
        gradientCount += 1;
      }
      if (y + 1 < height) {
        const below = pixelOffset(width, x, y + 1);
        const belowValue = luminance(data[below], data[below + 1], data[below + 2]);
        gradientSum += Math.abs(value - belowValue);
        gradientCount += 1;
      }
    }
  }

  const meanLuminance = luminanceSum / count;
  const variance = Math.max(0, luminanceSquareSum / count - meanLuminance * meanLuminance);
  const metrics = {
    width: sourceWidth,
    height: sourceHeight,
    megapixels: (sourceWidth * sourceHeight) / 1_000_000,
    meanLuminance,
    contrast: Math.sqrt(variance),
    shadowClipping: shadows / count,
    highlightClipping: highlights / count,
    sharpness: gradientCount ? gradientSum / gradientCount : 0,
  };

  let score = 100;
  const guidance = [];
  if (Math.min(sourceWidth, sourceHeight) < 600 || metrics.megapixels < 0.5) {
    score -= 30;
    guidance.push({ code: 'low_resolution', message: 'Move closer and keep the complete board in frame.' });
  }
  if (meanLuminance > 225 || metrics.highlightClipping > 0.18) {
    score -= 25;
    guidance.push({ code: 'overexposed', message: 'Reduce direct light or change the angle to remove glare.' });
  }
  if (meanLuminance < 35 || metrics.shadowClipping > 0.22) {
    score -= 25;
    guidance.push({ code: 'underexposed', message: 'Add diffuse light so dark board regions remain visible.' });
  }
  if (metrics.contrast < 22) {
    score -= 20;
    guidance.push({ code: 'low_contrast', message: 'Use a plain contrasting background and more even light.' });
  }
  if (metrics.sharpness < 7) {
    score -= 30;
    guidance.push({ code: 'blurred', message: 'Hold the camera steady and tap the board to focus.' });
  } else if (metrics.sharpness < 14) {
    score -= 12;
    guidance.push({ code: 'soft_focus', message: 'Retake closer with firmer focus for better matching.' });
  }

  score = clamp(Math.round(score), 0, 100);
  const status = score >= 80 ? 'good' : score >= 55 ? 'usable' : 'retake';
  if (!guidance.length) {
    guidance.push({ code: 'ready', message: 'Image quality is suitable for internal reference matching.' });
  }
  return { score, status, metrics, guidance };
}

function normalizeVector(values) {
  const magnitude = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0));
  if (!magnitude) {
    const fallback = values.slice();
    fallback[0] = 1;
    return fallback;
  }
  return values.map((value) => value / magnitude);
}

export function extractFeatureVector(image) {
  const { data, width, height } = image;
  if (!data || width <= 0 || height <= 0 || data.length < width * height * 4) {
    throw new TypeError('Valid RGBA image data is required');
  }

  const structureSize = 8;
  const structure = new Array(structureSize * structureSize).fill(0);
  const structureCounts = new Array(structure.length).fill(0);
  const histogramBins = 8;
  const histogram = new Array(histogramBins * 3).fill(0);
  const edgeGrid = 4;
  const edges = new Array(edgeGrid * edgeGrid * 2).fill(0);
  const edgeCounts = new Array(edgeGrid * edgeGrid).fill(0);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const offset = pixelOffset(width, x, y);
      const r = data[offset];
      const g = data[offset + 1];
      const b = data[offset + 2];
      const value = luminance(r, g, b) / 255;

      const sx = Math.min(structureSize - 1, Math.floor((x / width) * structureSize));
      const sy = Math.min(structureSize - 1, Math.floor((y / height) * structureSize));
      const structureIndex = sy * structureSize + sx;
      structure[structureIndex] += value;
      structureCounts[structureIndex] += 1;

      histogram[Math.min(histogramBins - 1, Math.floor((r / 256) * histogramBins))] += 1;
      histogram[histogramBins + Math.min(histogramBins - 1, Math.floor((g / 256) * histogramBins))] += 1;
      histogram[histogramBins * 2 + Math.min(histogramBins - 1, Math.floor((b / 256) * histogramBins))] += 1;

      const ex = Math.min(edgeGrid - 1, Math.floor((x / width) * edgeGrid));
      const ey = Math.min(edgeGrid - 1, Math.floor((y / height) * edgeGrid));
      const edgeIndex = ey * edgeGrid + ex;
      if (x + 1 < width) {
        const right = pixelOffset(width, x + 1, y);
        edges[edgeIndex * 2] += Math.abs(value - luminance(data[right], data[right + 1], data[right + 2]) / 255);
      }
      if (y + 1 < height) {
        const below = pixelOffset(width, x, y + 1);
        edges[edgeIndex * 2 + 1] += Math.abs(value - luminance(data[below], data[below + 1], data[below + 2]) / 255);
      }
      edgeCounts[edgeIndex] += 1;
    }
  }

  for (let i = 0; i < structure.length; i += 1) {
    structure[i] /= structureCounts[i] || 1;
  }
  for (let i = 0; i < histogram.length; i += 1) {
    histogram[i] /= width * height;
  }
  for (let i = 0; i < edgeCounts.length; i += 1) {
    edges[i * 2] /= edgeCounts[i] || 1;
    edges[i * 2 + 1] /= edgeCounts[i] || 1;
  }

  return normalizeVector([...structure, ...histogram, ...edges]);
}

export function cosineSimilarity(left, right) {
  if (left.length !== right.length || !left.length) return 0;
  let dot = 0;
  let leftMagnitude = 0;
  let rightMagnitude = 0;
  for (let i = 0; i < left.length; i += 1) {
    dot += left[i] * right[i];
    leftMagnitude += left[i] * left[i];
    rightMagnitude += right[i] * right[i];
  }
  const denominator = Math.sqrt(leftMagnitude * rightMagnitude);
  return denominator ? clamp(dot / denominator, -1, 1) : 0;
}

export function rankReferenceCandidates(queryVector, references, limit = 3) {
  return references
    .map(({ vector, ...metadata }) => ({
      ...metadata,
      similarity: cosineSimilarity(queryVector, vector),
    }))
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, Math.max(1, limit));
}

export function rankModelCandidates(queryVector, references, limit = 3) {
  const rankedReferences = rankReferenceCandidates(queryVector, references, references.length || 1);
  const seenModels = new Set();
  const models = [];
  for (const candidate of rankedReferences) {
    if (seenModels.has(candidate.model)) continue;
    seenModels.add(candidate.model);
    models.push(candidate);
    if (models.length >= Math.max(1, limit)) break;
  }
  return models;
}
