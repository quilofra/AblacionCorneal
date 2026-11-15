const DEBOUNCE_MS = 200;
const FALLBACK_PROCEDURES = [
  { value: "surface", label: "Superficie (PRK/PTK)" },
  { value: "lasik", label: "LASIK" },
  { value: "smile", label: "SMILE" },
];

const FALLBACK_ZONES = [6, 6.5];

const state = {
  config: null,
  laser: null,
  laserSeq: 0,
  laserAbort: null,
  laserTimer: null,
  requestSeq: 0,
  abortController: null,
  debounceTimer: null,
};

const elements = {
  procedureSelect: document.querySelector("#procedure-select"),
  zoneSelect: document.querySelector("#optical-zone-select"),
  sphereInput: document.querySelector("#sphere-input"),
  laserText: document.querySelector("#laser-text"),
  flapCapField: document.querySelector("#flap-cap-field"),
  flapCapLabel: document.querySelector("#flap-cap-label"),
  flapCapInput: document.querySelector("#flap-cap-input"),
  settingsHint: document.querySelector("#settings-hint"),
  paquiInput: document.querySelector("#paqui-input"),
  ablationInput: document.querySelector("#ablation-input"),
  suspiciousToggle: document.querySelector("#suspicious-toggle"),
  hintText: document.querySelector("#hint-text"),
  errorText: document.querySelector("#error-text"),
  statusBadge: document.querySelector("#status-badge"),
  maxSafeText: document.querySelector("#max-safe-text"),
  marginText: document.querySelector("#margin-text"),
  limitText: document.querySelector("#limit-text"),
  segmentLabels: document.querySelector("#segment-labels"),
  segmentFlap: document.querySelector("#segment-flap"),
  segmentAblation: document.querySelector("#segment-ablation"),
  segmentResidual: document.querySelector("#segment-residual"),
  copySummaryButton: document.querySelector("#copy-summary-button"),
  infoButton: document.querySelector("#info-button"),
  infoModal: document.querySelector("#info-modal"),
  infoBackdrop: document.querySelector("#info-backdrop"),
  infoCloseButton: document.querySelector("#info-close-button"),
  desktopNoteText: document.querySelector("#desktop-note-text"),
  downloadLinks: [
    document.querySelector("#download-link"),
    document.querySelector("#download-link-inline"),
  ],
  repoLinks: [
    document.querySelector("#repo-link"),
  ],
  metricValues: {
    ablation: document.querySelector("#ablation-pct-value"),
    lerUm: document.querySelector("#ler-um-value"),
    lerPct: document.querySelector("#ler-pct-value"),
    postop: document.querySelector("#postop-value"),
  },
  metricCards: {
    ablation: document.querySelector('[data-metric="ablation"]'),
    lerUm: document.querySelector('[data-metric="ler-um"]'),
    lerPct: document.querySelector('[data-metric="ler-pct"]'),
    postop: document.querySelector('[data-metric="postop"]'),
  },
  rules: {
    ablation: document.querySelector("#rule-ablation"),
    lerUm: document.querySelector("#rule-ler-um"),
    lerPct: document.querySelector("#rule-ler-pct"),
    postop: document.querySelector("#rule-postop"),
  },
};

function setLinkState(link, href) {
  if (!link) {
    return;
  }

  if (href) {
    link.href = href;
    link.classList.remove("is-disabled");
    link.setAttribute("aria-disabled", "false");
  } else {
    link.href = "#";
    link.classList.add("is-disabled");
    link.setAttribute("aria-disabled", "true");
  }
}

function openInfoModal() {
  elements.infoModal.classList.remove("is-hidden");
  elements.infoModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeInfoModal() {
  elements.infoModal.classList.add("is-hidden");
  elements.infoModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function bindInfoModal() {
  elements.infoButton.addEventListener("click", openInfoModal);
  elements.infoBackdrop.addEventListener("click", closeInfoModal);
  elements.infoCloseButton.addEventListener("click", closeInfoModal);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.infoModal.classList.contains("is-hidden")) {
      closeInfoModal();
    }
  });
}

function currentProcedure() {
  return elements.procedureSelect.value || "surface";
}

function tissueLabel(procedure) {
  if (procedure === "lasik") {
    return "Flap";
  }
  if (procedure === "smile") {
    return "Cap";
  }
  return "Flap/Cap";
}

