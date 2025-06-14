// Show loading spinner
function showLoading() {
  document.getElementById('loading').style.display = 'flex';
  document.getElementById('world-list').style.display = 'none';
}

// Hide loading spinner
function hideLoading() {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('world-list').style.display = 'flex';
}

// Update world count
function updateWorldCount(count) {
  document.getElementById('world-count').textContent = count;
}

// Render worlds
function renderWorlds(worlds) {
  const list = document.getElementById('world-list');
  
  list.innerHTML = '';
  worlds.forEach(world => {
    const el = document.createElement("div");
    el.className = "world";
    el.innerHTML = `
      <div class="world-row">
        <div class="world-title-section">
          <div class="world-title">
            ${world.world_name}
          </div>
          <div class="world-version">v${world.version}</div>
        </div>
        <div class="world-meta">
          <div class="meta-item">
            <span class="meta-label">Developer</span>
            <span class="meta-value">${world.dev_name || "Unknown"}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Last Updated</span>
            <span class="meta-value">${world.last_updated || "N/A"}</span>
          </div>
        </div>
        <div class="world-download">
          <a href="${world.download_url}" class="download-link" target="_blank">
            <i class="fas fa-download"></i>
            Download
          </a>
        </div>
      </div>
    `;
    list.appendChild(el);
  });
  
  updateWorldCount(worlds.length);
}

// Load worlds from API
function loadWorlds() {
  showLoading();
  
  fetch("/api/worlds/")
    .then(res => res.json())
    .then(data => {
      renderWorlds(data);
      hideLoading();
    })
    .catch(err => {
      console.error("Failed to load worlds:", err);
      hideLoading();
      document.getElementById("world-list").innerHTML = 
        '<div class="error-message"><i class="fas fa-exclamation-triangle"></i><br>Error loading world list. Please refresh the page.</div>';
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  loadWorlds();
});