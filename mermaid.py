from flask import Flask, request, render_template_string, jsonify, send_from_directory
import pathlib

app = Flask(__name__)

# Remote icon pack URLs
AWS_REMOTE = "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v20.0/dist/aws-icons-mermaid.json"
GCP_REMOTE = "https://raw.githubusercontent.com/lukmanulhakimdevops/gcp-icons-for-mermaid-js/refs/heads/main/dist/gcp-icons-mermaid.json"
OTHER_REMOTE = "https://unpkg.com/@iconify-json/logos@1/icons.json"

# Local storage
PACKS_DIR = pathlib.Path(app.root_path) / "static" / "packs"
PACKS_DIR.mkdir(parents=True, exist_ok=True)

AWS_LOCAL = PACKS_DIR / "aws-icons-mermaid.json"
GCP_LOCAL = PACKS_DIR / "gcp-icons-mermaid.json"
OTHER_LOCAL = PACKS_DIR / "logos-icons-mermaid.json"

HTML = r"""
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mermaid + AWS, GCP & Logos Icons</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1rem; }
    textarea { width: 100%; min-height: 240px; font-family: monospace; font-size: 14px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }
    #diagram { border:1px dashed #aaa; padding:.5rem; min-height:200px; transform-origin: 0 0; transition: border-color 0.3s, background-color 0.3s; }
    pre.error { color: #b91c1c; white-space: pre-wrap; font-weight: bold; }
    .pill { display:inline-block; padding:.15rem .5rem; border:1px solid #ddd; border-radius:999px; margin-right:.25rem; font-size:.85rem; cursor:pointer; }
    .pill[aria-pressed="true"] { background:#111; color:#fff; }
    .muted { color:#555; }
    .small { font-size:.85rem; }
    .category-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }
    .icon-item {
        display: inline-block;
        padding: 2px 6px;
        margin: 2px;
        background-color: #f0f0f0;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        cursor: pointer;
        transition: background-color 0.2s, border-color 0.2s;
        user-select: none; /* Mencegah seleksi teks saat double click */
    }
    .icon-item:hover {
        background-color: #e0e0e0;
    }
    .icon-item.used {
        background-color: #dcfce7; /* light green */
        border: 1px solid #16a34a; /* green */
        color: #15803d;
    }
    #icon-search-filter {
        width: 98%;
        padding: 6px;
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    .button-group { display:flex; flex-wrap:wrap; gap:.5rem; }
    .row { display:flex; flex-wrap:wrap; gap:.5rem; align-items:center;}

    /* 🔥 Efek flow animasi untuk garis/arrow */
    .flow-line {
      stroke-dasharray: 8;
      stroke-dashoffset: 0;
      animation: flow 1s linear infinite;
    }
    @keyframes flow {
      to { stroke-dashoffset: -16; }
    }
  </style>

  <script src="https://unpkg.com/mermaid@11.9.0/dist/mermaid.min.js"></script>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/gif.js/0.2.0/gif.js"></script>

</head>
<body>
  <h1>Mermaid + AWS, GCP & Logos Architecture Icons</h1>

  <div class="row">
    <span id="packs-status">checking…</span>
  </div>

  <div class="grid">
    <div class="card">
      <form id="diagram-form" method="post">
        <textarea id="code" name="code" placeholder="Ketik kode Mermaid di sini...">{{ code|safe }}</textarea>
        <div style="margin-top:.5rem" class="button-group">
          <button type="button" id="btn-insert-sample-aws">Sample AWS</button>
          <button type="button" id="btn-insert-sample-gcp">Sample GCP</button>
          <button type="button" id="btn-insert-sample-hybrid">Sample Hybrid</button>
          <input type="submit" value="Render" />
        </div>
      </form>
      <div style="margin-top:1rem">
        <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
          <strong>Kategori Icon</strong>
          <span class="pill" role="button" id="toggle-categories" aria-pressed="true">Show/Hide</span>
          <span class="muted small">(toggle untuk menampilkan/menyembunyikan daftar ikon)</span>
        </div>
        <details id="icon-panel" open>
          <summary><strong>Available icons</strong></summary>
          <div style="margin: 0.5rem 0;">
            <input type="text" id="icon-search-filter" placeholder="Filter icons by name...">
          </div>
          <div id="icon-list">Loading…</div>
        </details>
      </div>
    </div>

    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <strong>Result</strong>
        <div>
          <button type="button" id="zoom-out">-</button>
          <button type="button" id="zoom-in">+</button>
          <button type="button" id="save-png">Save PNG</button>
          <button type="button" id="save-svg">Save SVG</button>
          <button type="button" id="save-gif">Save GIF</button>
        </div>
        <small>Mermaid v<span id="mm-ver"></span></small>
      </div>
      <div id="diagram"></div>
      <pre id="err" class="error"></pre>
    </div>
  </div>

<script>
  const AWS_LOCAL = '{{ aws_local }}';
  const GCP_LOCAL = '{{ gcp_local }}';
  const OTHER_LOCAL = '{{ other_local }}';
  const AWS_REMOTE = '{{ aws_remote }}';
  const GCP_REMOTE = '{{ gcp_remote }}';
  const OTHER_REMOTE = '{{ other_remote }}';

  let AWS_PACK_URL = AWS_REMOTE;
  let GCP_PACK_URL = GCP_REMOTE;
  let OTHER_PACK_URL = OTHER_REMOTE;
  let currentScale = 1;

  let awsIconData = null;
  let gcpIconData = null;
  let logosIconData = null;
  let serviceCounters = {};

  mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });

  async function checkPacksStatus() {
      try {
          const r = await fetch('/packs-status').then(r => r.json());
          AWS_PACK_URL  = r.aws   ? AWS_LOCAL  : AWS_REMOTE;
          GCP_PACK_URL  = r.gcp   ? GCP_LOCAL  : GCP_REMOTE;
          OTHER_PACK_URL = r.logos ? OTHER_LOCAL : OTHER_REMOTE;

          document.getElementById('packs-status').textContent =
              `AWS: ${r.aws ? 'offline' : 'remote'}, ` +
              `GCP: ${r.gcp ? 'offline' : 'remote'}, ` +
              `Logos: ${r.logos ? 'offline' : 'remote'}`;

          await rebuildIconRegistry();
          await loadIconList();
      } catch (e) {
          document.getElementById('packs-status').textContent = '⚠️ Error checking packs';
      }
  }
  
  function updateUsedIconHighlighting() {
      const code = document.getElementById('code').value;
      const allIcons = document.querySelectorAll('.icon-item');
      
      allIcons.forEach(iconEl => {
          const iconName = iconEl.dataset.iconName;
          const isUsed = new RegExp(`\\((${iconName})\\)`).test(code);
          if (isUsed) {
              iconEl.classList.add('used');
          } else {
              iconEl.classList.remove('used');
          }
      });
  }

  async function loadIconList() {
      const listEl = document.getElementById("icon-list");
      listEl.textContent = 'Loading...';
      try {
          if (!awsIconData) awsIconData = await fetch(AWS_PACK_URL).then(r=>r.json()).catch(()=>null);
          if (!gcpIconData) gcpIconData = await fetch(GCP_PACK_URL).then(r=>r.json()).catch(()=>null);
          if (!logosIconData) logosIconData = await fetch(OTHER_PACK_URL).then(r=>r.json()).catch(()=>null);

          const awsIcons = (awsIconData && awsIconData.icons) ? Object.keys(awsIconData.icons) : [];
          const gcpIcons = (gcpIconData && gcpIconData.icons) ? Object.keys(gcpIconData.icons) : [];
          const logosIcons = (logosIconData && logosIconData.icons) ? Object.keys(logosIconData.icons) : [];

          const createIconSpan = (prefix, name) => `<span class="icon-item" data-icon-name="${prefix}:${name}">${prefix}:${name}</span>`;

          if (!awsIcons.length && !gcpIcons.length && !logosIcons.length){
              listEl.textContent = "⚠️ No icons loaded.";
          } else {
              let html = '';
              if (awsIcons.length) {
                  html += `
                  <div class="icon-category">
                    <div class="category-header">
                      <b>AWS icons (${awsIcons.length})</b>
                      <span class="pill category-toggle" role="button" aria-pressed="true" data-target="aws-icon-details">Show/Hide</span>
                    </div>
                    <div id="aws-icon-details">
                      ${awsIcons.map(name => createIconSpan("aws", name)).join(" ")}
                    </div>
                  </div><br>`;
              }
              if (gcpIcons.length) {
                  html += `
                  <div class="icon-category">
                    <div class="category-header">
                      <b>GCP icons (${gcpIcons.length})</b>
                      <span class="pill category-toggle" role="button" aria-pressed="true" data-target="gcp-icon-details">Show/Hide</span>
                    </div>
                    <div id="gcp-icon-details">
                      ${gcpIcons.map(name => createIconSpan("gcp", name)).join(" ")}
                    </div>
                  </div><br>`;
              }
              if (logosIcons.length) {
                  html += `
                  <div class="icon-category">
                    <div class="category-header">
                      <b>Logos icons (${logosIcons.length})</b>
                      <span class="pill category-toggle" role="button" aria-pressed="true" data-target="logos-icon-details">Show/Hide</span>
                    </div>
                    <div id="logos-icon-details">
                      ${logosIcons.map(name => createIconSpan("logos", name)).join(" ")}
                    </div>
                  </div>`;
              }
              listEl.innerHTML = html;

              document.querySelectorAll('.category-toggle').forEach(button => {
                button.addEventListener('click', e => {
                    const targetId = e.target.getAttribute('data-target');
                    const targetElement = document.getElementById(targetId);
                    const isPressed = e.target.getAttribute('aria-pressed') === 'true';

                    e.target.setAttribute('aria-pressed', !isPressed);
                    targetElement.style.display = isPressed ? 'none' : 'block';
                });
              });
              
              updateUsedIconHighlighting();
          }
      } catch(e) {
          listEl.textContent = "⚠️ Failed to load icon lists.";
      }
  }

  async function rebuildIconRegistry() {
      mermaid.registerIconPacks([
          {
              name: 'aws',
              loader: async () => {
                  if (awsIconData) return awsIconData;
                  awsIconData = await fetch(AWS_PACK_URL).then(r => r.json());
                  return awsIconData;
              }
          },
          {
              name: 'gcp',
              loader: async () => {
                  if (gcpIconData) return gcpIconData;
                  gcpIconData = await fetch(GCP_PACK_URL).then(r => r.json());
                  return gcpIconData;
              }
          },
          {
              name: 'logos',
              loader: async () => {
                  if (logosIconData) return logosIconData;
                  logosIconData = await fetch(OTHER_PACK_URL).then(r => r.json());
                  return logosIconData;
              }
          }
      ]);
  }

  async function renderDiagram() {
      const el = document.getElementById('diagram');
      const err = document.getElementById('err');

      err.textContent = '';
      el.innerHTML = '';
      el.style.borderColor = '#aaa';
      el.style.backgroundColor = 'transparent';

      document.getElementById('diagram').style.transform = `scale(1)`;
      currentScale = 1;
      let code = document.getElementById('code').value;

      try {
          if (code.trim() === '') {
              el.innerHTML = 'Silakan tulis kode Mermaid atau gunakan tombol Sampel.';
              return;
          }

          await rebuildIconRegistry();

          const { svg, bindFunctions } = await mermaid.render('mmd-' + Date.now(), code);
          el.innerHTML = svg;
          if (bindFunctions) bindFunctions(el);

          // 🔥 Tambahkan efek flow ke garis/arrow
          const svgEl = el.querySelector("svg");
          if (svgEl) {
            svgEl.querySelectorAll("path, line, polyline").forEach(edge => {
              edge.classList.add("flow-line");
            });
          }
      } catch (e) {
          el.style.borderColor = '#b91c1c';
          el.style.backgroundColor = '#fff5f5';
          const message = (e && (e.message || e.toString())) || 'Unknown error';
          let errorMessage = 'Mermaid Syntax Error:\n' + message;
          err.textContent = errorMessage;
      }
  }

  function saveSVG() {
      const svgEl = document.querySelector('#diagram svg');
      if (!svgEl) { alert('Please render a diagram first!'); return; }
      svgEl.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      const svgData = svgEl.outerHTML;
      const blob = new Blob([svgData], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = 'diagram.svg';
      document.body.appendChild(link); link.click(); document.body.removeChild(link);
      URL.revokeObjectURL(url);
  }

  function savePNG() {
      const svgEl = document.querySelector('#diagram svg');
      if (!svgEl) { alert('Please render a diagram first!'); return; }
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      const { width, height } = svgEl.getBBox();
      const padding = 20;
      canvas.width = (width + padding * 2) * currentScale;
      canvas.height = (height + padding * 2) * currentScale;
      const svgData = new XMLSerializer().serializeToString(svgEl);
      const img = new Image();
      const svgUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData);
      img.onload = function () {
          context.fillStyle = 'white';
          context.fillRect(0, 0, canvas.width, canvas.height);
          context.drawImage(img, padding * currentScale, padding * currentScale, width * currentScale, height * currentScale);
          const link = document.createElement('a');
          link.href = canvas.toDataURL('image/png');
          link.download = 'diagram.png';
          document.body.appendChild(link); link.click(); document.body.removeChild(link);
      };
      img.src = svgUrl;
  }

  function handleFilter() {
      const filterText = document.getElementById('icon-search-filter').value.toLowerCase().trim();
      document.querySelectorAll('.icon-item').forEach(iconSpan => {
          const iconName = iconSpan.dataset.iconName.toLowerCase();
          if (iconName.includes(filterText)) {
              iconSpan.style.display = 'inline-block';
          } else {
              iconSpan.style.display = 'none';
          }
      });
  }

  document.getElementById('diagram-form').addEventListener('submit', ev => { ev.preventDefault(); renderDiagram(); });
  document.getElementById('zoom-in').addEventListener('click', () => { currentScale += 0.1; document.getElementById('diagram').style.transform = `scale(${currentScale})`; });
  document.getElementById('zoom-out').addEventListener('click', () => { currentScale = Math.max(0.1, currentScale - 0.1); document.getElementById('diagram').style.transform = `scale(${currentScale})`; });
  document.getElementById('save-svg').addEventListener('click', saveSVG);
  document.getElementById('save-png').addEventListener('click', savePNG);

  document.getElementById('toggle-categories').addEventListener('click', (e)=>{
    const panel = document.getElementById('icon-panel');
    const pressed = e.target.getAttribute('aria-pressed') === 'true';
    e.target.setAttribute('aria-pressed', (!pressed).toString());
    panel.open = !pressed ? true : false;
  });

  document.getElementById('icon-search-filter').addEventListener('input', handleFilter);

  document.getElementById('code').addEventListener('input', updateUsedIconHighlighting);

  // Event delegation untuk semua interaksi dengan daftar ikon
  const iconList = document.getElementById('icon-list');
  
  // Klik tunggal: Tambah service
  iconList.addEventListener('click', (e) => {
    if (e.target && e.target.classList.contains('icon-item')) {
        const iconName = e.target.dataset.iconName;
        const [_, namePart] = iconName.split(':');
        const baseId = namePart.replace(/-/g, '');
        
        if (!serviceCounters[baseId]) {
            serviceCounters[baseId] = 0;
        }
        serviceCounters[baseId]++;
        const serviceId = `${baseId}_${serviceCounters[baseId]}`;
        
        const label = namePart.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        const newLine = `  service ${serviceId}(${iconName})[${label}]`;

        const codeEl = document.getElementById('code');
        codeEl.value = (codeEl.value.trim() + '\n' + newLine).trim();
        
        codeEl.dispatchEvent(new Event('input', { bubbles: true }));
        renderDiagram();
    }
  });

  // Klik ganda: Hapus service
  iconList.addEventListener('dblclick', (e) => {
    if (e.target && e.target.classList.contains('icon-item')) {
        const iconName = e.target.dataset.iconName;
        const codeEl = document.getElementById('code');
        let currentCode = codeEl.value;
        
        // Escape karakter spesial untuk regex
        const escapedIconName = iconName.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        
        // Buat regex untuk menghapus semua baris yang mengandung service dengan ikon ini
        const regex = new RegExp(`^\\s*service\\s+\\w+\\(\\s*${escapedIconName}\\s*\\).*$\\n?`, "gm");
        
        const newCode = currentCode.replace(regex, '').trim();
        
        codeEl.value = newCode;
        
        codeEl.dispatchEvent(new Event('input', { bubbles: true }));
        renderDiagram();
    }
  });


  (async function init() {
      try {
          document.getElementById('mm-ver').textContent = mermaid.version;
          await checkPacksStatus();
          setupSamples();
          if (document.getElementById('code').value) { renderDiagram(); }
      } catch (e) { console.error("Initialization failed:", e); }
  })();

  function setupSamples() {
      const awsSample = `architecture-beta
  service user(aws:user)[User]
  group awscloud(aws:aws-cloud)[AWS Cloud]
    group region(aws:region)[Region] in awscloud
      group s3bucket(aws:simple-storage-service)[Amazon S3 bucket] in region
        service video(aws:multimedia)[Video File] in s3bucket
      service handler(aws:lambda-lambda-function)[Lambda Handler] in region
  user:R -[upload]-> L:video
  handler:T <-[trigger]- B:video`;

      const gcpSample = `architecture-beta
  service user(gcp:identityplatform)[User]
  group gcpcloud(gcp:google-cloud)[Google Cloud]
    group bucket(gcp:cloudstorage)[Cloud Storage Bucket] in gcpcloud
      service video(gcp:aihub)[Video File] in bucket
    service trigger(gcp:eventarc)[Eventarc Trigger] in gcpcloud
  user:R -[upload]-> L:video
  trigger:T <-[trigger]- B:video`;

      const hybridSample = `architecture-beta
  service app(logos:python)[Python App]
  group aws(aws:aws-cloud)[AWS Cloud]
    service s3(aws:simple-storage-service)[S3 Bucket] in aws
  group gcp(gcp:google-cloud)[GCP Cloud]
    service bq(gcp:bigquery)[BigQuery] in gcp
  app:R -[upload]-> L:s3
  s3:R -[etl]-> L:bq`;

      document.getElementById('btn-insert-sample-aws').onclick = () => { document.getElementById('code').value = awsSample; updateUsedIconHighlighting(); renderDiagram(); };
      document.getElementById('btn-insert-sample-gcp').onclick = () => { document.getElementById('code').value = gcpSample; updateUsedIconHighlighting(); renderDiagram(); };
      document.getElementById('btn-insert-sample-hybrid').onclick = () => { document.getElementById('code').value = hybridSample; updateUsedIconHighlighting(); renderDiagram(); };
  }

  /**
   * Save GIF implementation
   *
   * Prinsip:
   * - Efek flow asli menggunakan CSS animation stroke-dashoffset dari 0 -> -16 setiap 1s.
   * - Untuk membuat GIF kita harus merender beberapa frame dengan offset berbeda secara manual.
   * - Proses:
   * 1. Ambil SVG, temukan semua edge yang memiliki class 'flow-line'
   * 2. Untuk setiap frame, set inline style strokeDashoffset pada edge-edge tersebut
   * 3. Serialize SVG ke data URL, gambar ke canvas, tambahkan frame ke GIF
   * 4. Setelah semua frame selesai, render GIF dan unduh
   *
   * Catatan:
   * - library gif.js dipakai (sudah di-include di <head>)
   * - kita mengembalikan semua style edge ke keadaan semula setelah selesai
   */
  async function saveGIF() {
    const svgEl = document.querySelector('#diagram svg');
    if (!svgEl) { alert('Please render a diagram first!'); return; }

    // Pastikan kita punya elemen yang diubah (path/line/polyline) yang diberi class flow-line
    const edges = Array.from(svgEl.querySelectorAll('.flow-line'));
    // Dapatkan bbox untuk ukuran canvas
    const bbox = svgEl.getBBox();
    const padding = 20;
    const canvas = document.createElement('canvas');
    canvas.width = (bbox.width + padding * 2) * currentScale;
    canvas.height = (bbox.height + padding * 2) * currentScale;
    const ctx = canvas.getContext('2d');

    // Save original inline styles supaya bisa dipulihkan setelah selesai
    const originalStyles = edges.map(e => e.getAttribute('style'));

    // Animation parameters
    const fps = 25;
    const durationSec = 1.0; // 1 detik loop (sama dengan CSS)
    const frames = Math.max(8, Math.round(fps * durationSec)); // mis. 25 frames
    const maxOffset = 16; // sesuai keyframes (0 -> -16)

    // Siapkan GIF encoder (gif.js)
    const gif = new GIF({
      workers: 2,
      quality: 10,
      workerScript: 'https://cdnjs.cloudflare.com/ajax/libs/gif.js/0.2.0/gif.worker.js',
      width: canvas.width,
      height: canvas.height
    });

    // Helper untuk membuat data URL dari SVG saat ini (dengan inline styles telah diterapkan)
    function svgToDataURL(svgElement) {
      // Pastikan svg memiliki namespace
      svgElement.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      // Serialize
      const svgData = new XMLSerializer().serializeToString(svgElement);
      return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData);
    }

    // Tambahkan setiap frame ke GIF, menunggu gambar ter-load sebelum menambahkan
    for (let i = 0; i < frames; i++) {
      // compute offset: antara 0 dan -maxOffset
      const t = i / frames;
      const offset = - (t * maxOffset);

      // Apply inline style stroke-dashoffset ke setiap edge
      edges.forEach(edge => {
        // strokeDashoffset dapat diberikan sebagai px
        edge.style.strokeDashoffset = offset + 'px';
        // Pastikan stroke-dasharray ter-set (beberapa edge mungkin tidak punya inline)
        if (!edge.style.strokeDasharray) {
          // keep as is; merubah via style hanya jika belum ada
          // Namun kalau stroke-dasharray tidak ada, masih tetap akan terlihat jika class memberi property
          // Tidak memaksa perubahan di sini.
        }
      });

      // Clone SVG untuk serialisasi agar tidak mempengaruhi elemen asli saat image load async
      const svgClone = svgEl.cloneNode(true);

      // 🔥 PERBAIKAN: Sisipkan CSS yang dibutuhkan untuk animasi langsung ke dalam klon SVG.
      // Ini penting karena XMLSerializer tidak menyertakan style dari tag <style> dokumen.
      // Tanpa `stroke-dasharray`, `stroke-dashoffset` yang kita animasikan tidak akan berpengaruh.
      const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style');
      styleEl.textContent = '.flow-line { stroke-dasharray: 8; }';
      const defsEl = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
      defsEl.appendChild(styleEl);
      svgClone.insertBefore(defsEl, svgClone.firstChild);

      // Jika transform (viewBox) atau width/height dibutuhkan, copy atribut penting
      if (!svgClone.getAttribute('width')) {
        svgClone.setAttribute('width', bbox.width + padding * 2);
      }
      if (!svgClone.getAttribute('height')) {
        svgClone.setAttribute('height', bbox.height + padding * 2);
      }
      // Wrap cloned svg in an svg root with correct viewbox if needed
      // (serialize the cloned node)
      const dataUrl = svgToDataURL(svgClone);

      // Convert to Image and draw to canvas (await load)
      /* eslint-disable no-await-in-loop */
      await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
          // Clear canvas and white background
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          // draw the SVG image
          ctx.drawImage(img, padding * currentScale, padding * currentScale, bbox.width * currentScale, bbox.height * currentScale);
          // add frame to gif
          gif.addFrame(ctx, {copy: true, delay: Math.round(1000 / fps)});
          resolve();
        };
        img.onerror = function(err) {
          console.error('Image load error for frame', err);
          reject(err);
        };
        img.src = dataUrl;
      });
    }

    // Restore original inline styles
    edges.forEach((e, idx) => {
      if (originalStyles[idx] === null) {
        e.removeAttribute('style');
      } else {
        e.setAttribute('style', originalStyles[idx]);
      }
    });

    // Render GIF and trigger download when ready
    gif.on('finished', function(blob) {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'diagram.gif';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    });

    gif.render();
  }

  // Tombol Save GIF
  document.getElementById('save-gif').addEventListener('click', () => {
    try {
      saveGIF();
    } catch (err) {
      console.error('saveGIF failed', err);
      alert('Gagal membuat GIF: ' + err);
    }
  });

</script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    code = (request.form.get('code') or '').strip()
    if not code:
        code = """architecture-beta
  service user(aws:user)[User]
  group awscloud(aws:aws-cloud)[AWS Cloud]
    service s3(aws:simple-storage-service)[S3 Bucket] in awscloud
  user:R -> L:s3"""

    return render_template_string(
        HTML, code=code,
        aws_remote=AWS_REMOTE, gcp_remote=GCP_REMOTE, other_remote=OTHER_REMOTE,
        aws_local="/static/packs/aws-icons-mermaid.json",
        gcp_local="/static/packs/gcp-icons-mermaid.json",
        other_local="/static/packs/logos-icons-mermaid.json"
    )

@app.route('/packs-status')
def packs_status():
    return jsonify({
        "aws": AWS_LOCAL.exists(),
        "gcp": GCP_LOCAL.exists(),
        "logos": OTHER_LOCAL.exists()
    })

@app.route('/static/packs/<path:filename>')
def serve_packs(filename):
    return send_from_directory(PACKS_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
