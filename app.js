const state = {
  payload: null,
  deferredPrompt: null,
};

const $ = (selector) => document.querySelector(selector);
const list = $("#cardList");
const status = $("#status");
const template = $("#cardTemplate");
const windowSelect = $("#windowSelect");
const sortSelect = $("#sortSelect");
const printingSelect = $("#printingSelect");
const searchInput = $("#searchInput");

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

function signedMoney(value) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${money.format(value)}`;
}

function signedPercent(value) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function findPastSnapshot(history, days) {
  if (!history?.length) return null;
  const latest = new Date(history.at(-1).date);
  const target = new Date(latest);
  target.setUTCDate(target.getUTCDate() - days);

  let best = null;
  for (const point of history) {
    const pointDate = new Date(point.date);
    if (pointDate <= target) best = point;
  }
  return best ?? history[0];
}

function calculateRows() {
  const days = Number(windowSelect.value);
  const selectedPrinting = printingSelect.value;
  const query = searchInput.value.trim().toLowerCase();

  return state.payload.cards
    .map((card) => {
      const current = card.history?.at(-1);
      const previous = findPastSnapshot(card.history, days);
      if (!current || !previous || !Number.isFinite(current.price) || !Number.isFinite(previous.price)) return null;
      const dollarChange = current.price - previous.price;
      const percentChange = previous.price > 0 ? (dollarChange / previous.price) * 100 : 0;
      const elapsedMs = new Date(current.date) - new Date(previous.date);
      return {
        ...card,
        current,
        previous,
        dollarChange,
        percentChange,
        actualDays: Math.max(0, Math.round(elapsedMs / 86400000)),
      };
    })
    .filter(Boolean)
    .filter((card) => selectedPrinting === "all" || card.printing === selectedPrinting)
    .filter((card) => !query || `${card.name} ${card.set} ${card.number ?? ""}`.toLowerCase().includes(query));
}

function sortRows(rows) {
  const mode = sortSelect.value;
  const sorters = {
    "percent-desc": (a, b) => b.percentChange - a.percentChange,
    "dollar-desc": (a, b) => b.dollarChange - a.dollarChange,
    "percent-asc": (a, b) => a.percentChange - b.percentChange,
    "dollar-asc": (a, b) => a.dollarChange - b.dollarChange,
    "price-desc": (a, b) => b.current.price - a.current.price,
  };
  return rows.sort(sorters[mode]);
}

function render() {
  if (!state.payload) return;
  const rows = sortRows(calculateRows());

  list.replaceChildren();
  status.hidden = rows.length > 0;
  status.textContent = rows.length ? "" : "No cards match those filters.";

  $("#cardCount").textContent = rows.length.toLocaleString();
  $("#updatedAt").textContent = new Date(state.payload.updatedAt).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  $("#actualWindow").textContent = rows.length ? `${Math.max(...rows.map((r) => r.actualDays))} days` : "–";

  const fragment = document.createDocumentFragment();

  for (const card of rows) {
    const node = template.content.cloneNode(true);
    const link = node.querySelector(".card-link");
    link.href = card.tcgplayerUrl || `https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/product?q=${encodeURIComponent(card.name)}`;

    const image = node.querySelector(".card-image");
    if (card.imageUrl) {
      image.src = card.imageUrl;
      image.alt = `${card.name} card`;
      image.addEventListener("error", () => image.remove());
    } else {
      image.remove();
    }

    node.querySelector(".card-name").textContent = card.name;
    node.querySelector(".card-meta").textContent = [card.set, card.number, card.printing].filter(Boolean).join(" · ");
    node.querySelector(".old-price").textContent = money.format(card.previous.price);
    node.querySelector(".new-price").textContent = money.format(card.current.price);

    const direction = card.percentChange >= 0 ? "positive" : "negative";
    const pill = node.querySelector(".change-pill");
    pill.textContent = signedPercent(card.percentChange);
    pill.classList.add(direction);

    const dollar = node.querySelector(".dollar-change");
    dollar.textContent = signedMoney(card.dollarChange);
    dollar.classList.add(direction);

    fragment.appendChild(node);
  }

  list.appendChild(fragment);
}

async function load() {
  try {
    const response = await fetch(`./data/movers.json?ts=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.payload = await response.json();

    const printings = [...new Set(state.payload.cards.map((card) => card.printing).filter(Boolean))].sort();
    for (const printing of printings) {
      const option = document.createElement("option");
      option.value = printing;
      option.textContent = printing;
      printingSelect.appendChild(option);
    }

    render();
  } catch (error) {
    status.hidden = false;
    status.textContent = "Could not load market data. Run the updater or check the deployment.";
    console.error(error);
  }
}

for (const element of [windowSelect, sortSelect, printingSelect, searchInput]) {
  element.addEventListener("input", render);
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  state.deferredPrompt = event;
  $("#installButton").hidden = false;
});

$("#installButton").addEventListener("click", async () => {
  if (!state.deferredPrompt) return;
  state.deferredPrompt.prompt();
  await state.deferredPrompt.userChoice;
  state.deferredPrompt = null;
  $("#installButton").hidden = true;
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js"));
}

load();
