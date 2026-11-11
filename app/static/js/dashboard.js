/**
 * Interactive Dashboard JavaScript for BBVA Fondos App
 * Renders all columns extracted from the official BBVA Anaquel PDF.
 */

let state = {
  page: 1,
  limit: 25,
  total: 0,
  search: "",
  segment: "",
  category: "",
  is_debt_only: false,
  only_favorites: false,
  sort_by: "ticker",
  order: "ASC",
  view_mode: window.innerWidth < 768 ? "cards" : "table",
  chartInstance: null
};

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});

async function initDashboard() {
  applyViewMode();
  await loadTelemetry();
  await loadFilters();
  await loadSeriesTable();
  setupEventListeners();
}

function applyViewMode() {
  const tableView = document.getElementById("seriesTableView");
  const cardsView = document.getElementById("seriesCardsContainer");
  const cardsBtn = document.getElementById("viewCardsBtn");
  const tableBtn = document.getElementById("viewTableBtn");

  if (state.view_mode === "cards") {
    if (tableView) tableView.style.display = "none";
    if (cardsView) cardsView.style.display = "grid";
    if (cardsBtn) cardsBtn.classList.add("active");
    if (tableBtn) tableBtn.classList.remove("active");
  } else {
    if (tableView) tableView.style.display = "block";
    if (cardsView) cardsView.style.display = "none";
    if (tableBtn) tableBtn.classList.add("active");
    if (cardsBtn) cardsBtn.classList.remove("active");
  }
}

function setViewMode(mode) {
  state.view_mode = mode;
  applyViewMode();
}

