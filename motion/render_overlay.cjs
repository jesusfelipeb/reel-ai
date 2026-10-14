// Renderiza motion/overlay.html cuadro por cuadro a PNG con fondo transparente.
// Uso: node motion/render_overlay.cjs <timeline.json> <out_dir> [fps] [workers] [solo_estos_segundos,...]
const path = require('path');
const { pathToFileURL } = require('url');
const fs = require('fs');
const { chromium } = require('playwright');

async function main() {
  const [timelinePath, outDir, fpsArg, workersArg, onlyArg] = process.argv.slice(2);
  const fps = Number(fpsArg || 30);
  const workers = Number(workersArg || 4);
  const data = JSON.parse(fs.readFileSync(timelinePath, 'utf-8'));
  fs.mkdirSync(outDir, { recursive: true });

  const total = data.scene.end - data.scene.start + data.scene.end_card_seconds;
  const frames = onlyArg
    ? onlyArg.split(',').map(s => Math.round(Number(s) * fps))
    : Array.from({ length: Math.ceil(total * fps) }, (_, i) => i);

  const browser = await chromium.launch({ args: ['--disable-dev-shm-usage'] });
  const url = pathToFileURL(path.resolve(__dirname, 'overlay.html')).href;

  const chunks = Array.from({ length: workers }, (_, w) => frames.filter((_, i) => i % workers === w));
  let done = 0;
  await Promise.all(chunks.map(async chunk => {
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    page.on('pageerror', err => { console.error('pageerror:', err.message); process.exitCode = 1; });
    await page.goto(url);
    await page.evaluate(d => window.setScene(d), data);
    for (const f of chunk) {
      await page.evaluate(t => window.renderAt(t), f / fps);
      const name = onlyArg ? `still-${(f / fps).toFixed(2)}.png` : `f${String(f).padStart(5, '0')}.png`;
      await page.screenshot({ path: path.join(outDir, name), omitBackground: true });
      done += 1;
      if (done % 150 === 0) console.log(`  overlay ${done}/${frames.length}`);
    }
    await page.close();
  }));
  await browser.close();
}

main().catch(err => { console.error(err); process.exit(1); });
