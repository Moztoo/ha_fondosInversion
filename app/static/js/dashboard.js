/**
 * Interactive Dashboard JavaScript for BBVA Fondos
 */

let state = {
  page: 1,
  limit: 25,
  total: 0,
  search: "",
  segment: "",
  category: "",
  chartInstance: null
};

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});

async function initDashboard() {
  await loadTelemetry();
  await loadFilters();
  await loadFundsTable();
  setupEventListeners();
}

function setupEventListeners() {
  // Search input debounced
  let debounceTimer;
  document.getElementById("searchInput").addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.search = e.target.value.trim();
      state.page = 1;
      loadFundsTable();
    }, 300);
  });

  // Segment pill buttons
  document.querySelectorAll(".pill-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.segment = btn.dataset.segment || "";
      state.page = 1;
      loadFundsTable();
    });
  });

  // Category select
  document.getElementById("categorySelect").addEventListener("change", (e) => {
    state.category = e.target.value;
    state.page = 1;
    loadFundsTable();
  });

  // Sync button
  document.getElementById("syncBtn").addEventListener("click", handleSync);

  // Pagination buttons
  document.getElementById("prevPageBtn").addEventListener("click", () => {
    if (state.page > 1) {
      state.page--;
      loadFundsTable();
    }
  });

  document.getElementById("nextPageBtn").addEventListener("click", () => {
    const maxPage = Math.ceil(state.total / state.limit);
    if (state.page < maxPage) {
      state.page++;
      loadFundsTable();
    }
  });

  // Modal close
  document.getElementById("closeModalBtn").addEventListener("click", closeModal);
  document.getElementById("detailModal").addEventListener("click", (e) => {
    if (e.target.id === "detailModal") closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
}

async function loadTelemetry() {
  try {
    const res = await fetch("/api/v1/health");
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
    const res = await fetch("/api/v1/filters");
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

async function loadFundsTable() {
  const tbody = document.getElementById("fundsTableBody");
  tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 30px; color: var(--text-secondary);">Cargando fondos...</td></tr>`;

  try {
    const params = new URLSearchParams({
      page: state.page,
      limit: state.limit,
    });
    if (state.search) params.append("search", state.search);
    if (state.segment) params.append("segment", state.segment);
    if (state.category) params.append("category", state.category);

    const res = await fetch(`/api/v1/funds?${params.toString()}`);
    const json = await res.json();

    if (!json.success || !json.data) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--accent-danger);">Error al cargar los datos</td></tr>`;
      return;
    }

    state.total = json.meta?.total || 0;
    updatePaginationUI();

    if (json.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 40px; color: var(--text-muted);">No se encontraron fondos con los filtros aplicados.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    json.data.forEach(fund => {
      const tr = document.createElement("tr");

      // Series tags
      const seriesBadges = (fund.series_list || [])
        .slice(0, 5)
        .map(s => `<span class="badge badge-series">${s}</span>`)
        .join("") + (fund.series_list.length > 5 ? `<span class="badge badge-series">+${fund.series_list.length - 5}</span>` : "");

      // 1 Year Yield formatting
      let yieldHtml = '<span class="mono text-muted">-</span>';
      if (fund.latest_rendimiento_1a !== null && fund.latest_rendimiento_1a !== undefined) {
        const cls = fund.latest_rendimiento_1a >= 0 ? "yield-pos" : "yield-neg";
        const sign = fund.latest_rendimiento_1a > 0 ? "+" : "";
        yieldHtml = `<span class="mono ${cls}">${sign}${fund.latest_rendimiento_1a.toFixed(2)}%</span>`;
      }

      // Price formatting
      const priceHtml = fund.latest_price !== null && fund.latest_price !== undefined
        ? `<span class="mono" style="font-weight: 600;">$${fund.latest_price.toFixed(4)}</span>`
        : '<span class="mono text-muted">-</span>';

      tr.innerHTML = `
        <td style="font-weight: 700; color: #fff;">${fund.ticker}</td>
        <td><span class="badge badge-segment">${fund.segment}</span></td>
        <td style="color: var(--text-secondary);">${fund.category}</td>
        <td>${seriesBadges}</td>
        <td>${priceHtml}</td>
        <td>${yieldHtml}</td>
        <td class="mono" style="color: var(--text-muted); font-size: 12px;">${fund.latest_report_date || "-"}</td>
        <td>
          <button class="btn btn-outline" style="padding: 4px 10px; font-size: 11px;" onclick="openDetailModal('${fund.ticker}', '${fund.segment}')">
            Detalle e Historial
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Error loading table:", err);
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--accent-danger);">Error de conexión con el servicio</td></tr>`;
  }
}

function updatePaginationUI() {
  const maxPage = Math.ceil(state.total / state.limit) || 1;
  document.getElementById("pageInfo").textContent = `Página ${state.page} de ${maxPage} (${state.total} fondos)`;
  document.getElementById("prevPageBtn").disabled = state.page <= 1;
  document.getElementById("nextPageBtn").disabled = state.page >= maxPage;
}

async function handleSync() {
  const btn = document.getElementById("syncBtn");
  btn.disabled = true;
  btn.textContent = "Sincronizando PDF...";

  try {
    const res = await fetch("/api/v1/sync", { method: "POST" });
    const json = await res.json();
    if (json.success) {
      showToast(json.data.message || "Sincronización completada con éxito.", "success");
      await loadTelemetry();
      await loadFilters();
      await loadFundsTable();
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

async function openDetailModal(ticker, segment) {
  const modal = document.getElementById("detailModal");
  document.getElementById("modalTitle").textContent = `${ticker} (${segment})`;
  document.getElementById("modalSubtitle").textContent = "Cargando series y datos históricos...";
  modal.classList.add("open");

  try {
    const res = await fetch(`/api/v1/funds/${ticker}?segment=${encodeURIComponent(segment)}`);
    const json = await res.json();

    if (!json.success || !json.data || json.data.length === 0) {
      document.getElementById("modalSubtitle").textContent = "No se encontraron detalles para este fondo.";
      return;
    }

    const seriesData = json.data;
    document.getElementById("modalSubtitle").textContent = `${seriesData[0].category} · ${seriesData.length} series registradas`;

    // Populate series table
    const tableBody = document.getElementById("modalSeriesBody");
    tableBody.innerHTML = "";

    seriesData.forEach((s, idx) => {
      const snap = s.latest_snapshot || {};
      const tr = document.createElement("tr");

      const rendDia = snap.rendimiento_diario != null ? `${snap.rendimiento_diario >= 0 ? "+" : ""}${snap.rendimiento_diario.toFixed(2)}%` : "-";
      const rendMes = snap.rendimiento_mes != null ? `${snap.rendimiento_mes >= 0 ? "+" : ""}${snap.rendimiento_mes.toFixed(2)}%` : "-";
      const rend1a = snap.rendimiento_1a != null ? `${snap.rendimiento_1a >= 0 ? "+" : ""}${snap.rendimiento_1a.toFixed(2)}%` : "-";
      const precio = snap.precio != null ? `$${snap.precio.toFixed(4)}` : "-";

      tr.innerHTML = `
        <td style="font-weight: 700;"><span class="badge badge-series">${s.series}</span></td>
        <td class="mono">$${(s.minimo_inversion || 0).toLocaleString()}</td>
        <td>${s.calificacion || '<span class="text-muted">N/A</span>'}</td>
        <td class="mono" style="font-weight: 600;">${precio}</td>
        <td class="mono">${rendDia}</td>
        <td class="mono">${rendMes}</td>
        <td class="mono ${snap.rendimiento_1a >= 0 ? "yield-pos" : "yield-neg"}">${rend1a}</td>
        <td>
          <button class="btn btn-outline" style="padding: 2px 8px; font-size: 11px;" onclick="loadSeriesChart('${ticker}', '${s.series}', '${segment}')">
            Graficar
          </button>
        </td>
      `;
      tableBody.appendChild(tr);
    });

    // Default graph first series
    if (seriesData.length > 0) {
      loadSeriesChart(ticker, seriesData[0].series, segment);
    }

  } catch (err) {
    console.error("Error opening modal:", err);
  }
}

async function loadSeriesChart(ticker, series, segment) {
  try {
    const res = await fetch(`/api/v1/funds/${ticker}/${series}/history?segment=${encodeURIComponent(segment)}`);
    const json = await res.json();

    const history = json.data || [];
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
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            borderWidth: 2,
            tension: 0.2,
            yAxisID: "y",
            fill: true,
          },
          {
            label: "Rendimiento 1A (%)",
            data: yields.length > 0 ? yields : [0],
            borderColor: "#0ea5e9",
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
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            labels: { color: "#fafafa", font: { family: "system-ui" } }
          },
          tooltip: {
            backgroundColor: "#18181b",
            titleColor: "#fafafa",
            bodyColor: "#a1a1aa",
            borderColor: "#27272a",
            borderWidth: 1,
          }
        },
        scales: {
          x: {
            grid: { color: "#27272a" },
            ticks: { color: "#a1a1aa" }
          },
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
              color: "#0ea5e9",
              callback: (val) => `${val}%`
            }
          }
        }
      }
    });

  } catch (err) {
    console.error("Error charting series:", err);
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
