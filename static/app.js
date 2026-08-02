/**
 * Frontend JavaScript - Custom AI Chatbot with Memory
 * Author: Senior AI Architect (Decode Lab)
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const userInput = document.getElementById("userInput");
  const btnSend = document.getElementById("btnSend");
  const chatMessages = document.getElementById("chatMessages");
  const typingIndicator = document.getElementById("typingIndicator");
  const charCount = document.getElementById("charCount");
  
  // Dashboard Elements
  const providerName = document.getElementById("providerName");
  const sessionIdText = document.getElementById("sessionIdText");
  const memoryCountText = document.getElementById("memoryCountText");
  const memoryProgressBar = document.getElementById("memoryProgressBar");
  const droppedCount = document.getElementById("droppedCount");
  const turnCount = document.getElementById("turnCount");

  // Buttons
  const btnRunAudit = document.getElementById("btnRunAudit");
  const btnPersistDb = document.getElementById("btnPersistDb");
  const btnClearMemory = document.getElementById("btnClearMemory");
  
  // Alerts & Modals
  const alertBanner = document.getElementById("alertBanner");
  const alertMessage = document.getElementById("alertMessage");
  const btnCloseAlert = document.getElementById("btnCloseAlert");
  const auditModal = document.getElementById("auditModal");
  const auditModalBody = document.getElementById("auditModalBody");
  const btnCloseModal = document.getElementById("btnCloseModal");
  const btnCloseModalBtn = document.getElementById("btnCloseModalBtn");

  // Load Session Data on start
  fetchSessionState();

  // Input event listeners for live validation guard & char count
  userInput.addEventListener("input", () => {
    const rawVal = userInput.value;
    const trimmedVal = rawVal.trim();
    
    charCount.textContent = `${rawVal.length} chars`;
    btnSend.disabled = (trimmedVal.length === 0);
    
    // Auto-grow textarea
    userInput.style.height = "auto";
    userInput.style.height = `${Math.min(userInput.scrollHeight, 120)}px`;
  });

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!btnSend.disabled) {
        sendMessage();
      }
    }
  });

  btnSend.addEventListener("click", sendMessage);

  // Quick Prompt Chips
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("chip-prompt")) {
      const text = e.target.getAttribute("data-text");
      if (text) {
        userInput.value = text;
        userInput.dispatchEvent(new Event("input"));
        sendMessage();
      }
    }
  });

  // Action Buttons
  btnClearMemory.addEventListener("click", clearMemory);
  btnPersistDb.addEventListener("click", persistToDb);
  btnRunAudit.addEventListener("click", runSystemAudit);

  // Modals & Alerts
  if (btnCloseAlert) btnCloseAlert.addEventListener("click", hideAlert);
  if (btnCloseModal) btnCloseModal.addEventListener("click", hideModal);
  if (btnCloseModalBtn) btnCloseModalBtn.addEventListener("click", hideModal);

  // =========================================================================
  // API FUNCTIONS
  // =========================================================================

  async function fetchSessionState() {
    try {
      const res = await fetch("/api/session");
      const data = await res.json();

      if (data) {
        providerName.textContent = data.provider || "MOCK";
        sessionIdText.textContent = data.session_id ? `${data.session_id.substring(0, 13)}...` : "Active";
        updateMemoryDashboard(data.memory_summary, data.history);
        renderHistory(data.history);
      }
    } catch (err) {
      console.error("Failed to fetch session state:", err);
    }
  }

  async function sendMessage() {
    const text = userInput.value;
    const trimmed = text.trim();

    if (!trimmed) {
      showAlert("Structural Validation Gate: Input cannot be empty or whitespace-only.");
      return;
    }

    hideAlert();
    userInput.value = "";
    userInput.style.height = "auto";
    btnSend.disabled = true;

    // Append user message UI immediately
    appendMessageUI("user", trimmed);
    showTyping(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      const data = await res.json();
      showTyping(false);

      if (!res.ok) {
        // Validation Gate or Server error response
        showAlert(`[Validation Gate Intercepted]: ${data.error || "Invalid payload"}`);
        return;
      }

      // Append model response UI
      appendMessageUI("model", data.response, data.provider);
      updateMemoryDashboard(data.memory_summary, data.history);

    } catch (err) {
      showTyping(false);
      showAlert(`Network/Server Error: ${err.message}`);
    }
  }

  async function clearMemory() {
    try {
      const res = await fetch("/api/clear", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        chatMessages.innerHTML = `
          <div class="welcome-card">
            <div class="welcome-icon"><i class="fa-solid fa-broom"></i></div>
            <h3>Memory Cleared</h3>
            <p>In-memory conversation history has been reset.</p>
          </div>
        `;
        updateMemoryDashboard(data.memory_summary, []);
      }
    } catch (err) {
      showAlert("Failed to clear memory.");
    }
  }

  async function persistToDb() {
    try {
      const res = await fetch("/api/persist", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        alert(`[PASSED] Persisted ${data.persisted_message_count} messages into PostgreSQL JSONB (Session UUID: ${data.session_id})`);
      } else {
        showAlert("Failed to persist to database.");
      }
    } catch (err) {
      showAlert("Error persisting memory.");
    }
  }

  async function runSystemAudit() {
    showModal(true);
    auditModalBody.innerHTML = `
      <div class="audit-loading">
        <div class="spinner"></div>
        <p>Running System Audit ("Memory Exam")...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/audit", { method: "POST" });
      const data = await res.json();

      let html = `<div style="margin-bottom: 16px; font-size: 15px; font-weight: 700;">
        Status: ${data.all_passed ? '<span style="color: #10b981;">[PASSED ALL AUDITS]</span>' : '<span style="color: #ef4444;">[SOME AUDITS FAILED]</span>'}
      </div>`;

      data.audits.forEach(item => {
        html += `
          <div class="audit-item">
            <span><strong>Test ${item.id}:</strong> ${item.name}</span>
            <span class="audit-badge ${item.passed ? 'passed' : 'failed'}">
              ${item.passed ? 'PASSED' : 'FAILED'}
            </span>
          </div>
        `;
      });

      auditModalBody.innerHTML = html;
    } catch (err) {
      auditModalBody.innerHTML = `<p style="color: #ef4444;">Error running audit: ${err.message}</p>`;
    }
  }

  // =========================================================================
  // HELPER UI RENDERERS
  // =========================================================================

  function updateMemoryDashboard(summary, history) {
    if (!summary) return;

    const count = summary.current_message_count || (history ? history.length : 0);
    const max = summary.max_capacity || 10;
    const pct = Math.min(100, (count / max) * 100);

    memoryCountText.textContent = `${count} / ${max} Messages`;
    memoryProgressBar.style.width = `${pct}%`;
    droppedCount.textContent = summary.total_dropped_messages || 0;
    turnCount.textContent = Math.floor(count / 2);
  }

  function renderHistory(history) {
    if (!history || history.length === 0) return;

    // Clear welcome card if history exists
    chatMessages.innerHTML = "";
    history.forEach(msg => {
      appendMessageUI(msg.role, msg.content);
    });
  }

  function appendMessageUI(role, content, provider = "") {
    // Remove welcome card on first message
    const welcomeCard = chatMessages.querySelector(".welcome-card");
    if (welcomeCard) welcomeCard.remove();

    const isUser = (role === "user");
    const rowDiv = document.createElement("div");
    rowDiv.className = `message-row ${isUser ? 'user-row' : 'model-row'}`;

    const iconClass = isUser ? "fa-user" : "fa-robot";
    const metaText = isUser ? "You" : `AI (${provider || "Decode Lab"})`;

    rowDiv.innerHTML = `
      <div class="avatar"><i class="fa-solid ${iconClass}"></i></div>
      <div class="message-content">
        <div class="message-bubble">${escapeHtml(content)}</div>
        <div class="message-meta">${metaText}</div>
      </div>
    `;

    chatMessages.appendChild(rowDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function showTyping(show) {
    typingIndicator.style.display = show ? "flex" : "none";
    if (show) chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function showAlert(msg) {
    alertMessage.textContent = msg;
    alertBanner.style.display = "flex";
  }

  function hideAlert() {
    alertBanner.style.display = "none";
  }

  function showModal(show) {
    auditModal.style.display = show ? "flex" : "none";
  }

  function hideModal() {
    auditModal.style.display = "none";
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
});