function updateConfigurationUI() {
  const procedure = currentProcedure();
  const label = tissueLabel(procedure);
  const needsFlapCap = procedure !== "surface";

  elements.flapCapLabel.textContent = `Espesor ${label.toLowerCase()} (µm)`;
  elements.flapCapInput.placeholder = "120";
  elements.flapCapField.classList.toggle("is-hidden", !needsFlapCap);

  if (procedure !== "surface") {
    elements.settingsHint.textContent =
      `Se descontará ${label.toLowerCase()} para calcular el lecho residual.`;
  } else {
    elements.settingsHint.textContent =
      "Técnica de superficie: no descuenta flap/cap en el cálculo.";
  }
}

function setStatusBadge(status) {
  const labelMap = {
    ok: "Cumple",
    warning: "Cerca",
    fail: "No cumple",
    invalid: "No válido",
  };

  elements.statusBadge.textContent = labelMap[status] || "No válido";
  elements.statusBadge.dataset.state = status || "invalid";
}

function setMetric(card, valueElement, value, status = "neutral") {
  card.dataset.state = status;
  valueElement.textContent = value;
}

function setRule(ruleElement, status, value, threshold) {
  ruleElement.dataset.state = status;
  ruleElement.querySelector(".rule-icon").textContent =
    status === "pass" ? "✓" : status === "warn" ? "!" : status === "fail" ? "✕" : "–";
  ruleElement.querySelector(".rule-value").textContent = value;
  ruleElement.querySelector(".rule-threshold").textContent = threshold;
}

function updateSegments(flapCap, ablation, residual) {
  const total = flapCap + ablation + residual;

  if (!total) {
    elements.segmentFlap.style.flex = "1";
    elements.segmentAblation.style.flex = "1";
    elements.segmentResidual.style.flex = "1";
    return;
  }

  elements.segmentFlap.style.flex = `${Math.max(1, flapCap)}`;
  elements.segmentAblation.style.flex = `${Math.max(1, ablation)}`;
  elements.segmentResidual.style.flex = `${Math.max(1, residual)}`;
}

function resetResults() {
  setStatusBadge("invalid");
  setMetric(elements.metricCards.ablation, elements.metricValues.ablation, "–", "neutral");
  setMetric(elements.metricCards.lerUm, elements.metricValues.lerUm, "–", "neutral");
  setMetric(elements.metricCards.lerPct, elements.metricValues.lerPct, "–", "neutral");
  setMetric(elements.metricCards.postop, elements.metricValues.postop, "–", "neutral");

  elements.maxSafeText.textContent = "Máx ablación segura: –";
  elements.marginText.textContent = "Margen: –";
  elements.limitText.textContent = "Limita: –";
  elements.segmentLabels.textContent = `${tissueLabel(currentProcedure())} 0 µm · Ablación 0 µm · Residual 0 µm`;
  updateSegments(0, 0, 0);

  setRule(elements.rules.ablation, "neutral", "–", "");
  setRule(elements.rules.lerUm, "neutral", "–", "");
  setRule(elements.rules.lerPct, "neutral", "–", "");
  setRule(elements.rules.postop, "neutral", "–", "");
}

function buildSummary(result, paqui, ablation) {
  const statusLabel =
    result.overall_status === "ok"
      ? "Cumple"
      : result.overall_status === "warning"
        ? "Cerca"
        : "No cumple";

  const laser = state.laser && state.laser.found
    ? `esfera ${formatD(state.laser.sphere_d)} D, ZO ${formatZone(state.laser.optical_zone_mm)} mm (Teneo ${state.laser.ablation_um} µm${state.laser.interpolated ? ", interpolado" : ""}), `
    : "";

  return `${result.procedure_label}, ${laser}paqui preop ${paqui} µm, ablación ${ablation} µm (${result.ablation_pct.toFixed(1)}%), LER ${result.ler_um} µm (${result.ler_pct.toFixed(1)}%), post-op ${result.postop_paqui_um} µm, ${result.tissue_label.toLowerCase()} efectivo ${result.subtract_um} µm, estado ${statusLabel}, limita ${result.limit_factor}, máx segura ${result.ablation_max_safe_um} µm, margen ${result.margin_um >= 0 ? "+" : ""}${result.margin_um} µm.`;
}

function formatD(value) {
  const text = Number(value).toLocaleString("es-ES", { signDisplay: "exceptZero", maximumFractionDigits: 2 });
  return text.replace("-", "−");
}

function formatZone(value) {
  return Number(value).toLocaleString("es-ES", { maximumFractionDigits: 1 });
}

