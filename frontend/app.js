const apiBase = "/api";
let authToken = null;
let currentUser = null;

function persistAuth() {
  if (authToken && currentUser) {
    localStorage.setItem("renovahub_token", authToken);
    localStorage.setItem("renovahub_user", JSON.stringify(currentUser));
  }
}

const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");
const projectForm = document.getElementById("project-form");
const homeownerDashboard = document.getElementById("homeowner-dashboard");
const contractorDashboard = document.getElementById("contractor-dashboard");
const homeownerProjectsList = document.getElementById("homeowner-projects");
const homeownerQuotesList = document.getElementById("homeowner-quotes");
const contractorProjectsList = document.getElementById("contractor-projects");
const contractorQuotesList = document.getElementById("contractor-quotes");
const homeownerSummary = document.getElementById("homeowner-summary");
const contractorSummary = document.getElementById("contractor-summary");

document.getElementById("year").textContent = new Date().getFullYear();

document.getElementById("cta-homeowner").addEventListener("click", () => {
  document.getElementById("homeowner-dashboard").scrollIntoView({ behavior: "smooth" });
});

document.getElementById("cta-contractor").addEventListener("click", () => {
  document.getElementById("contractor-dashboard").scrollIntoView({ behavior: "smooth" });
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(registerForm);
  const role = form.get("role");
  const payload = {
    email: form.get("email"),
    password: form.get("password"),
    profile: role === "homeowner"
      ? { full_name: form.get("name") }
      : { business_name: form.get("name"), specialties: [], service_areas: [] }
  };
  const endpoint = role === "homeowner"
    ? `${apiBase}/auth/homeowner/register`
    : `${apiBase}/auth/contractor/register`;
  const result = await request(endpoint, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  if (result?.token) {
    authToken = result.token;
    currentUser = { id: result.user_id, role, tier: result.tier };
    persistAuth();
    await loadDashboard(role);
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(loginForm);
  const response = await request(`${apiBase}/auth/login`, {
    method: "POST",
    body: JSON.stringify({
      email: form.get("email"),
      password: form.get("password")
    })
  });
  if (response?.token) {
    authToken = response.token;
    currentUser = { id: response.user_id, role: response.role, tier: response.tier };
    persistAuth();
    await loadDashboard(response.role);
  } else {
    alert(response?.error || "Unable to log in");
  }
});

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!authToken) {
    alert("Please log in as a homeowner");
    return;
  }
  const form = new FormData(projectForm);
  const payload = Object.fromEntries(form.entries());
  payload.budget_min = payload.budget_min ? Number(payload.budget_min) : null;
  payload.budget_max = payload.budget_max ? Number(payload.budget_max) : null;
  payload.photos = [];
  const result = await request(`${apiBase}/homeowner/projects`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  if (result?.id) {
    projectForm.reset();
    await loadHomeownerData();
  } else {
    alert(result?.error || "Failed to create project");
  }
});

async function request(url, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  const response = await fetch(url, { ...options, headers });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (data?.error) {
      alert(data.error);
    }
    return data;
  }
  return data;
}

async function loadDashboard(role) {
  document.getElementById("auth-section").hidden = true;
  if (role === "homeowner") {
    homeownerDashboard.hidden = false;
    contractorDashboard.hidden = true;
    await loadHomeownerData();
  } else {
    contractorDashboard.hidden = false;
    homeownerDashboard.hidden = true;
    await loadContractorData();
  }
}

async function loadHomeownerData() {
  const [summary, projects] = await Promise.all([
    request(`${apiBase}/homeowner/dashboard`),
    request(`${apiBase}/homeowner/projects`)
  ]);
  if (summary) {
    homeownerSummary.innerHTML = `
      <p><strong>Tier:</strong> ${summary.tier}</p>
      <p><strong>Open projects:</strong> ${summary.open_projects}</p>
      <p><strong>Completed projects:</strong> ${summary.completed_projects}</p>
      <p><strong>Quotes received:</strong> ${summary.quotes_received}</p>
    `;
  }
  renderProjects(homeownerProjectsList, projects?.projects || [], true);
}

