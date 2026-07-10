import fs from 'node:fs';


const html = fs.readFileSync('mainboard_repair_system_v7.4_updated.html', 'utf8');
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(match => match[1]);

scripts.forEach((source, index) => {
  try {
    new Function(source);
  } catch (error) {
    throw new Error(`Inline script ${index + 1} failed to compile: ${error.message}`);
  }
});

console.log(`Inline scripts compile: ${scripts.length}`);
