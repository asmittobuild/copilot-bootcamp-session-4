document.addEventListener("DOMContentLoaded", () => {
  const capabilitiesList = document.getElementById("capabilities-list");
  const capabilitySelect = document.getElementById("capability");
  const registerForm = document.getElementById("register-form");
  const messageDiv = document.getElementById("message");
  const registerHelp = document.getElementById("register-help");
  const emailInput = document.getElementById("email");

  const loginBtn = document.getElementById("login-btn");
  const logoutBtn = document.getElementById("logout-btn");
  const authUser = document.getElementById("auth-user");
  const loginModal = document.getElementById("login-modal");
  const loginForm = document.getElementById("login-form");
  const cancelLoginBtn = document.getElementById("cancel-login-btn");

  const authState = {
    token: localStorage.getItem("slalom_access_token"),
    user: null,
  };

  function getAuthHeaders() {
    if (!authState.token) {
      return {};
    }
    return { Authorization: `Bearer ${authState.token}` };
  }

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type || "info";
    messageDiv.classList.remove("hidden");
    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function clearCapabilityOptions() {
    capabilitySelect.innerHTML = '<option value="">-- Select a capability --</option>';
  }

  function openLoginModal() {
    loginModal.classList.remove("hidden");
    loginModal.setAttribute("aria-hidden", "false");
  }

  function closeLoginModal() {
    loginModal.classList.add("hidden");
    loginModal.setAttribute("aria-hidden", "true");
    loginForm.reset();
  }

  function updateRegisterFormMode() {
    const submitButton = registerForm.querySelector('button[type="submit"]');

    if (!authState.user) {
      emailInput.disabled = true;
      capabilitySelect.disabled = true;
      submitButton.disabled = true;
      submitButton.textContent = "Sign In To Continue";
      registerHelp.textContent = "Sign in as a practice lead or consultant to continue.";
      return;
    }

    capabilitySelect.disabled = false;
    submitButton.disabled = false;

    if (authState.user.role === "consultant") {
      emailInput.value = authState.user.email;
      emailInput.disabled = true;
      submitButton.textContent = "Request Registration";
      registerHelp.textContent = "Consultants submit requests that practice leads must approve.";
      return;
    }

    emailInput.disabled = false;
    submitButton.textContent = "Register Expertise";
    registerHelp.textContent = "Practice leads can directly register and approve consultant requests.";
  }

  function updateAuthUI() {
    if (authState.user) {
      authUser.textContent = `${authState.user.display_name} (${authState.user.role})`;
      authUser.classList.remove("hidden");
      loginBtn.classList.add("hidden");
      logoutBtn.classList.remove("hidden");
    } else {
      authUser.classList.add("hidden");
      loginBtn.classList.remove("hidden");
      logoutBtn.classList.add("hidden");
    }

    updateRegisterFormMode();
  }

  async function restoreSession() {
    if (!authState.token) {
      return;
    }

    try {
      const response = await fetch("/auth/me", {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Session token is no longer valid");
      }

      const payload = await response.json();
      authState.user = payload.user;
    } catch (error) {
      localStorage.removeItem("slalom_access_token");
      authState.token = null;
      authState.user = null;
    }
  }

  async function fetchCapabilities() {
    try {
      const response = await fetch("/capabilities", {
        headers: getAuthHeaders(),
      });
      const capabilities = await response.json();

      capabilitiesList.innerHTML = "";
      clearCapabilityOptions();

      const isPracticeLead = authState.user && authState.user.role === "practice_lead";

      Object.entries(capabilities).forEach(([name, details]) => {
        const capabilityCard = document.createElement("div");
        capabilityCard.className = "capability-card";

        const availableCapacity = details.capacity || 0;
        const currentConsultants = details.consultants ? details.consultants.length : 0;
        const pendingRequests = details.pending_requests || [];
        const pendingCount = details.pending_request_count || 0;

        const consultantsHTML =
          details.consultants && details.consultants.length > 0
            ? `<div class="consultants-section">
              <h5>Registered Consultants:</h5>
              <ul class="consultants-list">
                ${details.consultants
                  .map((email) => {
                    const actionButton = isPracticeLead
                      ? `<button class="delete-btn" data-capability="${name}" data-email="${email}" title="Remove consultant">Remove</button>`
                      : "";
                    return `<li><span class="consultant-email">${email}</span>${actionButton}</li>`;
                  })
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No consultants registered yet</em></p>`;

        const pendingHTML = isPracticeLead
          ? `<div class="pending-section">
              <h5>Pending Requests:</h5>
              ${pendingRequests.length > 0
                ? `<ul class="consultants-list">
                    ${pendingRequests
                      .map(
                        (email) => `<li><span class="consultant-email">${email}</span><button class="approve-btn" data-capability="${name}" data-email="${email}">Approve</button></li>`
                      )
                      .join("")}
                  </ul>`
                : '<p><em>No pending requests</em></p>'}
            </div>`
          : `<p><strong>Pending Requests:</strong> ${pendingCount}</p>`;

        capabilityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Practice Area:</strong> ${details.practice_area}</p>
          <p><strong>Industry Verticals:</strong> ${details.industry_verticals ? details.industry_verticals.join(", ") : "Not specified"}</p>
          <p><strong>Capacity:</strong> ${availableCapacity} hours/week available</p>
          <p><strong>Current Team:</strong> ${currentConsultants} consultants</p>
          ${pendingHTML}
          <div class="consultants-container">
            ${consultantsHTML}
          </div>
        `;

        capabilitiesList.appendChild(capabilityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        capabilitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
      document.querySelectorAll(".approve-btn").forEach((button) => {
        button.addEventListener("click", handleApprove);
      });
    } catch (error) {
      capabilitiesList.innerHTML = "<p>Failed to load capabilities. Please try again later.</p>";
      console.error("Error fetching capabilities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const capability = button.getAttribute("data-capability");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(capability)}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        fetchCapabilities();
      } else {
        showMessage(result.detail || "Could not unregister consultant.", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister consultant.", "error");
      console.error("Error unregistering:", error);
    }
  }

  async function handleApprove(event) {
    const button = event.target;
    const capability = button.getAttribute("data-capability");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(capability)}/approve?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        fetchCapabilities();
      } else {
        showMessage(result.detail || "Could not approve registration request.", "error");
      }
    } catch (error) {
      showMessage("Failed to approve request.", "error");
      console.error("Error approving request:", error);
    }
  }

  loginBtn.addEventListener("click", openLoginModal);
  cancelLoginBtn.addEventListener("click", closeLoginModal);

  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("slalom_access_token");
    authState.token = null;
    authState.user = null;
    updateAuthUI();
    fetchCapabilities();
    showMessage("Signed out successfully.", "info");
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const result = await response.json();

      if (!response.ok) {
        showMessage(result.detail || "Sign in failed.", "error");
        return;
      }

      authState.token = result.access_token;
      authState.user = result.user;
      localStorage.setItem("slalom_access_token", authState.token);

      closeLoginModal();
      updateAuthUI();
      fetchCapabilities();
      showMessage(`Welcome, ${result.user.display_name}!`, "success");
    } catch (error) {
      showMessage("Failed to sign in.", "error");
      console.error("Error logging in:", error);
    }
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!authState.user) {
      showMessage("Sign in first to continue.", "error");
      return;
    }

    const capability = capabilitySelect.value;
    const email = authState.user.role === "consultant" ? authState.user.email : emailInput.value;

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(capability)}/register?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        if (authState.user.role !== "consultant") {
          registerForm.reset();
        }
        fetchCapabilities();
      } else {
        showMessage(result.detail || "Could not register consultant.", "error");
      }
    } catch (error) {
      showMessage("Failed to register consultant.", "error");
      console.error("Error registering:", error);
    }
  });

  (async () => {
    await restoreSession();
    updateAuthUI();
    fetchCapabilities();
  })();
});
