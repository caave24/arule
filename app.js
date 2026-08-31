const fetchJSON = async (path) => {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.json();
};

const randomItem = (items) => items[Math.floor(Math.random() * items.length)];

function setGoogleFonts(fonts = []) {
  if (!fonts.length) return;
  const families = fonts
    .map((font) => `family=${encodeURIComponent(font).replace(/%20/g, "+")}:wght@400;500;600;700`)
    .join("&");
  document.querySelector("#google-fonts").href =
    `https://fonts.googleapis.com/css2?${families}&display=swap`;
}

function applyText(item) {
  document.querySelector("#quote").textContent = item.text || "";
  document.querySelector("#quote-source").textContent = item.source ? `— ${item.source}` : "";
}

function setRandomColor(colors) {
  document.documentElement.style.setProperty("--text-color", randomItem(colors));
}

function setTitle(config) {
  document.title = config.pageTitle || "A-RULE";
}

function setClockColor(config) {
  if (config.clockColor) {
    document.documentElement.style.setProperty("--clock-color", config.clockColor);
  }
}

function setupClock(config) {
  const timeElement = document.querySelector("#time");
  const dateElement = document.querySelector("#date");
  const timeZone = config.timeZone || "America/New_York";
  const locale = config.locale || "en-US";

  const updateClock = () => {
    const now = new Date();

    timeElement.textContent = new Intl.DateTimeFormat(locale, {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      second: config.showSeconds ? "2-digit" : undefined,
      hourCycle: "h23"
    }).format(now);

    dateElement.textContent = new Intl.DateTimeFormat(locale, {
      timeZone,
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric"
    }).format(now);
  };

  updateClock();
  setInterval(updateClock, 1000);
}

function setupClockControls() {
  document.querySelectorAll("[data-size]").forEach((button) => {
    button.addEventListener("click", () => {
      const size = button.dataset.size;
      document.documentElement.style.setProperty("--clock-size", `${size}px`);
      localStorage.setItem("a-rule-clock-size", size);
    });
  });

  const saved = localStorage.getItem("a-rule-clock-size");
  if (saved) {
    document.documentElement.style.setProperty("--clock-size", `${saved}px`);
  }
}

async function preload(url) {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(true);
    image.onerror = () => resolve(false);
    image.src = url;
  });
}

async function setupBackgrounds(config) {
  const base = document.querySelector(".bg-base");
  const next = document.querySelector(".bg-next");
  const images = config.images || [];

  if (!images.length) {
    console.warn("No background images configured.");
    return;
  }

  let current = -1;

  const chooseNext = () => {
    if (images.length === 1) return 0;
    let index;
    do {
      index = Math.floor(Math.random() * images.length);
    } while (index === current);
    return index;
  };

  const changeBackground = async (initial = false) => {
    const index = chooseNext();
    const url = images[index];

    if (!(await preload(url))) {
      console.warn(`Background failed to load: ${url}`);
      return;
    }

    if (initial) {
      base.style.backgroundImage = `url("${url}")`;
      current = index;
      return;
    }

    next.style.backgroundImage = `url("${url}")`;
    requestAnimationFrame(() => next.classList.add("visible"));

    const duration = Number(config.transitionDurationMs || 1800);
    window.setTimeout(() => {
      base.style.backgroundImage = `url("${url}")`;
      next.classList.remove("visible");
      current = index;
    }, duration);
  };

  document.documentElement.style.setProperty(
    "--transition-ms",
    `${Number(config.transitionDurationMs || 1800)}ms`
  );

  await changeBackground(true);

  const interval = Number(config.changeEveryMs || 45000);
  if (interval > 0) {
    setInterval(() => changeBackground(false), interval);
  }
}

async function init() {
  try {
    const [textConfig, bgConfig, timeConfig] = await Promise.all([
      fetchJSON("./configs/text.json"),
      fetchJSON("./configs/backgrounds.json"),
      fetchJSON("./configs/time.json")
    ]);

    setGoogleFonts(textConfig.googleFonts);
    setTitle(textConfig);
    setClockColor(timeConfig);
    setRandomColor(textConfig.colors || ["#ffffff"]);
    applyText(randomItem(textConfig.items || [{ text: "A-RULE" }]));

    setupClock(timeConfig);
    setupClockControls();
    setupBackgrounds(bgConfig);
  } catch (error) {
    console.error(error);
    document.querySelector("#quote").textContent = "A-RULE";
    document.querySelector("#quote-source").textContent =
      "Check the browser console and your config files.";
  }
}

init();