function setupEventListeners() {
  // Debounced search
  let debounceTimer;
  document.getElementById("searchInput").addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.search = e.target.value.trim();
      state.page = 1;
      loadSeriesTable();
    }, 300);
  });

  // Filter pills
  document.querySelectorAll(".pill-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const filterType = btn.dataset.filter;
      if (filterType === "favorites") {
        state.only_favorites = true;
        state.segment = "";
        state.is_debt_only = false;
      } else if (filterType === "debt-pf") {
        state.only_favorites = false;
        state.segment = "Personas Físicas";
        state.is_debt_only = true;
        document.getElementById("categorySelect").value = "";
        state.category = "";
      } else if (filterType === "pf") {
        state.only_favorites = false;
        state.segment = "Personas Físicas";
        state.is_debt_only = false;
      } else if (filterType === "pm") {
        state.only_favorites = false;
        state.segment = "Personas Morales";
        state.is_debt_only = false;
      } else if (filterType === "colab") {
        state.only_favorites = false;
        state.segment = "Colaboradores BBVA";
        state.is_debt_only = false;
      } else {
        state.only_favorites = false;
        state.segment = "";
        state.is_debt_only = false;
      }

      state.page = 1;
      loadSeriesTable();
    });
  });

  // Category select
  document.getElementById("categorySelect").addEventListener("change", (e) => {
    state.category = e.target.value;
    state.page = 1;
    loadSeriesTable();
  });

  // Sorting select
  document.getElementById("sortSelect").addEventListener("change", (e) => {
    const [sortBy, order] = e.target.value.split(":");
    state.sort_by = sortBy;
    state.order = order;
    state.page = 1;
    loadSeriesTable();
  });

  // View mode switcher (Cards vs Table)
  const cardsBtn = document.getElementById("viewCardsBtn");
  if (cardsBtn) {
    cardsBtn.addEventListener("click", () => setViewMode("cards"));
  }
  const tableBtn = document.getElementById("viewTableBtn");
  if (tableBtn) {
    tableBtn.addEventListener("click", () => setViewMode("table"));
  }

  // Sync button
  document.getElementById("syncBtn").addEventListener("click", handleSync);

  // Test Notification button
  const testBtn = document.getElementById("testNotifyBtn");
  if (testBtn) {
    testBtn.addEventListener("click", handleTestNotification);
  }

  // Pagination buttons
  document.getElementById("prevPageBtn").addEventListener("click", () => {
    if (state.page > 1) {
      state.page--;
      loadSeriesTable();
    }
  });

  document.getElementById("nextPageBtn").addEventListener("click", () => {
    const maxPage = Math.ceil(state.total / state.limit);
    if (state.page < maxPage) {
      state.page++;
      loadSeriesTable();
    }
  });

  // Modal events
  document.getElementById("closeModalBtn").addEventListener("click", closeModal);
  document.getElementById("detailModal").addEventListener("click", (e) => {
    if (e.target.id === "detailModal") closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
}

function getApiBase() {
  const path = window.location.pathname;
  const match = path.match(/^(\/api\/hassio_ingress\/[^\/]+)/);
  if (match) {
    return match[1];
  }
  if (window.INGRESS_ROOT) {
    return window.INGRESS_ROOT.replace(/\/$/, "");
  }
  return "";
}

async function loadTelemetry() {
  try {
    const res = await fetch(`${getApiBase()}/api/v1/health`);
    const json = await res.json();
    if (json.success && json.data) {
      const d = json.data;
      document.getElementById("kpiTotalFunds").textContent = d.total_funds.toLocaleString();
      document.getElementById("kpiTotalSeries").textContent = d.total_series.toLocaleString();
      document.getElementById("kpiLastDate").textContent = d.last_report_date || "Sin datos";
      const syncInfo = d.auto_sync_enabled ? `Auto: ${d.auto_sync_time} hrs` : "Manual";
      const lastSyncText = d.last_sync_time ? ` · Último: ${d.last_sync_time.split(" ")[1] || d.last_sync_time}` : "";
      document.getElementById("kpiSyncStatus").textContent = `${syncInfo}${lastSyncText}`;
    }
  } catch (err) {
    console.error("Error loading telemetry:", err);
  }
}

async function loadFilters() {
  try {
    const res = await fetch(`${getApiBase()}/api/v1/filters`);
    const json = await res.json();
    if (json.success && json.data) {
      const select = document.getElementById("categorySelect");
      select.innerHTML = '<option value="">Todas las Categorías</option>';
      json.data.categories.forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Error loading filters:", err);
  }
}

function formatPercent(val) {
  if (val === null || val === undefined) return '<span class="text-muted">-</span>';
  const cls = val >= 0 ? "yield-pos" : "yield-neg";
  const sign = val > 0 ? "+" : "";
  return `<span class="mono ${cls}">${sign}${val.toFixed(2)}%</span>`;
}

function formatCurrency(val) {
  if (val === null || val === undefined) return '<span class="text-muted">-</span>';
  return `<span class="mono" style="font-weight: 600;">$${val.toFixed(4)}</span>`;
}

async function loadSeriesTable() {
  const tbody = document.getElementById("seriesTableBody");
  const cardsContainer = document.getElementById("seriesCardsContainer");

  tbody.innerHTML = `<tr><td colspan="16" style="text-align: center; padding: 30px; color: var(--text-secondary);">Cargando catálogo completo de fondos...</td></tr>`;
  if (cardsContainer) {
    cardsContainer.innerHTML = `<div style="text-align: center; padding: 30px; color: var(--text-secondary);">Cargando catálogo de fondos...</div>`;
  }

  try {
    const params = new URLSearchParams({
      page: state.page,
      limit: state.limit,
      sort_by: state.sort_by,
      order: state.order,
      is_debt_only: state.is_debt_only ? "true" : "false",
      only_favorites: state.only_favorites ? "true" : "false"
    });
    if (state.search) params.append("search", state.search);
    if (state.segment) params.append("segment", state.segment);
    if (state.category) params.append("category", state.category);

    const res = await fetch(`${getApiBase()}/api/v1/series?${params.toString()}`);
    const json = await res.json();

    if (!json.success || !json.data) {
      tbody.innerHTML = `<tr><td colspan="16" style="text-align: center; color: var(--accent-danger);">Error al cargar las series de fondos</td></tr>`;
      if (cardsContainer) {
        cardsContainer.innerHTML = `<div style="text-align: center; color: var(--accent-danger); padding: 20px;">Error al cargar las series de fondos</div>`;
      }
      return;
    }

    state.total = json.meta?.total || 0;
    updatePaginationUI();

    if (json.data.length === 0) {
      const emptyMsg = state.only_favorites 
        ? "No tienes fondos marcados como favoritos aún. Haz clic en la estrella ★ de cualquier fondo para agregarlo."
        : "No se encontraron fondos con los filtros aplicados.";
      tbody.innerHTML = `<tr><td colspan="16" style="text-align: center; padding: 40px; color: var(--text-muted);">${emptyMsg}</td></tr>`;
      if (cardsContainer) {
        cardsContainer.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">${emptyMsg}</div>`;
      }
      return;
    }

    tbody.innerHTML = "";
    if (cardsContainer) cardsContainer.innerHTML = "";

    json.data.forEach(item => {
      const califBadge = item.calificacion 
        ? `<span class="badge" style="background: rgba(14, 165, 233, 0.15); color: #38bdf8;">${item.calificacion}</span>`
        : '<span class="text-muted" style="font-size: 11px;">N/A</span>';

      const favClass = item.is_favorite ? "fav-star-btn is-fav" : "fav-star-btn";
      const favChar = item.is_favorite ? "★" : "☆";
      const favTitle = item.is_favorite ? "Quitar de favoritos" : "Marcar como favorito";

      // 1. Render Desktop Table Row
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="text-align: center;">
          <button class="${favClass}" onclick="toggleFavorite('${item.ticker}', '${item.series}', this, event)" title="${favTitle}">${favChar}</button>
        </td>
        <td style="font-weight: 700; color: #fff;">${item.ticker}</td>
        <td><span class="badge badge-series">${item.series}</span></td>
        <td><span class="badge badge-segment">${item.segment}</span></td>
        <td style="color: var(--text-secondary); font-size: 12px;">${item.category}</td>
        <td class="mono" style="text-align: right;">$${(item.minimo_inversion || 0).toLocaleString()}</td>
        <td style="text-align: center;">${califBadge}</td>
        <td style="text-align: right;">${formatPercent(item.rendimiento_diario)}</td>
        <td style="text-align: right;">${formatPercent(item.rendimiento_semanal)}</td>
        <td style="text-align: right;">${formatPercent(item.rendimiento_mes)}</td>
        <td style="text-align: right;">${formatPercent(item.rendimiento_anio)}</td>
        <td style="text-align: right; font-weight: 700;">${formatPercent(item.rendimiento_1a)}</td>
        <td style="text-align: right;">${formatPercent(item.rendimiento_2a)}</td>
        <td style="text-align: right;">${formatCurrency(item.precio)}</td>
        <td class="mono" style="text-align: center; color: var(--text-muted); font-size: 11px;">${item.report_date || "-"}</td>
        <td style="text-align: center;">
          <button class="btn btn-outline" style="padding: 3px 8px; font-size: 11px;" onclick="openHistoricalModal('${item.ticker}', '${item.series}', '${item.segment}')">
            📈 Graficar
          </button>
        </td>
      `;
      tbody.appendChild(tr);

      // 2. Render Mobile / Responsive Card (No horizontal scroll needed!)
      if (cardsContainer) {
        const card = document.createElement("div");
        card.className = "fund-card";
        card.onclick = (e) => {
          if (e.target.closest(".fav-star-btn")) return;
          openHistoricalModal(item.ticker, item.series, item.segment);
        };

        const califCardBadge = item.calificacion 
          ? `<span class="badge-calif">${item.calificacion}</span>`
          : '';

        card.innerHTML = `
          <div class="fund-card-header">
            <div class="fund-card-title-group">
              <button class="${favClass}" onclick="toggleFavorite('${item.ticker}', '${item.series}', this, event)" title="${favTitle}">${favChar}</button>
              <span class="fund-ticker">${item.ticker}</span>
              <span class="badge badge-series">${item.series}</span>
              <span class="badge badge-segment">${item.segment}</span>
            </div>
            <div class="fund-card-price-group">
              <span class="fund-price">${formatCurrency(item.precio)}</span>
              <span class="fund-date">${item.report_date || "-"}</span>
            </div>
          </div>

          <div class="fund-card-meta">
            <span>${item.category}</span>
            ${califCardBadge}
          </div>

          <div class="fund-card-yields">
            <div class="yield-pill-card highlight">
              <span class="yield-card-lbl">Mes</span>
              <span class="yield-card-val">${formatPercent(item.rendimiento_mes)}</span>
            </div>
            <div class="yield-pill-card">
              <span class="yield-card-lbl">1 Año</span>
              <span class="yield-card-val">${formatPercent(item.rendimiento_1a)}</span>
            </div>
            <div class="yield-pill-card">
              <span class="yield-card-lbl">Diario</span>
              <span class="yield-card-val">${formatPercent(item.rendimiento_diario)}</span>
            </div>
            <div class="yield-pill-card">
              <span class="yield-card-lbl">Acum Año</span>
              <span class="yield-card-val">${formatPercent(item.rendimiento_anio)}</span>
            </div>
          </div>

          <div class="fund-card-footer">
            <span>Mínimo: $${(item.minimo_inversion || 0).toLocaleString()}</span>
            <button class="btn btn-outline btn-xs" onclick="event.stopPropagation(); openHistoricalModal('${item.ticker}', '${item.series}', '${item.segment}')">
              📈 Gráfica & Histórico
            </button>
          </div>
        `;
        cardsContainer.appendChild(card);
      }
    });

  } catch (err) {
    console.error("Error loading table:", err);
    tbody.innerHTML = `<tr><td colspan="16" style="text-align: center; color: var(--accent-danger);">Error de conexión con el servicio</td></tr>`;
    if (cardsContainer) {
      cardsContainer.innerHTML = `<div style="text-align: center; color: var(--accent-danger); padding: 20px;">Error de conexión con el servicio</div>`;
    }
  }
}

function updatePaginationUI() {
  const maxPage = Math.ceil(state.total / state.limit) || 1;
  document.getElementById("pageInfo").textContent = `Página ${state.page} de ${maxPage} (${state.total} series registradas)`;
  document.getElementById("prevPageBtn").disabled = state.page <= 1;
  document.getElementById("nextPageBtn").disabled = state.page >= maxPage;
}

async function handleSync() {
  const btn = document.getElementById("syncBtn");
  btn.disabled = true;
  btn.textContent = "Sincronizando PDF...";

  try {
    const res = await fetch(`${getApiBase()}/api/v1/sync`, { method: "POST" });
    const json = await res.json();
    if (json.success) {
      showToast(json.data.message || "Sincronización completada con éxito.", "success");
      await loadTelemetry();
      await loadFilters();
      await loadSeriesTable();
    } else {
      showToast(json.error?.message || "Error al sincronizar el Anaquel de BBVA.", "error");
    }
  } catch (err) {
    console.error("Sync error:", err);
    showToast("Error de conexión durante la sincronización.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Sincronizar PDF";
  }
}

async function openHistoricalModal(ticker, series, segment) {
  const modal = document.getElementById("detailModal");
  document.getElementById("modalTitle").textContent = `${ticker} · Serie ${series} (${segment})`;
  document.getElementById("modalSubtitle").textContent = "Cargando historial de precios y rendimientos...";
  modal.classList.add("open");

  try {
    const res = await fetch(`${getApiBase()}/api/v1/funds/${ticker}/${series}/history?segment=${encodeURIComponent(segment)}`);
    const json = await res.json();

    const history = json.data || [];
    document.getElementById("modalSubtitle").textContent = `${history.length} snapshot(s) históricos guardados en base de datos`;

    // Populate snapshots table
    const tableBody = document.getElementById("modalSnapshotsBody");
    tableBody.innerHTML = "";

    history.slice().reverse().forEach(h => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="mono">${h.report_date}</td>
        <td class="mono" style="text-align: right; font-weight: 600;">$${h.precio.toFixed(4)}</td>
        <td style="text-align: right;">${formatPercent(h.rendimiento_diario)}</td>
        <td style="text-align: right;">${formatPercent(h.rendimiento_semanal)}</td>
        <td style="text-align: right;">${formatPercent(h.rendimiento_mes)}</td>
        <td style="text-align: right;">${formatPercent(h.rendimiento_anio)}</td>
        <td style="text-align: right; font-weight: 700;">${formatPercent(h.rendimiento_1a)}</td>
        <td style="text-align: right;">${formatPercent(h.rendimiento_2a)}</td>
      `;
      tableBody.appendChild(tr);
    });

    // Render Chart.js
    const ctx = document.getElementById("historyChartCanvas").getContext("2d");
    const labels = history.map(h => h.report_date);
    const prices = history.map(h => h.precio);
    const yields = history.map(h => h.rendimiento_1a);

    if (state.chartInstance) {
      state.chartInstance.destroy();
    }

    state.chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels.length > 0 ? labels : ["Hoy"],
        datasets: [
          {
            label: `Precio ${ticker} (${series})`,
            data: prices.length > 0 ? prices : [0],
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.12)",
            borderWidth: 2,
            tension: 0.2,
            yAxisID: "y",
            fill: true,
          },
          {
            label: "Rendimiento 1A (%)",
            data: yields.length > 0 ? yields : [0],
            borderColor: "#38bdf8",
            borderWidth: 1.5,
            borderDash: [5, 5],
            tension: 0.2,
            yAxisID: "y1",
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#fafafa", font: { family: "system-ui" } } },
          tooltip: {
            backgroundColor: "#18181b",
            titleColor: "#fafafa",
            bodyColor: "#a1a1aa",
            borderColor: "#27272a",
            borderWidth: 1,
          }
        },
        scales: {
          x: { grid: { color: "#27272a" }, ticks: { color: "#a1a1aa" } },
          y: {
            type: "linear",
            position: "left",
            grid: { color: "#27272a" },
            ticks: {
              color: "#10b981",
              callback: (val) => `$${val}`
            }
          },
          y1: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: {
              color: "#38bdf8",
              callback: (val) => `${val}%`
            }
          }
        }
      }
    });

  } catch (err) {
    console.error("Error opening historical modal:", err);
  }
}

