const tabButtons = document.querySelectorAll(".tab-btn");
const forms = document.querySelectorAll(".form");
const authMessage = document.getElementById("auth-message");

function activateTab(targetId) {
  tabButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.target === targetId);
  });
  forms.forEach((form) => {
    form.classList.toggle("active", form.id === targetId);
  });
}

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => activateTab(btn.dataset.target));
});

const existing = loadSession();
if (existing?.role === "student") {
  window.location.href = "/student";
}
if (existing?.role === "professor") {
  window.location.href = "/professor";
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(authMessage, "Signing in...", "");

  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const role = document.querySelector("input[name='login-role']:checked")?.value || "student";

  try {
    const user = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, role }),
    });
    saveSession(user);
    setMessage(authMessage, "Login successful.", "success");
    window.location.href = user.role === "professor" ? "/professor" : "/student";
  } catch (error) {
    setMessage(authMessage, `Login failed: ${error.message}`, "error");
  }
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(authMessage, "Creating account...", "");

  const email = document.getElementById("register-email").value.trim();
  const full_name = document.getElementById("register-name").value.trim();
  const student_id_number = document.getElementById("register-student-id").value.trim();
  const password = document.getElementById("register-password").value;
  const role = document.querySelector("input[name='register-role']:checked")?.value || "student";

  try {
    await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, full_name, student_id_number, password, role }),
    });
    setMessage(authMessage, "Registration successful. You can login now.", "success");
    activateTab("login-form");
  } catch (error) {
    setMessage(authMessage, `Registration failed: ${error.message}`, "error");
  }
});
