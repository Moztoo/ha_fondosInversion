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
  sort_by: "ticker",
  order: "ASC",
  chartInstance: null
};

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});

async function initDashboard() {
  await loadTelemetry();
  await loadFilters();
  await loadSeriesTable();
  setupEventListeners();
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
      if (filterType === "debt-pf") {
        state.segment = "Personas Físicas";
        state.is_debt_only = true;
        document.getElementById("categorySelect").value = "";
        state.category = "";
      } else if (filterType === "pf") {
        state.segment = "Personas Físicas";
        state.is_debt_only = false;
      } else if (filterType === "pm") {
        state.segment = "Personas Morales";
        state.is_debt_only = false;
      } else if (filterType === "colab") {
        state.segment = "Colaboradores BBVA";
        state.is_debt_only = false;
      } else {
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

  // Sync button
  document.getElementById("syncBtn").addEventListener("click", handleSync);

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
      document.getElementById("kpiSyncStatus").textContent = d.last_sync_time ? `Sincronizado: ${d.last_sync_time}` : "Pendiente de sincronizar";
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
  tbody.innerHTML = `<tr><td colspan="15" style="text-align: center; padding: 30px; color: var(--text-secondary);">Cargando catálogo completo de fondos...</td></tr>`;

  try {
    const params = new URLSearchParams({
      page: state.page,
      limit: state.limit,
      sort_by: state.sort_by,
      order: state.order,
      is_debt_only: state.is_debt_only ? "true" : "false"
    });
    if (state.search) params.append("search", state.search);
    if (state.segment) params.append("segment", state.segment);
    if (state.category) params.append("category", state.category);

    const res = await fetch(`${getApiBase()}/api/v1/series?${params.toString()}`);
    const json = await res.json();

    if (!json.success || !json.data) {
      tbody.innerHTML = `<tr><td colspan="15" style="text-align: center; color: var(--accent-danger);">Error al cargar las series de fondos</td></tr>`;
      return;
    }

    state.total = json.meta?.total || 0;
    updatePaginationUI();

    if (json.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="15" style="text-align: center; padding: 40px; color: var(--text-muted);">No se encontraron fondos con los filtros aplicados.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    json.data.forEach(item => {
      const tr = document.createElement("tr");

      const califBadge = item.calificacion 
        ? `<span class="badge" style="background: rgba(14, 165, 233, 0.15); color: #38bdf8;">${item.calificacion}</span>`
        : '<span class="text-muted" style="font-size: 11px;">N/A</span>';

      tr.innerHTML = `
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
    });

  } catch (err) {
    console.error("Error loading table:", err);
    tbody.innerHTML = `<tr><td colspan="15" style="text-align: center; color: var(--accent-danger);">Error de conexión con el servicio</td></tr>`;
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