function closeModal() {
  document.getElementById("detailModal").classList.remove("open");
  if (state.chartInstance) {
    state.chartInstance.destroy();
    state.chartInstance = null;
  }
}

function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 4000);
}

async function toggleFavorite(ticker, series, btn, event) {
  if (event) event.stopPropagation();

  // Optimistic UI toggle
  const wasFav = btn.classList.contains("is-fav");
  const newFav = !wasFav;
  btn.classList.toggle("is-fav", newFav);
  btn.textContent = newFav ? "★" : "☆";
  btn.title = newFav ? "Quitar de favoritos" : "Marcar como favorito";

  try {
    const res = await fetch(`${getApiBase()}/api/v1/favorites/${encodeURIComponent(ticker)}/${encodeURIComponent(series)}/toggle`, {
      method: "POST"
    });
    const json = await res.json();
    if (json.success && json.data) {
      showToast(json.data.message, "success");
      // Synchronize counterpart star buttons (card vs table)
      document.querySelectorAll(`button[onclick*="'${ticker}', '${series}'"]`).forEach(otherBtn => {
        if (otherBtn !== btn) {
          otherBtn.classList.toggle("is-fav", newFav);
          otherBtn.textContent = newFav ? "★" : "☆";
          otherBtn.title = newFav ? "Quitar de favoritos" : "Marcar como favorito";
        }
      });
      // If we are currently filtering by favorites, refresh the view
      if (state.only_favorites) {
        loadSeriesTable();
      }
    } else {
      // Revert optimistic state
      btn.classList.toggle("is-fav", wasFav);
      btn.textContent = wasFav ? "★" : "☆";
      showToast(json.error?.message || "No se pudo actualizar favorito", "error");
    }
  } catch (err) {
    console.error("Error toggling favorite:", err);
    btn.classList.toggle("is-fav", wasFav);
    btn.textContent = wasFav ? "★" : "☆";
    showToast("Error de conexión al marcar favorito", "error");
  }
}

async function handleTestNotification() {
  const btn = document.getElementById("testNotifyBtn");
  if (!btn) return;
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "🔔 Enviando alerta...";

  try {
    const res = await fetch(`${getApiBase()}/api/v1/notifications/test`, {
      method: "POST"
    });
    const json = await res.json();
    if (json.success && json.data) {
      const d = json.data;
      if (d.sent) {
        showToast(`✅ Alerta enviada a ${d.device} (${d.favorites_count} favoritos)`, "success");
      } else {
        showToast(`⚠️ Home Assistant: ${d.device || 'Sin dispositivo'} (Evento emitido: ${d.event_fired})`, "error");
      }
    } else {
      showToast("Error al invocar servicio de notificación", "error");
    }
  } catch (err) {
    console.error("Error testing notification:", err);
    showToast("Error de comunicación con Home Assistant", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}
