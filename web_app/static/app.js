const DEBOUNCE_MS = 200;
const FALLBACK_PROCEDURES = [
  { value: "lasik", label: "LASIK" },
  { value: "prk", label: "PRK" },
];
const FLAP_UM = 120;

const FALLBACK_ZONES = [6, 6.5];

const state = {
  config: null,
  requestSeq: 0,
  abortController: null,
  debounceTimer: null,
};

const elements = {
  procedureSelect: document.querySelector("#procedure-select"),
  zoneSelect: document.querySelector("#optical-zone-select"),
  modeSelect: document.querySelector("#input-mode-select"),
  sphereInput: document.querySelector("#sphere-input"),
  cylinderInput: document.querySelector("#cylinder-input"),
  modeFields: document.querySelectorAll("[data-mode]"),
  laserText: document.querySelector("#laser-text"),
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
  lerFormula: document.querySelector("#ler-formula"),
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
  return elements.procedureSelect.value || "lasik";
}

function currentMode() {
  return elements.modeSelect.value === "direct" ? "direct" : "refraction";
}

function lerFormulaText(flap, ablation, ler) {
  const paqui = ler + flap + ablation;
  return flap > 0
    ? `LER = ${paqui} (paqui) − ${flap} (flap) − ${ablation} (ablación) = ${ler} µm`
    : `LER = ${paqui} (paqui) − ${ablation} (ablación) = ${ler} µm · PRK: sin flap`;
}

function segmentText(flap, ablation, residual) {
  const flapText = flap > 0 ? `Flap ${flap} µm · ` : "";
  return `${flapText}Ablación ${ablation} µm · Residual ${residual} µm`;
}

function updateConfigurationUI() {
  const mode = currentMode();
  elements.modeFields.forEach((field) => {
    field.classList.toggle("is-hidden", field.dataset.mode !== mode);
  });

  elements.settingsHint.textContent =
    currentProcedure() === "lasik"
      ? `LASIK: se resta el flap de ${FLAP_UM} µm del lecho residual.`
      : "PRK: no hay flap, no se resta nada.";
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

function updateSegments(flap, ablation, residual) {
  const total = flap + ablation + residual;
  elements.segmentFlap.hidden = flap <= 0;

  if (!total) {
    elements.segmentFlap.style.flex = "1";
    elements.segmentAblation.style.flex = "1";
    elements.segmentResidual.style.flex = "1";
    return;
  }

  elements.segmentFlap.style.flex = `${Math.max(1, flap)}`;
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
  elements.segmentLabels.textContent = segmentText(currentProcedure() === "lasik" ? FLAP_UM : 0, 0, 0);
  elements.lerFormula.textContent = "LER = paquimetría − flap (120 µm en LASIK) − ablación";
  updateSegments(0, 0, 0);
  elements.laserText.textContent = "";

  setRule(elements.rules.ablation, "neutral", "–", "");
  setRule(elements.rules.lerUm, "neutral", "–", "");
  setRule(elements.rules.lerPct, "neutral", "–", "");
  setRule(elements.rules.postop, "neutral", "–", "");
}

function buildSummary(result, paqui) {
  const statusLabel =
    result.overall_status === "ok"
      ? "Cumple"
      : result.overall_status === "warning"
        ? "Cerca"
        : "No cumple";

  const laser = result.laser
    ? `graduación ${describeRefraction(result.laser)}, ZO ${formatZone(result.laser.optical_zone_mm)} mm (Teneo${result.laser.interpolated ? ", interpolado" : ""}), `
    : "";
  const flap = result.subtract_um > 0 ? `flap ${result.subtract_um} µm, ` : "sin flap, ";

  return `${result.procedure_label}, ${laser}paqui preop ${paqui} µm, ablación ${result.ablation_um} µm (${result.ablation_pct.toFixed(1)}%), LER ${result.ler_um} µm (${result.ler_pct.toFixed(1)}%), post-op ${result.postop_paqui_um} µm, ${flap}estado ${statusLabel}, limita ${result.limit_factor}, máx segura ${result.ablation_max_safe_um} µm, margen ${result.margin_um >= 0 ? "+" : ""}${result.margin_um} µm.`;
}

function formatD(value) {
  const text = Number(value).toLocaleString("es-ES", { signDisplay: "exceptZero", maximumFractionDigits: 2 });
  return text.replace("-", "−");
}

function formatZone(value) {
  return Number(value).toLocaleString("es-ES", { maximumFractionDigits: 1 });
}

function describeRefraction(laser) {
  if (!laser.cylinder_d) {
    return `${formatD(laser.sphere_d)} D`;
  }
  return `${formatD(laser.sphere_d)} / ${formatD(laser.cylinder_d)} (esfera equivalente ${formatD(laser.equivalent_d)} D)`;
}

function laserSummary(laser) {
  if (!laser || !laser.found) {
    return "";
  }
  const details = laser.interpolated
    ? "interpolado entre dos filas de la tabla"
    : `zona ${laser.zone_mm.replaceAll(".", ",")} mm · ${laser.time_s} s`;
  return `Teneo · ZO ${formatZone(laser.optical_zone_mm)} mm · ${describeRefraction(laser)} → ablación ${laser.ablation_um} µm (${details}).`;
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
    suspicious: elements.suspiciousToggle.checked,
    procedure: currentProcedure(),
  };

  if (currentMode() === "refraction") {
    const sphere = Number.parseFloat(elements.sphereInput.value);
    if (Number.isNaN(sphere)) {
      showFailure("Introduce la esfera.");
      return;
    }
    payload.sphere_d = sphere;
    payload.cylinder_d = Number.parseFloat(elements.cylinderInput.value) || 0;
    payload.optical_zone_mm = Number.parseFloat(elements.zoneSelect.value);
  } else {
    const ablation = Number.parseInt(elements.ablationInput.value || "", 10);
    if (Number.isNaN(ablation)) {
      showFailure("Introduce la ablación.");
      return;
    }
    payload.ablation_um = ablation;
  }

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
  elements.laserText.textContent = laserSummary(result.laser);
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
  elements.segmentLabels.textContent = segmentText(result.subtract_um, result.ablation_um, result.ler_um);
  elements.lerFormula.textContent = lerFormulaText(result.subtract_um, result.ablation_um, result.ler_um);
  updateSegments(result.subtract_um, result.ablation_um, result.ler_um);

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
      await navigator.clipboard.writeText(buildSummary(result, paqui));
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

  const repoUrl = state.config.github_repo_url || "";
  const downloadUrl = state.config.desktop_download_url || "";

  elements.repoLinks.forEach((link) => setLinkState(link, repoUrl));
  elements.downloadLinks.forEach((link) => setLinkState(link, downloadUrl));
  updateDesktopNote(downloadUrl);

  [
    elements.procedureSelect,
    elements.modeSelect,
    elements.zoneSelect,
    elements.sphereInput,
    elements.cylinderInput,
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
