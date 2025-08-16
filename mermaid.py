#!/usr/bin/env python3
from flask import Flask, request, render_template_string, jsonify, send_from_directory
import os, pathlib, requests

app = Flask(__name__)

AWS_REMOTE = "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v20.0/dist/aws-icons-mermaid.json"
GCP_REMOTE = "https://cdn.jsdelivr.net/gh/lukmanulhakimdevops/gcp-icons-for-mermaid-js@refs/heads/main/dist/gcp-icons-mermaid.json"

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
  <title>Mermaid + AWS/GCP Icons (Flask)</title>
  <style>
    html, body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
    .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
    textarea { width: 100%; min-height: 260px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 14px; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 1rem; }
    @media (min-width: 1000px){ .grid { grid-template-columns: 1fr 1fr; } }
    .card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,.06); }
    .row { display:flex; gap:.5rem; align-items:center; flex-wrap:wrap }
    button, input[type="submit"] { border: 1px solid #d1d5db; padding: .5rem .9rem; border-radius: 10px; background: white; cursor: pointer; }
    button:hover, input[type="submit"]:hover { background: #f3f4f6; }
    .muted { color:#6b7280; font-size: .9rem; }
    .badge { display:inline-block; padding:.2rem .5rem; border:1px solid #e5e7eb; border-radius:.5rem; margin:.15rem; font-size:.8rem; cursor:pointer }
    #diagram { overflow:auto; border: 1px dashed #e5e7eb; border-radius: 10px; padding:.5rem; min-height: 200px; transform-origin: 0 0; }
    code { background:#f9fafb; padding:.15rem .35rem; border-radius:.35rem }
    .error { color:#b91c1c; white-space: pre-wrap; }
    .notice { padding:.6rem .8rem; border:1px solid #d1fae5; background:#ecfdf5; color:#065f46; border-radius:.6rem; }
    .warn { padding:.6rem .8rem; border:1px solid #fde68a; background:#fffbeb; color:#92400e; border-radius:.6rem; }
  </style>
  <script src="https://unpkg.com/mermaid@11.9.0/dist/mermaid.min.js"></script>
</head>
<body>
  <div class="container">
    <h1>Mermaid + AWS & GCP Architecture Icons</h1>

    <div id="packs-banner" class="warn" style="display:none; margin:.75rem 0"></div>
    <div class="row" style="margin:.5rem 0">
      <button id="btn-download-packs">Download icon packs (offline)</button>
      <span class="muted">Status: <span id="packs-status">checking…</span></span>
    </div>

    <p class="muted">Icon pack sources: <code id="aws-url"></code> & <code id="gcp-url"></code></p>

    <div class="grid">
      <div class="card">
        <form id="diagram-form" method="post" action="{{ url_for('index') }}">
          <div class="row" style="justify-content:space-between">
            <div><strong>Enter Mermaid code</strong></div>
            <div class="row">
              <button type="button" id="btn-insert-sample-aws">Insert sample (AWS)</button>
              <button type="button" id="btn-insert-sample-gcp">Insert sample (GCP)</button>
              <input type="submit" value="Render" />
            </div>
          </div>
          <textarea id="code" name="code" placeholder="Type Mermaid code here...">{{ code|safe }}</textarea>
          <div class="muted" style="margin-top:.5rem">
            Use <code>architecture-beta</code> and reference icons as <code>aws:icon-name</code> or <code>gcp:icon-name</code>.
          </div>
        </form>
        <div style="margin-top:1rem">
          <details>
            <summary><strong>Available icons</strong></summary>
            <div id="icon-list" class="muted">Loading…</div>
          </details>
        </div>
      </div>

      <div class="card">
        <div class="row" style="justify-content:space-between">
          <strong>Result</strong>
          <div class="row">
            <button type="button" id="zoom-out">-</button>
            <button type="button" id="zoom-in">+</button>
            <button type="button" id="save-png">Save PNG</button>
            <button type="button" id="save-svg">Save SVG</button>
          </div>
          <div class="muted">Mermaid v<span id="mm-ver"></span></div>
        </div>
        <div id="diagram"></div>
        <pre id="err" class="error"></pre>
      </div>
    </div>
  </div>

<script>
  // Remote URLs (fallback if offline packs not present)
  const AWS_REMOTE = '{{ aws_remote }}';
  const GCP_REMOTE = '{{ gcp_remote }}';

  // Local offline URLs served by Flask static
  const AWS_LOCAL = '{{ aws_local }}';
  const GCP_LOCAL = '{{ gcp_local }}';

  let AWS_PACK_URL = AWS_REMOTE;
  let GCP_PACK_URL = GCP_REMOTE;

  document.getElementById('aws-url').textContent = 'auto (offline if available)';
  document.getElementById('gcp-url').textContent = 'auto (offline if available)';

  let currentScale = 1;
  mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });

  async function checkPacksStatus() {
    const r = await fetch('/packs-status').then(r => r.json());
    const statusEl = document.getElementById('packs-status');
    const banner = document.getElementById('packs-banner');

    if (r.aws && r.gcp) {
      AWS_PACK_URL = AWS_LOCAL;
      GCP_PACK_URL = GCP_LOCAL;
      statusEl.textContent = 'offline ready (AWS + GCP cached)';
      banner.className = 'notice';
      banner.style.display = '';
      banner.textContent = '✅ Icon packs downloaded. Offline mode enabled.';
    } else {
      AWS_PACK_URL = r.aws ? AWS_LOCAL : AWS_REMOTE;
      GCP_PACK_URL = r.gcp ? GCP_LOCAL : GCP_REMOTE;
      const missing = [];
      if (!r.aws) missing.push('AWS');
      if (!r.gcp) missing.push('GCP');
      statusEl.textContent = missing.length ? ('missing: ' + missing.join(', ')) : 'partial';
      banner.className = 'warn';
      banner.style.display = '';
      banner.textContent = 'ℹ️ Click "Download icon packs (offline)" so this app and mermaid.py can run without internet.';
    }
  }

  async function downloadPacks() {
    const btn = document.getElementById('btn-download-packs');
    btn.disabled = true;
    btn.textContent = 'Downloading…';
    try {
      const r = await fetch('/download-packs', { method: 'POST' }).then(r => r.json());
      if (r.ok) {
        await checkPacksStatus();
        await rebuildIconRegistry(); // re-register with new URLs (local)
        await setupSamples();
        alert('✅ Icon packs downloaded. Offline ready.');
      } else {
        alert('❌ Failed to download packs: ' + (r.error || 'Unknown error'));
      }
    } catch (e) {
      alert('❌ Failed to download packs: ' + (e.message || e));
    } finally {
      btn.disabled = false;
      btn.textContent = 'Download icon packs (offline)';
    }
  }

  document.getElementById('btn-download-packs').addEventListener('click', downloadPacks);

  async function rebuildIconRegistry() {
    // Re-register loaders with the current URLs (offline or remote)
    mermaid.registerIconPacks([
      { name: 'aws', loader: () => fetch(AWS_PACK_URL, {cache: 'no-store'}).then(r => r.json()) },
      { name: 'gcp', loader: () => fetch(GCP_PACK_URL, {cache: 'no-store'}).then(r => r.json()) }
    ]);
  }

  async function renderDiagram() {
    const el = document.getElementById('diagram');
    const err = document.getElementById('err');
    err.textContent = '';
    el.innerHTML = '';
    currentScale = 1;
    el.style.transform = `scale(${currentScale})`;
    const code = document.getElementById('code').value;
    try {
      const { svg, bindFunctions } = await mermaid.render('mmd-' + Date.now(), code);
      el.innerHTML = svg;
      if (bindFunctions) bindFunctions(el);
    } catch (e) {
      err.textContent = (e && (e.message || e.error || e)) + '\n\nCheck icon pack availability and names.';
    }
  }

  document.getElementById('diagram-form').addEventListener('submit', function(ev){
    ev.preventDefault();
    renderDiagram();
  });

  document.getElementById('zoom-in').addEventListener('click', () => {
    currentScale += 0.1;
    document.getElementById('diagram').style.transform = `scale(${currentScale})`;
  });
  document.getElementById('zoom-out').addEventListener('click', () => {
    currentScale = Math.max(0.1, currentScale - 0.1);
    document.getElementById('diagram').style.transform = `scale(${currentScale})`;
  });

  function download(href, name) { const a = document.createElement('a'); a.href = href; a.download = name; a.click(); }
  document.getElementById('save-png').addEventListener('click', () => {
    const svgEl = document.querySelector('#diagram svg'); if (!svgEl) return;
    const svgData = new XMLSerializer().serializeToString(svgEl);
    const canvas = document.createElement('canvas'); const bbox = svgEl.getBBox();
    canvas.width = bbox.width; canvas.height = bbox.height;
    const ctx = canvas.getContext('2d'); const img = new Image();
    img.onload = function(){ ctx.drawImage(img,0,0); download(canvas.toDataURL('image/png'),'diagram.png'); }
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
  });
  document.getElementById('save-svg').addEventListener('click', () => {
    const svgEl = document.querySelector('#diagram svg'); if (!svgEl) return;
    const svgData = new XMLSerializer().serializeToString(svgEl);
    download('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData), 'diagram.svg');
  });

  async function loadIconList(container, url, prefix) {
      const data = await fetch(url, {cache: 'no-store'}).then(r => r.json());
      let keys = Object.keys((data && data.icons) || {});
      if (!keys.length) {
          const p = document.createElement('p');
          p.textContent = `No icons found for ${prefix.toUpperCase()}.`;
          container.appendChild(p);
          return [];
      }
      const title = document.createElement('strong');
      title.textContent = `${prefix.toUpperCase()} Icons (${keys.length}):`;
      container.appendChild(title);

      const wrapper = document.createElement('div');
      wrapper.innerHTML = keys.map(k => {
          let shortName = k.startsWith(prefix + "-") ? k.replace(prefix + "-", "") : k;
          return `<span class="badge" data-full="${prefix}:${shortName}">${prefix}:${shortName}</span>`;
      }).join('');
      container.appendChild(wrapper);

      wrapper.querySelectorAll('.badge').forEach(badge => {
          badge.addEventListener('click', () => {
              const textarea = document.getElementById('code');
              const iconCode = badge.dataset.full;
              const start = textarea.selectionStart, end = textarea.selectionEnd, text = textarea.value;
              textarea.value = text.substring(0, start) + iconCode + text.substring(end);
              textarea.focus();
              textarea.selectionStart = textarea.selectionEnd = start + iconCode.length;
              renderDiagram();
          });
      });

      return keys;
  }

  async function setupSamples() {
    try {
      const container = document.getElementById('icon-list');
      container.innerHTML = '';
      await loadIconList(container, AWS_PACK_URL, 'aws');
      await loadIconList(container, GCP_PACK_URL, 'gcp');

      const awsSample = `%%{init: {"theme": "default"}}%%
architecture-beta
  group "AWS Cloud"
    group client(aws:network-amazon-route-53)[Route 53]
    group web(aws:compute-amazon-ec2)[EC2]
    group data(aws:database-amazon-rds)[RDS]

    client -->> web: DNS Query
    web -->> data: DB Connection
  end`;
      document.getElementById('btn-insert-sample-aws').addEventListener('click', () => {
        document.getElementById('code').value = awsSample;
        renderDiagram();
      });

      const gcpSample = `%%{init: {"theme": "default"}}%%
architecture-beta
  actor "User" as user
  group "Google Cloud"
    service(gcp:networking-cloud-load-balancing)[Load Balancer] as lb
    group "Backend Services"
        service(gcp:compute-engine)[Compute Engine] as gce
        service(gcp:databases-cloud-sql)[Cloud SQL] as db
    end
    gce -->> db: Reads/Writes
    lb -->> gce: Forwards Traffic
  end
  user -->> lb: Request`;
      document.getElementById('btn-insert-sample-gcp').addEventListener('click', () => {
        document.getElementById('code').value = gcpSample;
        renderDiagram();
      });

    } catch (e) {
      document.getElementById('icon-list').textContent = 'Failed to load icon list: ' + (e.message || e);
    }
  }

  try { document.getElementById('mm-ver').textContent = mermaid.version; } catch {}

  (async function init(){
    await checkPacksStatus();
    await rebuildIconRegistry();
    await setupSamples();
    {% if code %} renderDiagram(); {% endif %}
  })();
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
    return jsonify({
        "aws": AWS_LOCAL.exists(),
        "gcp": GCP_LOCAL.exists()
    })

@app.route('/download-packs', methods=['POST'])
def download_packs():
    try:
        _download(AWS_REMOTE, AWS_LOCAL)
        _download(GCP_REMOTE, GCP_LOCAL)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# (Optional) serve files if needed explicitly
@app.route('/static/packs/<path:filename>')
def serve_packs(filename):
    return send_from_directory(PACKS_DIR, filename)

if __name__ == '__main__':
    # Run on 5001 to match your previous setup
    app.run(host='0.0.0.0', port=5001, debug=True)