function showLaser(text) {
  elements.laserText.textContent = text;
}

function scheduleLaser() {
  window.clearTimeout(state.laserTimer);
  state.laserTimer = window.setTimeout(updateLaser, DEBOUNCE_MS);
}

async function updateLaser() {
  const seq = ++state.laserSeq;
  if (state.laserAbort) {
    state.laserAbort.abort();
    state.laserAbort = null;
  }

  const sphere = Number.parseFloat(elements.sphereInput.value);
  if (Number.isNaN(sphere)) {
    state.laser = null;
    showLaser("");
    return;
  }

  const controller = new AbortController();
  state.laserAbort = controller;
  const query = new URLSearchParams({
    sphere_d: String(sphere),
    optical_zone_mm: elements.zoneSelect.value,
  });

  let laser;
  try {
    const response = await fetch(`/api/laser-ablation?${query}`, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`http-${response.status}`);
    }
    laser = await response.json();
  } catch (error) {
    if (error.name !== "AbortError" && seq === state.laserSeq) {
      state.laser = null;
      showLaser("No se pudo consultar la tabla del láser.");
    }
    return;
  }

  if (seq !== state.laserSeq) {
    return;
  }
  state.laserAbort = null;
  state.laser = laser;

  if (!laser.found) {
    showLaser(laser.message);
    return;
  }

  const details = laser.interpolated
    ? "interpolado entre dos filas de la tabla"
    : `zona ${laser.zone_mm.replaceAll(".", ",")} mm · ${laser.time_s} s`;
  showLaser(
    `Teneo · ZO ${formatZone(laser.optical_zone_mm)} mm · ${formatD(laser.sphere_d)} D → ablación máx. ${laser.ablation_um} µm (${details}).`,
  );
  elements.ablationInput.value = String(laser.ablation_um);
  computeNow();
}

function showFailure(message) {
  elements.errorText.textContent = message;
  elements.hintText.textContent = "";
  resetResults();
}

function scheduleCompute() {
  window.clearTimeout(state.debounceTimer);
  state.debounceTimer = window.setTimeout(compute, DEBOUNCE_MS);
}

function computeNow() {
  window.clearTimeout(state.debounceTimer);
  compute();
}

async function compute() {
  const paqui = Number.parseInt(elements.paquiInput.value || "", 10);
  const ablation = Number.parseInt(elements.ablationInput.value || "", 10) || 0;
  const flapCap = Number.parseInt(elements.flapCapInput.value || "", 10) || 0;

  // Cualquier petición anterior queda obsoleta.
  const seq = ++state.requestSeq;
  if (state.abortController) {
    state.abortController.abort();
    state.abortController = null;
  }

  if (Number.isNaN(paqui)) {
    showFailure("Introduce paquimetría preop.");
    return;
  }

  const payload = {
    paqui_preop_um: paqui,
    ablation_um: ablation,
    suspicious: elements.suspiciousToggle.checked,
    procedure: currentProcedure(),
    flap_cap_um: flapCap,
  };

  const controller = new AbortController();
  state.abortController = controller;

  let result;
  try {
    const response = await fetch("/api/compute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(response.status === 422 ? "invalid" : `http-${response.status}`);
    }
    result = await response.json();
  } catch (error) {
    if (error.name === "AbortError" || seq !== state.requestSeq) {
      return;
    }
    showFailure(
      error.message === "invalid"
        ? "Valores fuera de rango: revisa las cifras introducidas."
        : "No se pudo calcular (sin conexión con el servidor). Se reintentará al cambiar un dato.",
    );
    return;
  }

  // Una respuesta lenta no debe pisar a una más reciente.
  if (seq !== state.requestSeq) {
    return;
  }
  state.abortController = null;

  if (!result.valid) {
    elements.errorText.textContent = result.errors?.[0] || "Entradas inconsistentes.";
    elements.hintText.textContent = "";
    resetResults();
    return;
  }

  elements.errorText.textContent = "";
  elements.hintText.textContent =
    paqui < 470 || paqui > 500
      ? "Paquimetría fuera del rango de referencia (470–500 µm)."
      : "";

  setStatusBadge(result.overall_status);
  setMetric(
    elements.metricCards.ablation,
    elements.metricValues.ablation,
    result.ablation_pct.toFixed(1),
    result.rule_ablation_status,
  );
  setMetric(
    elements.metricCards.lerUm,
    elements.metricValues.lerUm,
    `${result.ler_um}`,
    result.rule_ler_um_status,
  );
  setMetric(
    elements.metricCards.lerPct,
    elements.metricValues.lerPct,
    result.ler_pct.toFixed(1),
    result.rule_ler_pct_status,
  );
  setMetric(
    elements.metricCards.postop,
    elements.metricValues.postop,
    `${result.postop_paqui_um}`,
    result.rule_postop_status,
  );

  elements.maxSafeText.textContent = `Máx ablación segura: ${result.ablation_max_safe_um} µm`;
  elements.marginText.textContent = `Margen: ${result.margin_um >= 0 ? "+" : ""}${result.margin_um} µm`;
  elements.limitText.textContent = `Limita: ${result.limit_factor}`;
  elements.segmentLabels.textContent = `${result.tissue_label} ${result.subtract_um} µm · Ablación ${ablation} µm · Residual ${result.ler_um} µm`;
  updateSegments(result.subtract_um, ablation, result.ler_um);

  setRule(
    elements.rules.ablation,
    result.rule_ablation_status,
    `${result.ablation_pct.toFixed(1)} %`,
    `<= ${result.ablation_pct_threshold.toFixed(1)} %`,
  );
  setRule(
    elements.rules.lerUm,
    result.rule_ler_um_status,
    `${result.ler_um} µm`,
    `>= ${result.ler_um_threshold} µm`,
  );
  setRule(
    elements.rules.lerPct,
    result.rule_ler_pct_status,
    `${result.ler_pct.toFixed(1)} %`,
    `>= ${result.ler_pct_threshold.toFixed(1)} %`,
  );
  setRule(
    elements.rules.postop,
    result.rule_postop_status,
    `${result.postop_paqui_um} µm`,
    `>= ${result.postop_um_threshold} µm`,
  );

  elements.copySummaryButton.onclick = async () => {
    const button = elements.copySummaryButton;
    const original = button.dataset.label || button.textContent;
    button.dataset.label = original;
    try {
      await navigator.clipboard.writeText(buildSummary(result, paqui, ablation));
      button.textContent = "Copiado ✓";
    } catch (error) {
      button.textContent = "No se pudo copiar";
    }
    window.setTimeout(() => {
      button.textContent = original;
    }, 1800);
  };
}

