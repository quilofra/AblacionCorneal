const state = {
  config: null,
};

const elements = {
  procedureSelect: document.querySelector("#procedure-select"),
  legacyToggle: document.querySelector("#legacy-toggle"),
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
  downloadLinks: [
    document.querySelector("#download-link"),
    document.querySelector("#download-link-secondary"),
  ],
  repoLinks: [
    document.querySelector("#repo-link"),
    document.querySelector("#repo-link-secondary"),
  ],
  downloadHelp: document.querySelector("#download-help"),
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
  const isLegacy = elements.legacyToggle.checked;
  const label = tissueLabel(procedure);
  const needsFlapCap = procedure !== "surface" && !isLegacy;

  elements.flapCapLabel.textContent = `Espesor ${label.toLowerCase()} (µm)`;
  elements.flapCapInput.placeholder = procedure === "lasik" ? "110" : "120";
  elements.flapCapField.classList.toggle("is-hidden", !needsFlapCap);

  if (isLegacy) {
    elements.settingsHint.textContent =
      "Modo legacy activo: la web replica el cálculo histórico e ignora flap/cap.";
  } else if (procedure !== "surface") {
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

  return `${result.procedure_label}, paqui preop ${paqui} µm, ablación ${ablation} µm (${result.ablation_pct.toFixed(1)}%), LER ${result.ler_um} µm (${result.ler_pct.toFixed(1)}%), post-op ${result.postop_paqui_um} µm, ${result.tissue_label.toLowerCase()} efectivo ${result.subtract_um} µm, legacy ${result.legacy_mode ? "sí" : "no"}, estado ${statusLabel}, limita ${result.limit_factor}, máx segura ${result.ablation_max_safe_um} µm, margen ${result.margin_um >= 0 ? "+" : ""}${result.margin_um} µm.`;
}

async function compute() {
  const paqui = Number.parseInt(elements.paquiInput.value || "", 10);
  const ablation = Number.parseInt(elements.ablationInput.value || "", 10) || 0;
  const flapCap = Number.parseInt(elements.flapCapInput.value || "", 10) || 0;

  if (Number.isNaN(paqui)) {
    elements.errorText.textContent = "Introduce paquimetría preop.";
    elements.hintText.textContent = "";
    resetResults();
    return;
  }

  const payload = {
    paqui_preop_um: paqui,
    ablation_um: ablation,
    suspicious: elements.suspiciousToggle.checked,
    procedure: currentProcedure(),
    flap_cap_um: flapCap,
    legacy_mode: elements.legacyToggle.checked,
  };

  const response = await fetch("/api/compute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

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
    await navigator.clipboard.writeText(buildSummary(result, paqui, ablation));
  };
}

async function bootstrap() {
  const configResponse = await fetch("/api/config");
  state.config = await configResponse.json();

  state.config.procedure_choices.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    elements.procedureSelect.append(option);
  });

  const repoUrl = state.config.github_repo_url || "";
  const downloadUrl = state.config.desktop_download_url || "";

  elements.repoLinks.forEach((link) => setLinkState(link, repoUrl));
  elements.downloadLinks.forEach((link) => setLinkState(link, downloadUrl));
  elements.downloadHelp.textContent = downloadUrl
    ? "La descarga apunta a la release pública configurada para la app de escritorio."
    : "Define DESKTOP_DOWNLOAD_URL o GITHUB_REPO_URL para activar la descarga pública de la app.";

  [
    elements.procedureSelect,
    elements.legacyToggle,
    elements.flapCapInput,
    elements.paquiInput,
    elements.ablationInput,
    elements.suspiciousToggle,
  ].forEach((element) => {
    element.addEventListener("input", () => {
      updateConfigurationUI();
      compute();
    });
    element.addEventListener("change", () => {
      updateConfigurationUI();
      compute();
    });
  });

  updateConfigurationUI();
  resetResults();
}

bootstrap();
