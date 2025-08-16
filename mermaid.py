#!/usr/bin/env python3
from flask import Flask, request, render_template_string, jsonify, send_from_directory
import pathlib, requests

app = Flask(__name__)

# Remote icon pack URLs
AWS_REMOTE = "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v20.0/dist/aws-icons-mermaid.json"
GCP_REMOTE = "https://cdn.jsdelivr.net/gh/lukmanulhakimdevops/gcp-icons-for-mermaid-js@refs/heads/main/dist/gcp-icons-mermaid.json"

# Local storage
PACKS_DIR = pathlib.Path(app.root_path) / "static" / "packs"
PACKS_DIR.mkdir(parents=True, exist_ok=True)

AWS_LOCAL = PACKS_DIR / "aws-icons-mermaid.json"
GCP_LOCAL = PACKS_DIR / "gcp-icons-mermaid.json"

HTML = r"""
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mermaid + AWS & GCP Architecture Icons</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1rem; }
    textarea { width: 100%; min-height: 240px; font-family: monospace; font-size: 14px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }
    #diagram { border:1px dashed #aaa; padding:.5rem; min-height:200px; transform-origin: 0 0; }
    pre.error { color: #b91c1c; white-space: pre-wrap; }
  </style>
  <script src="https://unpkg.com/mermaid@11.1.0/dist/mermaid.min.js"></script>
</head>
<body>
  <h1>Mermaid + AWS & GCP Architecture Icons</h1>

  <div>
    <button id="btn-download-packs">Download icon packs (offline)</button>
    <button id="btn-reload-icons">Reload icons</button>
    <span id="packs-status">checking…</span>
  </div>

  <div class="grid">
    <div class="card">
      <form id="diagram-form" method="post">
        <textarea id="code" name="code" placeholder="Type Mermaid code here...">{{ code|safe }}</textarea>
        <div style="margin-top:.5rem">
          <button type="button" id="btn-insert-sample-aws">Sample AWS</button>
          <button type="button" id="btn-insert-sample-gcp">Sample GCP</button>
          <button type="button" id="btn-insert-sample-hybrid">Sample Hybrid</button>
          <input type="submit" value="Render" />
        </div>
      </form>
      <div style="margin-top:1rem">
        <details open>
          <summary><strong>Available icons</strong></summary>
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
        </div>
        <small>Mermaid v<span id="mm-ver"></span></small>
      </div>
      <div id="diagram"></div>
      <pre id="err" class="error"></pre>
    </div>
  </div>

<script>
  const AWS_REMOTE = '{{ aws_remote }}';
  const GCP_REMOTE = '{{ gcp_remote }}';
  const AWS_LOCAL = '{{ aws_local }}';
  const GCP_LOCAL = '{{ gcp_local }}';

  let AWS_PACK_URL = AWS_REMOTE;
  let GCP_PACK_URL = GCP_REMOTE;
  let currentScale = 1;
  
  // ## OPTIMASI: Variabel untuk menyimpan data ikon (cache) ##
  let awsIconData = null;
  let gcpIconData = null;

  mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });

  async function checkPacksStatus() {
      try {
          const r = await fetch('/packs-status').then(r => r.json());
          AWS_PACK_URL = r.aws ? AWS_LOCAL : AWS_REMOTE;
          GCP_PACK_URL = r.gcp ? GCP_LOCAL : GCP_REMOTE;
          document.getElementById('packs-status').textContent =
              `AWS: ${r.aws ? 'offline/local' : 'remote'}, GCP: ${r.gcp ? 'offline/local' : 'remote'}`;
          // Muat daftar ikon setelah status dicek
          await loadIconList(); 
      } catch (e) {
          document.getElementById('packs-status').textContent = '⚠️ Error checking packs';
      }
  }

  // ## OPTIMASI: Fungsi ini sekarang mengisi cache ##
  async function loadIconList() {
      const listEl = document.getElementById("icon-list");
      listEl.textContent = 'Loading...';
      try {
          // Ambil data dan simpan di cache jika belum ada
          if (!awsIconData) {
              awsIconData = await fetch(AWS_PACK_URL).then(r=>r.json()).catch(()=>null);
          }
          if (!gcpIconData) {
              gcpIconData = await fetch(GCP_PACK_URL).then(r=>r.json()).catch(()=>null);
          }

          const awsIcons = (awsIconData && awsIconData.icons) ? Object.keys(awsIconData.icons) : [];
          const gcpIcons = (gcpIconData && gcpIconData.icons) ? Object.keys(gcpIconData.icons) : [];

          if (!awsIcons.length && !gcpIcons.length){
              listEl.textContent = "⚠️ No icons loaded.";
          } else {
              listEl.innerHTML =
                  `<b>AWS icons (${awsIcons.length})</b><br><small>${awsIcons.map(x => "aws:"+x).join(", ")}</small><br><br>` +
                  `<b>GCP icons (${gcpIcons.length})</b><br><small>${gcpIcons.map(x => "gcp:"+x).join(", ")}</small>`;
          }
      } catch(e) {
          listEl.textContent = "⚠️ Failed to load icon lists.";
      }
  }

  async function downloadPacks() {
      const btn = document.getElementById('btn-download-packs');
      btn.disabled = true; btn.textContent = 'Downloading…';
      try {
          const r = await fetch('/download-packs', { method: 'POST' }).then(r => r.json());
          if (r.ok) {
              awsIconData = null; gcpIconData = null; // Reset cache
              await checkPacksStatus(); 
              alert('✅ Packs ready.');
          } else { 
              alert('❌ Error: ' + (r.error || 'Unknown')); 
          }
      } catch(e){ alert('❌ ' + e); }
      btn.disabled = false; btn.textContent = 'Download icon packs (offline)';
  }
  document.getElementById('btn-download-packs').addEventListener('click', downloadPacks);
  
  document.getElementById('btn-reload-icons').addEventListener('click', async () => {
      awsIconData = null; gcpIconData = null; // Reset cache
      await checkPacksStatus();
      await rebuildIconRegistry();
  });
  
  // ## OPTIMASI: Fungsi ini sekarang menggunakan cache terlebih dahulu ##
  async function rebuildIconRegistry() {
      mermaid.registerIconPacks([
          {
              name: 'aws',
              loader: async () => {
                  if (awsIconData) return awsIconData; // Gunakan cache jika ada
                  awsIconData = await fetch(AWS_PACK_URL).then(r => r.json());
                  return awsIconData;
              }
          },
          {
              name: 'gcp',
              loader: async () => {
                  if (gcpIconData) return gcpIconData; // Gunakan cache jika ada
                  gcpIconData = await fetch(GCP_PACK_URL).then(r => r.json());
                  return gcpIconData;
              }
          }
      ]);
  }

  async function renderDiagram() {
      const el = document.getElementById('diagram');
      const err = document.getElementById('err');
      err.textContent = ''; el.innerHTML = ''; currentScale = 1;
      let code = document.getElementById('code').value;
      try {
          await rebuildIconRegistry(); // Pastikan registry terbaru sebelum render
          const { svg, bindFunctions } = await mermaid.render('mmd-' + Date.now(), code);
          el.innerHTML = svg; if (bindFunctions) bindFunctions(el);
      } catch (e) {
          err.textContent = (e.message || e) + '\\n\\nCheck syntax & icon names.';
      }
  }

  document.getElementById('diagram-form').addEventListener('submit', ev => { ev.preventDefault(); renderDiagram(); });
  document.getElementById('zoom-in').addEventListener('click', () => { currentScale += 0.1; document.getElementById('diagram').style.transform = `scale(${currentScale})`; });
  document.getElementById('zoom-out').addEventListener('click', () => { currentScale = Math.max(0.1, currentScale - 0.1); document.getElementById('diagram').style.transform = `scale(${currentScale})`; });

  function setupSamples() { /* ... (kode yang sudah ada, tidak perlu diubah) ... */ }
  
  (async function init() {
      try {
          document.getElementById('mm-ver').textContent = mermaid.version;
          await checkPacksStatus(); // Ini akan memuat list dan mengisi cache
          await rebuildIconRegistry(); // Ini akan menggunakan cache
          setupSamples();
          if (document.getElementById('code').value) { await renderDiagram(); }
      } catch (e) { console.error("Initialization failed:", e); }
  })();
  
  // Implementasi sisa fungsi-fungsi
  function setupSamples() {
      const awsSample = `architecture-beta
  service user(aws:user)[User]
  group awscloud(aws:aws-cloud)[AWS Cloud]
    group region(aws:region)[Region] in awscloud
      group s3bucket(aws:simple-storage-service)[Amazon S3 bucket] in region
        service video(aws:multimedia)[video] in s3bucket
      service handler(aws:lambda-lambda-function)[ObjectCreated event handler] in region
  user:R -[upload]-> L:video
  handler:T <-[trigger]- B:video`;
      const gcpSample = `architecture-beta
  service user(aws:user)[User]
  group gcpcloud(gcp:google-cloud-marketplace)[GCP Cloud]
    group bucket(gcp:cloud-storage)[Cloud Storage Bucket] in gcpcloud
      service video(aws:multimedia)[video] in bucket
    service trigger(gcp:eventarc)[Eventarc Trigger] in gcpcloud
  user:R -[upload]-> L:video
  trigger:T <-[trigger]- B:video`;
      const hybridSample = `architecture-beta
  service user(aws:user)[User]
  group aws(aws:aws-cloud)[AWS Cloud]
    service s3(aws:simple-storage-service)[S3 Bucket] in aws
  group gcp(gcp:google-cloud-marketplace)[GCP Cloud]
    service bq(gcp:bigquery)[BigQuery] in gcp
  user:R -[upload]-> L:s3
  s3:R -[etl]-> L:bq`;
      document.getElementById('btn-insert-sample-aws').onclick = () => { document.getElementById('code').value = awsSample; };
      document.getElementById('btn-insert-sample-gcp').onclick = () => { document.getElementById('code').value = gcpSample; };
      document.getElementById('btn-insert-sample-hybrid').onclick = () => { document.getElementById('code').value = hybridSample; };
  }
</script>
</body>
</html>
"""

def _download(url: str, dest: pathlib.Path):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)

@app.route('/', methods=['GET', 'POST'])
def index():
    code = (request.form.get('code') or '').strip()
    return render_template_string(
        HTML, code=code,
        aws_remote=AWS_REMOTE, gcp_remote=GCP_REMOTE,
        aws_local="/static/packs/aws-icons-mermaid.json",
        gcp_local="/static/packs/gcp-icons-mermaid.json"
    )

@app.route('/packs-status')
def packs_status():
    return jsonify({"aws": AWS_LOCAL.exists(), "gcp": GCP_LOCAL.exists()})

@app.route('/download-packs', methods=['POST'])
def download_packs():
    try:
        _download(AWS_REMOTE, AWS_LOCAL)
        _download(GCP_REMOTE, GCP_LOCAL)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/static/packs/<path:filename>')
def serve_packs(filename):
    return send_from_directory(PACKS_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