async function loadContractorData() {
  const [summary, projectResponse, quotesResponse] = await Promise.all([
    request(`${apiBase}/contractor/dashboard`),
    request(`${apiBase}/contractor/projects`),
    request(`${apiBase}/contractor/quotes`)
  ]);
  if (summary) {
    contractorSummary.innerHTML = `
      <p><strong>Tier:</strong> ${summary.tier}</p>
      <p><strong>Quotes submitted:</strong> ${summary.submitted_quotes}</p>
      <p><strong>Quotes accepted:</strong> ${summary.accepted_quotes}</p>
      <p><strong>Reviews:</strong> ${summary.reviews}</p>
    `;
  }
  renderProjects(contractorProjectsList, projectResponse?.projects || [], false);
  renderContractorQuotes(quotesResponse?.quotes || []);
}

function renderProjects(target, projects, allowQuoteActions) {
  target.innerHTML = "";
  projects.forEach((project) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <h4>${project.title}</h4>
      <p>${project.description || "No description"}</p>
      <p><strong>Budget:</strong> ${formatCurrency(project.budget_min, project.budget_max)}</p>
      <p><strong>Status:</strong> ${project.status}</p>
      ${allowQuoteActions ? `<button data-project="${project.id}" class="view-quotes">View Quotes</button>` : `<button data-project="${project.id}" class="submit-quote">Submit Quote</button>`}
    `;
    target.appendChild(item);
  });
  if (allowQuoteActions) {
    target.querySelectorAll(".view-quotes").forEach((btn) =>
      btn.addEventListener("click", () => loadQuotesForProject(btn.dataset.project))
    );
  } else {
    target.querySelectorAll(".submit-quote").forEach((btn) =>
      btn.addEventListener("click", () => promptQuote(btn.dataset.project))
    );
  }
}

async function loadQuotesForProject(projectId) {
  const data = await request(`${apiBase}/homeowner/quotes?project_id=${projectId}`);
  homeownerQuotesList.innerHTML = "";
  (data?.quotes || []).forEach((quote) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <h4>${quote.business_name || "Contractor"}</h4>
      <p><strong>Amount:</strong> $${Number(quote.amount).toFixed(2)}</p>
      <p>${quote.cost_breakdown || "No breakdown provided"}</p>
      <div class="actions">
        <button data-quote="${quote.id}" class="accept">Accept</button>
        <button data-quote="${quote.id}" class="decline secondary">Decline</button>
      </div>
    `;
    homeownerQuotesList.appendChild(item);
  });
  homeownerQuotesList.querySelectorAll(".accept").forEach((btn) =>
    btn.addEventListener("click", () => respondToQuote(btn.dataset.quote, true))
  );
  homeownerQuotesList.querySelectorAll(".decline").forEach((btn) =>
    btn.addEventListener("click", () => respondToQuote(btn.dataset.quote, false))
  );
}

async function respondToQuote(quoteId, accept) {
  const endpoint = accept
    ? `${apiBase}/homeowner/quotes/accept`
    : `${apiBase}/homeowner/quotes/decline`;
  const result = await request(endpoint, {
    method: "POST",
    body: JSON.stringify({ quote_id: Number(quoteId) })
  });
  if (result?.id) {
    await loadHomeownerData();
    await loadQuotesForProject(result.project_id);
  }
}

function promptQuote(projectId) {
  const amount = prompt("Enter your quote amount (USD)");
  if (!amount) return;
  const details = prompt("Provide a short scope summary");
  request(`${apiBase}/contractor/quotes`, {
    method: "POST",
    body: JSON.stringify({
      project_id: Number(projectId),
      amount: Number(amount),
      cost_breakdown: details,
      timeline: "4-6 weeks"
    })
  }).then(() => loadContractorData());
}

function formatCurrency(min, max) {
  if (!min && !max) return "Not specified";
  if (min && max) return `$${Number(min).toFixed(0)} - $${Number(max).toFixed(0)}`;
  return `$${Number(min || max).toFixed(0)}`;
}

(async function bootstrap() {
  if (localStorage.getItem("renovahub_token")) {
    authToken = localStorage.getItem("renovahub_token");
    currentUser = JSON.parse(localStorage.getItem("renovahub_user"));
    await loadDashboard(currentUser.role);
  }
})();

window.addEventListener("beforeunload", () => {
  persistAuth();
});


function renderContractorQuotes(quotes) {
  contractorQuotesList.innerHTML = "";
  quotes.forEach((quote) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <h4>${quote.project_title || "Project"}</h4>
      <p><strong>Status:</strong> ${quote.status}</p>
      <p><strong>Amount:</strong> $${Number(quote.amount).toFixed(2)}</p>
      <p>${quote.cost_breakdown || "No details"}</p>
    `;
    contractorQuotesList.appendChild(item);
  });
}