function updateDesktopNote(downloadUrl) {
  elements.desktopNoteText.textContent = downloadUrl
    ? "También disponible como app nativa para macOS."
    : "La app nativa para macOS se publicará desde GitHub Releases cuando exista enlace público.";
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) {
      throw new Error(`http-${response.status}`);
    }
    return await response.json();
  } catch (error) {
    // Sin config la calculadora sigue funcionando con valores por defecto.
    return {
      procedure_choices: FALLBACK_PROCEDURES,
      default_procedure: "lasik",
      default_flap_cap_um: 120,
    };
  }
}

async function bootstrap() {
  state.config = await loadConfig();

  (state.config.procedure_choices || FALLBACK_PROCEDURES).forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    elements.procedureSelect.append(option);
  });
  (state.config.optical_zone_choices || FALLBACK_ZONES).forEach((zone) => {
    const option = document.createElement("option");
    option.value = String(zone);
    option.textContent = formatZone(zone);
    elements.zoneSelect.append(option);
  });
  elements.zoneSelect.value = String(state.config.default_optical_zone_mm || 6);
  elements.procedureSelect.value = state.config.default_procedure || "lasik";
  if (!elements.flapCapInput.value) {
    elements.flapCapInput.value = String(state.config.default_flap_cap_um || 120);
  }

  const repoUrl = state.config.github_repo_url || "";
  const downloadUrl = state.config.desktop_download_url || "";

  elements.repoLinks.forEach((link) => setLinkState(link, repoUrl));
  elements.downloadLinks.forEach((link) => setLinkState(link, downloadUrl));
  updateDesktopNote(downloadUrl);

  [elements.zoneSelect, elements.sphereInput].forEach((element) => {
    element.addEventListener("input", scheduleLaser);
    element.addEventListener("change", updateLaser);
  });

  [
    elements.procedureSelect,
    elements.flapCapInput,
    elements.paquiInput,
    elements.ablationInput,
    elements.suspiciousToggle,
  ].forEach((element) => {
    element.addEventListener("input", () => {
      updateConfigurationUI();
      scheduleCompute();
    });
    element.addEventListener("change", () => {
      updateConfigurationUI();
      computeNow();
    });
  });

  bindInfoModal();
  updateConfigurationUI();
  resetResults();
}

bootstrap();
