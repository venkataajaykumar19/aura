/**
 * AURA — Client Application (Phase 10: Reminders & Daily Briefing)
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements - Header & Hero
  const statusDot = document.getElementById("statusDot");
  const statusLabel = document.getElementById("statusLabel");
  const liveClock = document.getElementById("liveClock");
  const voiceState = document.getElementById("voiceState");
  const heroMicBtn = document.getElementById("heroMicBtn");
  const barMicBtn = document.getElementById("barMicBtn");
  const voiceToggleBtn = document.getElementById("voiceToggleBtn");
  const liveTranscript = document.getElementById("liveTranscript");
  const lastReply = document.getElementById("lastReply");
  const chatTranscript = document.getElementById("chatTranscript");
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");

  // Elements - Briefing Panel
  const briefingDate = document.getElementById("briefingDate");
  const briefingCalendarText = document.getElementById("briefingCalendarText");
  const briefingGmailText = document.getElementById("briefingGmailText");
  const briefingApprovalsText = document.getElementById("briefingApprovalsText");
  const briefingRemindersText = document.getElementById("briefingRemindersText");

  // Elements - Reminders Panel
  const remindersInbox = document.getElementById("remindersList");
  const remindersCount = document.getElementById("remindersCount");
  const reminderForm = document.getElementById("reminderForm");
  const reminderTitle = document.getElementById("reminderTitle");
  const reminderDate = document.getElementById("reminderDate");
  const reminderTime = document.getElementById("reminderTime");
  const reminderStatusNotice = document.getElementById("reminderStatusNotice");

  // Elements - Approvals & Memory
  const approvalsInbox = document.getElementById("approvalsInbox");
  const approvalsCount = document.getElementById("approvalsCount");
  const memoryForm = document.getElementById("memoryForm");
  const prefName = document.getElementById("prefName");
  const prefLang = document.getElementById("prefLang");
  const prefStatusText = document.getElementById("prefStatusText");
  const factsList = document.getElementById("factsList");
  const factsCount = document.getElementById("factsCount");

  // Elements - Expenses
  const expenseForm = document.getElementById("expenseForm");
  const expenseAmount = document.getElementById("expenseAmount");
  const expenseCategory = document.getElementById("expenseCategory");
  const expenseNote = document.getElementById("expenseNote");
  const expensesMonthTotal = document.getElementById("expensesMonthTotal");
  const expensesList = document.getElementById("expensesList");

  // Elements - Notes
  const notesSearchInput = document.getElementById("notesSearchInput");
  const noteForm = document.getElementById("noteForm");
  const noteTitle = document.getElementById("noteTitle");
  const noteContent = document.getElementById("noteContent");
  const noteStatusNotice = document.getElementById("noteStatusNotice");
  const notesList = document.getElementById("notesList");
  const notesCount = document.getElementById("notesCount");

  // Elements - Auth
  const logoutBtn = document.getElementById("logoutBtn");
  const logoutDivider = document.getElementById("logoutDivider");

  async function checkAuthStatus() {
    try {
      const res = await fetch("/api/auth/status");
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/login";
        }
        return;
      }
      const data = await res.json();
      if (data.auth_enabled && data.logged_in) {
        if (logoutBtn) logoutBtn.style.display = "inline-block";
        if (logoutDivider) logoutDivider.style.display = "inline-block";
      } else {
        if (logoutBtn) logoutBtn.style.display = "none";
        if (logoutDivider) logoutDivider.style.display = "none";
      }
    } catch {}
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await fetch("/api/logout", { method: "POST" });
      } catch {}
      window.location.href = "/login";
    });
  }

  checkAuthStatus();
  const langSelector = document.getElementById("langSelector");
  let currentLanguage = "en-IN";

  const LANGUAGE_TEXTS = {
    "en-IN": {
      ready: "Ready",
      listening: "Listening…",
      speaking: "Speaking…",
      thinking: "Thinking…",
      placeholder: "Ask AURA or give an instruction…"
    },
    "kn-IN": {
      ready: "ಸಿದ್ಧವಾಗಿದೆ",
      listening: "ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದೆ…",
      speaking: "ಮಾತನಾಡುತ್ತಿದೆ…",
      thinking: "ಯೋಚಿಸುತ್ತಿದೆ…",
      placeholder: "AURA ಗೆ ಕೇಳಿ ಅಥವಾ ಸೂಚನೆ ನೀಡಿ…"
    },
    "hi-IN": {
      ready: "तैयार है",
      listening: "सुन रहा हूँ…",
      speaking: "बोल रहा हूँ…",
      thinking: "सोच रहा हूँ…",
      placeholder: "AURA से पूछें या कोई निर्देश दें…"
    },
    "te-IN": {
      ready: "సిద్ధంగా ఉంది",
      listening: "వింటోంది…",
      speaking: "మాట్లాడుతోంది…",
      thinking: "ఆలోచిస్తోంది…",
      placeholder: "AURA ను అడగండి లేదా సూచన ఇవ్వండి…"
    }
  };

  function updateLanguageUI(langCode) {
    if (!langCode) return;
    currentLanguage = langCode;
    const texts = LANGUAGE_TEXTS[langCode] || LANGUAGE_TEXTS["en-IN"];

    if (langSelector) langSelector.value = langCode;
    if (messageInput) messageInput.placeholder = texts.placeholder;
    if (voiceState && !isListening && voiceState.textContent !== "Speaking…") {
      voiceState.textContent = texts.ready;
    }
    if (heroMicBtn) {
      heroMicBtn.title = `Click to speak (${langCode})`;
    }
    if (recognition) {
      recognition.lang = langCode;
    }
  }

  if (langSelector) {
    langSelector.addEventListener("change", async (e) => {
      const selected = e.target.value;
      updateLanguageUI(selected);
      try {
        await fetch("/api/memory", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: "preferred_language", value: selected })
        });
      } catch (err) {
        console.warn("Failed to persist preferred_language:", err);
      }
    });
  }

  // Elements - Gmail Panel
  const gmailStatusText = document.getElementById("gmailStatusText");
  const gmailConnectBtn = document.getElementById("gmailConnectBtn");
  const gmailSummariseBtn = document.getElementById("gmailSummariseBtn");
  const emailSummaryBox = document.getElementById("emailSummaryBox");
  const gmailInbox = document.getElementById("gmailInbox");

  // Elements - Email Drafts
  const draftEditorWrap = document.getElementById("draftEditorWrap");
  const closeDraftEditorBtn = document.getElementById("closeDraftEditorBtn");
  const draftForm = document.getElementById("draftForm");
  const draftSourceEmailId = document.getElementById("draftSourceEmailId");
  const draftIdInput = document.getElementById("draftId");
  const draftInstruction = document.getElementById("draftInstruction");
  const generateDraftBtn = document.getElementById("generateDraftBtn");
  const draftTo = document.getElementById("draftTo");
  const draftSubject = document.getElementById("draftSubject");
  const draftBody = document.getElementById("draftBody");
  const saveDraftBtn = document.getElementById("saveDraftBtn");
  const sendForApprovalBtn = document.getElementById("sendForApprovalBtn");
  const draftStatusNotice = document.getElementById("draftStatusNotice");
  const draftsList = document.getElementById("draftsList");
  const draftsCount = document.getElementById("draftsCount");

  // Elements - Calendar Panel
  const calendarStatusText = document.getElementById("calendarStatusText");
  const calendarEventsList = document.getElementById("calendarEventsList");
  const calendarForm = document.getElementById("calendarForm");
  const eventTitle = document.getElementById("eventTitle");
  const eventDate = document.getElementById("eventDate");
  const eventTime = document.getElementById("eventTime");
  const calendarStatusNotice = document.getElementById("calendarStatusNotice");

  // In-memory conversation history: [{role: 'user'|'model', content: '...'}]
  const conversationHistory = [];
  const notifiedReminderIds = new Set();

  // Voice Settings & State
  let voiceReplyEnabled = true;
  let isListening = false;
  let recognition = null;
  let speechTextRecognized = "";

  // -------------------------------------------------------------------------
  // Live Clock & Real Timestamps
  // -------------------------------------------------------------------------
  function formatTimestamp(date = new Date()) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function updateClock() {
    if (liveClock) {
      liveClock.textContent = formatTimestamp();
    }
  }
  updateClock();
  setInterval(updateClock, 1000);

  // Set default today's date in forms
  const todayStr = new Date().toISOString().split("T")[0];
  if (eventDate) eventDate.value = todayStr;
  if (reminderDate) reminderDate.value = todayStr;

  // -------------------------------------------------------------------------
  // Brain Status Check
  // -------------------------------------------------------------------------
  async function checkBrainStatus() {
    try {
      const res = await fetch("/api/brain/status");
      if (res.ok) {
        const data = await res.json();
        if (data.configured) {
          statusDot.className = "status-dot active";
          statusLabel.textContent = "Brain ready";
        } else {
          statusDot.className = "status-dot error";
          statusLabel.textContent = "Brain unconfigured";
        }
      } else {
        statusDot.className = "status-dot error";
        statusLabel.textContent = "Brain offline";
      }
    } catch {
      statusDot.className = "status-dot error";
      statusLabel.textContent = "Brain offline";
    }
  }
  checkBrainStatus();

  // -------------------------------------------------------------------------
  // Daily Briefing
  // -------------------------------------------------------------------------
  async function loadBriefing() {
    try {
      const res = await fetch("/api/briefing");
      if (!res.ok) return;
      const data = await res.json();

      if (briefingDate) briefingDate.textContent = data.date || "Today";

      // Calendar line
      if (briefingCalendarText) {
        if (!data.calendar || !data.calendar.connected) {
          briefingCalendarText.textContent = "Calendar: not connected";
        } else {
          const events = data.calendar.events || [];
          if (events.length === 0) {
            briefingCalendarText.textContent = "Calendar: 0 events today";
          } else {
            const nextEv = events[0];
            const startT = nextEv.start_time ? formatIsoTime(nextEv.start_time) : "";
            briefingCalendarText.textContent = `Event: ${nextEv.title}${startT ? " (" + startT + ")" : ""}`;
          }
        }
      }

      // Gmail line
      if (briefingGmailText) {
        if (!data.gmail || !data.gmail.connected) {
          briefingGmailText.textContent = "Gmail: not connected";
        } else {
          const count = data.gmail.count || 0;
          briefingGmailText.textContent = `Inbox: ${count} new`;
        }
      }

      // Approvals line
      if (briefingApprovalsText) {
        const count = data.pending_approvals_count || 0;
        briefingApprovalsText.textContent = `Approvals: ${count}`;
      }

      // Reminders line
      if (briefingRemindersText) {
        const dueCount = data.due_reminders_count || 0;
        briefingRemindersText.textContent = `Reminders: ${dueCount} due`;
      }

      // Expenses month total
      if (expensesMonthTotal && typeof data.expenses_month_total === "number") {
        expensesMonthTotal.textContent = data.expenses_month_total.toLocaleString("en-IN", { maximumFractionDigits: 2 });
      }

    } catch (err) {
      console.warn("Failed to load briefing:", err);
    }
  }
  loadBriefing();

  // -------------------------------------------------------------------------
  // Reminders Management
  // -------------------------------------------------------------------------
  async function loadReminders() {
    try {
      const res = await fetch("/api/reminders");
      if (!res.ok) return;
      const reminders = await res.json();
      renderReminders(reminders);
    } catch (err) {
      console.warn("Failed to fetch reminders:", err);
    }
  }

  function renderReminders(reminders) {
    if (!remindersInbox) return;
    remindersInbox.innerHTML = "";

    const activePending = reminders.filter(r => r.status === "pending");
    if (remindersCount) remindersCount.textContent = activePending.length;

    if (!reminders || reminders.length === 0) {
      remindersInbox.innerHTML = `<div class="empty-notice">No reminders.</div>`;
      return;
    }

    const nowMs = Date.now();

    reminders.forEach((r) => {
      let isDue = false;
      try {
        const remindMs = new Date(r.remind_at).getTime();
        isDue = r.status === "pending" && !isNaN(remindMs) && remindMs <= nowMs;
      } catch {
        isDue = r.status === "pending" && r.remind_at <= new Date().toISOString();
      }
      const isDone = r.status === "done";

      const item = document.createElement("div");
      item.className = `reminder-item ${isDue ? "due" : ""} ${isDone ? "done" : ""}`;
      item.id = `reminder-item-${r.id}`;

      const details = document.createElement("div");
      details.className = "reminder-details";

      const meta = document.createElement("div");
      meta.className = "reminder-meta";

      const timeSpan = document.createElement("span");
      timeSpan.textContent = r.remind_at ? formatIsoDateTime(r.remind_at) : "";

      const statusTag = document.createElement("span");
      statusTag.textContent = isDone ? "DONE" : (isDue ? "DUE" : "PENDING");
      if (isDue) statusTag.className = "approval-tag";

      meta.appendChild(statusTag);
      meta.appendChild(timeSpan);

      const titleDiv = document.createElement("div");
      titleDiv.className = "reminder-title";
      titleDiv.textContent = r.title;

      details.appendChild(meta);
      details.appendChild(titleDiv);

      const actionsDiv = document.createElement("div");
      actionsDiv.className = "approval-actions";

      if (!isDone) {
        const doneBtn = document.createElement("button");
        doneBtn.type = "button";
        doneBtn.className = "btn-done";
        doneBtn.textContent = "Done";
        doneBtn.onclick = () => handleMarkReminderDone(r.id);
        actionsDiv.appendChild(doneBtn);
      }

      item.appendChild(details);
      item.appendChild(actionsDiv);
      remindersInbox.appendChild(item);
    });
  }

  async function handleMarkReminderDone(remId) {
    try {
      const res = await fetch(`/api/reminders/${remId}/done`, { method: "POST" });
      if (res.ok) {
        await loadReminders();
        loadBriefing();
      } else {
        const errData = await res.json();
        alert(errData.error || "Failed to mark reminder done.");
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  if (reminderForm) {
    reminderForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = reminderTitle ? reminderTitle.value.trim() : "";
      const date = reminderDate ? reminderDate.value.trim() : "";
      const time = reminderTime ? reminderTime.value.trim() : "";

      if (!title || !date || !time) return;

      const remindAt = `${date}T${time}:00`;

      try {
        const res = await fetch("/api/reminders", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, remind_at: remindAt })
        });

        if (res.ok) {
          if (reminderStatusNotice) {
            reminderStatusNotice.textContent = "Reminder added";
            setTimeout(() => { reminderStatusNotice.textContent = ""; }, 2500);
          }
          if (reminderTitle) reminderTitle.value = "";
          await loadReminders();
          loadBriefing();
        } else {
          const errData = await res.json();
          alert(errData.error || "Failed to add reminder.");
        }
      } catch (err) {
        alert(`Error: ${err.message}`);
      }
    });
  }

  // Periodic check for due reminders (every 60 seconds)
  async function checkDueReminders() {
    try {
      const res = await fetch("/api/reminders/due");
      if (!res.ok) return;
      const dueList = await res.json();

      if (Array.isArray(dueList)) {
        dueList.forEach((r) => {
          if (!notifiedReminderIds.has(r.id)) {
            notifiedReminderIds.add(r.id);
            // Render notice in the transcript area (no browser alert popups)
            appendReminderNotice(r.title);
          }
        });
      }
    } catch (err) {
      console.warn("Failed to check due reminders:", err);
    }
  }

  function appendReminderNotice(title) {
    const el = document.createElement("div");
    el.className = "chat-message reminder-notice";

    const content = document.createElement("div");
    content.className = "message-text";
    content.textContent = `Reminder: ${title}`;

    el.appendChild(content);
    chatTranscript.appendChild(el);
    scrollToBottom();
  }

  // Initial load and periodic timer
  loadReminders();
  checkDueReminders();
  setInterval(() => {
    checkDueReminders();
    loadReminders();
  }, 60000);

  // -------------------------------------------------------------------------
  // Approvals Management
  // -------------------------------------------------------------------------
  async function loadApprovals() {
    try {
      const res = await fetch("/api/approvals");
      if (!res.ok) return;
      const actions = await res.json();
      renderApprovals(actions);
    } catch (err) {
      console.warn("Failed to fetch approvals:", err);
    }
  }

  function renderApprovals(actions) {
    if (!approvalsInbox) return;
    approvalsInbox.innerHTML = "";

    const count = Array.isArray(actions) ? actions.length : 0;
    if (approvalsCount) approvalsCount.textContent = count;

    if (count === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "empty-notice";
      emptyDiv.textContent = "No pending approvals.";
      approvalsInbox.appendChild(emptyDiv);
      return;
    }

    actions.forEach((act) => {
      const item = document.createElement("div");
      item.className = "approval-item";
      item.id = `approval-item-${act.id}`;

      const details = document.createElement("div");
      details.className = "approval-details";

      const meta = document.createElement("div");
      meta.className = "approval-meta";

      const tag = document.createElement("span");
      tag.className = "approval-tag";
      tag.textContent = act.action_type || "ACTION";

      const timeSpan = document.createElement("span");
      timeSpan.textContent = act.created_at ? formatIsoTime(act.created_at) : "";

      meta.appendChild(tag);
      meta.appendChild(timeSpan);

      const summary = document.createElement("div");
      summary.className = "approval-summary";
      summary.textContent = act.summary;

      details.appendChild(meta);
      details.appendChild(summary);

      const actionsDiv = document.createElement("div");
      actionsDiv.className = "approval-actions";

      const approveBtn = document.createElement("button");
      approveBtn.type = "button";
      approveBtn.className = "btn-approve";
      approveBtn.textContent = "Approve";
      approveBtn.onclick = () => handleApprove(act.id);

      const rejectBtn = document.createElement("button");
      rejectBtn.type = "button";
      rejectBtn.className = "btn-reject";
      rejectBtn.textContent = "Reject";
      rejectBtn.onclick = () => handleReject(act.id);

      actionsDiv.appendChild(approveBtn);
      actionsDiv.appendChild(rejectBtn);

      item.appendChild(details);
      item.appendChild(actionsDiv);

      approvalsInbox.appendChild(item);
    });
  }

  function formatIsoTime(isoStr) {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    } catch {
      return "";
    }
  }

  function formatIsoDateTime(isoStr) {
    try {
      const d = new Date(isoStr);
      const datePart = d.toLocaleDateString([], { month: "short", day: "numeric" });
      const timePart = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
      return `${datePart}, ${timePart}`;
    } catch {
      return "";
    }
  }

  async function handleApprove(actionId) {
    try {
      const res = await fetch(`/api/approvals/${actionId}/approve`, {
        method: "POST"
      });
      if (res.ok) {
        await loadApprovals();
        loadBriefing();
        checkCalendarStatus();
        checkGmailStatus();

        if (typeof loadDrafts === 'function') loadDrafts();
      } else {
        const data = await res.json();
        alert(data.error || "Failed to approve action.");
      }
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  }

  async function handleReject(actionId) {
    try {
      const res = await fetch(`/api/approvals/${actionId}/reject`, {
        method: "POST"
      });
      if (res.ok) {
        await loadApprovals();
        loadBriefing();
      } else {
        const data = await res.json();
        alert(data.error || "Failed to reject action.");
      }
    } catch (err) {
      alert(`Rejection error: ${err.message}`);
    }
  }

  loadApprovals();

  // -------------------------------------------------------------------------
  // Memory & Preferences Management
  // -------------------------------------------------------------------------
  async function loadMemoryPreferences() {
    try {
      const res = await fetch("/api/memory");
      if (!res.ok) return;
      const data = await res.json();
      const prefs = data.preferences || {};
      if (prefs.name && prefName) prefName.value = prefs.name;
      if (prefs.language && prefLang) prefLang.value = prefs.language;
      if (prefs.preferred_language) {
        updateLanguageUI(prefs.preferred_language);
      } else if (prefs.language) {
        const langMap = { "english": "en-IN", "kannada": "kn-IN", "hindi": "hi-IN", "telugu": "te-IN" };
        const mapped = langMap[prefs.language.toLowerCase()];
        if (mapped) updateLanguageUI(mapped);
      }
    } catch (err) {
      console.warn("Failed to load memory:", err);
    }
  }
  loadMemoryPreferences();

  if (memoryForm) {
    memoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const nameVal = prefName ? prefName.value.trim() : "";
      const langVal = prefLang ? prefLang.value.trim() : "";

      try {
        await fetch("/api/memory", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: "name", value: nameVal })
        });
        await fetch("/api/memory", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: "language", value: langVal })
        });

        if (prefStatusText) {
          prefStatusText.textContent = "Saved";
          setTimeout(() => {
            prefStatusText.textContent = "";
          }, 2500);
        }
      } catch (err) {
        if (prefStatusText) {
          prefStatusText.textContent = "Error saving";
          prefStatusText.style.color = "var(--danger)";
        }
      }
    });
  }

  // -------------------------------------------------------------------------
  // Long-Term Memory: Facts
  // -------------------------------------------------------------------------
  async function loadFacts() {
    try {
      const res = await fetch("/api/facts");
      if (!res.ok) return;
      const data = await res.json();
      renderFacts(data.facts || []);
    } catch (err) {
      console.warn("Failed to load facts:", err);
    }
  }

  function renderFacts(facts) {
    if (!factsList) return;
    factsList.innerHTML = "";

    const count = Array.isArray(facts) ? facts.length : 0;
    if (factsCount) factsCount.textContent = count;

    if (count === 0) {
      factsList.innerHTML = `<div class="empty-notice">No learned facts yet.</div>`;
      return;
    }

    facts.forEach((f) => {
      const item = document.createElement("div");
      item.className = "fact-item";

      const content = document.createElement("div");
      content.className = "fact-content";

      const keySpan = document.createElement("span");
      keySpan.className = "fact-key";
      keySpan.textContent = f.key;

      const colon = document.createTextNode(": ");

      const valSpan = document.createElement("span");
      valSpan.className = "fact-val";
      valSpan.textContent = f.value;

      content.appendChild(keySpan);
      content.appendChild(colon);
      content.appendChild(valSpan);

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn-delete-fact";
      delBtn.textContent = "Delete";
      delBtn.onclick = () => handleDeleteFact(f.key);

      item.appendChild(content);
      item.appendChild(delBtn);
      factsList.appendChild(item);
    });
  }

  async function handleDeleteFact(key) {
    try {
      const res = await fetch(`/api/facts/${encodeURIComponent(key)}`, {
        method: "DELETE"
      });
      if (res.ok) {
        await loadFacts();
      }
    } catch (err) {
      console.warn("Failed to delete fact:", err);
    }
  }

  loadFacts();

  // -------------------------------------------------------------------------
  // Google Calendar Panel Management
  // -------------------------------------------------------------------------
  async function checkCalendarStatus() {
    try {
      const res = await fetch("/api/calendar/status");
      if (!res.ok) {
        renderCalendarDisconnected();
        return;
      }
      const data = await res.json();
      if (data.connected) {
        renderCalendarConnected();
        loadTodayEvents();
      } else {
        renderCalendarDisconnected();
      }
    } catch {
      renderCalendarDisconnected();
    }
  }

  function renderCalendarDisconnected() {
    if (calendarStatusText) {
      calendarStatusText.textContent = "not connected";
      calendarStatusText.classList.remove("connected");
    }
    if (calendarEventsList) {
      calendarEventsList.innerHTML = `<div class="empty-notice">not connected</div>`;
    }
  }

  function renderCalendarConnected() {
    if (calendarStatusText) {
      calendarStatusText.textContent = "connected";
      calendarStatusText.classList.add("connected");
    }
  }

  async function loadTodayEvents() {
    try {
      const res = await fetch("/api/calendar/today");
      if (!res.ok) return;
      const data = await res.json();
      if (!data.connected) {
        renderCalendarDisconnected();
        return;
      }

      const events = data.events || [];
      if (!calendarEventsList) return;
      calendarEventsList.innerHTML = "";

      if (events.length === 0) {
        calendarEventsList.innerHTML = `<div class="empty-notice">No events scheduled for today.</div>`;
        return;
      }

      events.forEach((ev) => {
        const item = document.createElement("div");
        item.className = "calendar-event-item";

        const details = document.createElement("div");
        details.className = "calendar-event-details";

        const meta = document.createElement("div");
        meta.className = "calendar-event-meta";

        const timeSpan = document.createElement("span");
        const startStr = ev.start_time ? formatIsoTime(ev.start_time) : "";
        const endStr = ev.end_time ? formatIsoTime(ev.end_time) : "";
        timeSpan.textContent = startStr ? `${startStr} – ${endStr}` : "All day";

        meta.appendChild(timeSpan);

        const title = document.createElement("div");
        title.className = "calendar-event-title";
        title.textContent = ev.title;

        details.appendChild(meta);
        details.appendChild(title);
        item.appendChild(details);

        calendarEventsList.appendChild(item);
      });
    } catch (err) {
      console.warn("Failed to load today events:", err);
    }
  }

  if (calendarForm) {
    calendarForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = eventTitle ? eventTitle.value.trim() : "";
      const date = eventDate ? eventDate.value.trim() : "";
      const time = eventTime ? eventTime.value.trim() : "";

      if (!title || !date || !time) return;

      try {
        const res = await fetch("/api/calendar/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, date, time, duration_minutes: 30 })
        });

        if (res.ok) {
          if (calendarStatusNotice) {
            calendarStatusNotice.textContent = "Sent to Approvals";
            setTimeout(() => {
              calendarStatusNotice.textContent = "";
            }, 3000);
          }
          if (eventTitle) eventTitle.value = "";
          await loadApprovals();
          loadBriefing();
        } else {
          const data = await res.json();
          alert(data.error || "Failed to submit event request.");
        }
      } catch (err) {
        alert(`Error submitting calendar event: ${err.message}`);
      }
    });
  }

  checkCalendarStatus();

  // -------------------------------------------------------------------------
  // Gmail Panel Management
  // -------------------------------------------------------------------------
  async function checkGmailStatus() {
    try {
      const res = await fetch("/api/gmail/status");
      if (!res.ok) {
        renderGmailDisconnected();
        return;
      }
      const data = await res.json();
      if (data.connected) {
        renderGmailConnected();
        loadRecentEmails();
      } else {
        renderGmailDisconnected();
      }
    } catch {
      renderGmailDisconnected();
    }
  }

  function renderGmailDisconnected() {
    if (gmailStatusText) {
      gmailStatusText.textContent = "not connected";
      gmailStatusText.classList.remove("connected");
    }
    if (gmailConnectBtn) {
      gmailConnectBtn.textContent = "Connect";
      gmailConnectBtn.style.display = "inline-block";
    }
    if (gmailSummariseBtn) {
      gmailSummariseBtn.style.display = "none";
    }
    if (gmailInbox) {
      gmailInbox.innerHTML = `<div class="empty-notice">not connected</div>`;
    }
  }

  function renderGmailConnected() {
    if (gmailStatusText) {
      gmailStatusText.textContent = "connected";
      gmailStatusText.classList.add("connected");
    }
    if (gmailConnectBtn) {
      gmailConnectBtn.textContent = "Reconnect";
    }
    if (gmailSummariseBtn) {
      gmailSummariseBtn.style.display = "inline-block";
    }
  }

  async function loadRecentEmails() {
    try {
      const res = await fetch("/api/gmail/recent");
      if (!res.ok) return;
      const data = await res.json();
      if (!data.connected) {
        renderGmailDisconnected();
        return;
      }

      const emails = data.emails || [];
      if (!gmailInbox) return;
      gmailInbox.innerHTML = "";

      if (emails.length === 0) {
        gmailInbox.innerHTML = `<div class="empty-notice">No emails in the last 24 hours.</div>`;
        return;
      }

      emails.forEach((em) => {
        const item = document.createElement("div");
        item.className = "email-item";

        const details = document.createElement("div");
        details.className = "email-details";

        const topRow = document.createElement("div");
        topRow.className = "email-top-row";

        const senderSpan = document.createElement("span");
        senderSpan.className = "email-sender";
        senderSpan.textContent = em.sender;

        const timeSpan = document.createElement("span");
        timeSpan.className = "email-time";
        timeSpan.textContent = em.time ? formatIsoTime(parseInt(em.time)) : "";

        topRow.appendChild(senderSpan);
        topRow.appendChild(timeSpan);

        const previewBlock = document.createElement("div");
        previewBlock.className = "email-preview-block";

        const subj = document.createElement("span");
        subj.className = "email-subject";
        subj.textContent = em.subject ? em.subject + (em.snippet ? " — " : "") : "";

        const snippet = document.createElement("span");
        snippet.className = "email-snippet";
        snippet.textContent = em.snippet || "";

        previewBlock.appendChild(subj);
        previewBlock.appendChild(snippet);

        details.appendChild(topRow);
        details.appendChild(previewBlock);

        const actionsDiv = document.createElement("div");
        actionsDiv.className = "email-actions";

        const draftBtn = document.createElement("button");
        draftBtn.type = "button";
        draftBtn.className = "btn-draft-reply";
        draftBtn.textContent = "Draft reply";
        draftBtn.onclick = () => openDraftEditorForEmail(em);

        actionsDiv.appendChild(draftBtn);

        item.appendChild(details);
        item.appendChild(actionsDiv);
        gmailInbox.appendChild(item);
      });
    } catch (err) {
      console.warn("Failed to load recent emails:", err);
    }
  }

  if (gmailConnectBtn) {
    gmailConnectBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/gmail/auth-url");
        const data = await res.json();
        if (data.auth_url) {
          window.location.href = data.auth_url;
        } else {
          alert(data.error || "Google Client ID & Secret not configured in .env");
        }
      } catch (err) {
        alert(`OAuth error: ${err.message}`);
      }
    });
  }

  if (gmailSummariseBtn) {
    gmailSummariseBtn.addEventListener("click", async () => {
      if (emailSummaryBox) {
        emailSummaryBox.style.display = "block";
        emailSummaryBox.textContent = "Summarising recent emails…";
      }
      try {
        const res = await fetch("/api/gmail/summarise", { method: "POST" });
        const data = await res.json();
        if (emailSummaryBox) {
          emailSummaryBox.textContent = data.summary || "No summary available.";
        }
        if (data.summary) {
          speakReply(data.summary);
        }
      } catch (err) {
        if (emailSummaryBox) {
          emailSummaryBox.textContent = `Error: ${err.message}`;
        }
      }
    });
  }

  checkGmailStatus();

  // -------------------------------------------------------------------------
  // Gmail Draft Replies Management
  // -------------------------------------------------------------------------
  let activeEmailForDraft = null;

  function openDraftEditorForEmail(em) {
    activeEmailForDraft = em;
    if (draftEditorWrap) draftEditorWrap.style.display = "flex";

    // Clean sender email
    let toAddr = em.sender || "";
    const match = toAddr.match(/<([^>]+)>/);
    if (match) toAddr = match[1];

    if (draftTo) draftTo.value = toAddr;
    if (draftSubject) {
      const origSubj = em.subject || "";
      draftSubject.value = origSubj.toLowerCase().startsWith("re:") ? origSubj : `Re: ${origSubj}`;
    }
    if (draftBody) draftBody.value = "";
    if (draftInstruction) draftInstruction.value = "";
    if (draftSourceEmailId) draftSourceEmailId.value = em.id || "";
    if (draftIdInput) draftIdInput.value = "";
    if (draftStatusNotice) draftStatusNotice.textContent = "";

    draftEditorWrap.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function closeDraftEditor() {
    if (draftEditorWrap) draftEditorWrap.style.display = "none";
    activeEmailForDraft = null;
    if (draftIdInput) draftIdInput.value = "";
  }

  if (closeDraftEditorBtn) {
    closeDraftEditorBtn.addEventListener("click", closeDraftEditor);
  }

  if (generateDraftBtn) {
    generateDraftBtn.addEventListener("click", async () => {
      const instr = draftInstruction ? draftInstruction.value.trim() : "";
      if (!instr) {
        alert("Please enter a short instruction (e.g. 'say yes, ask for tomorrow 3pm').");
        return;
      }

      if (draftStatusNotice) draftStatusNotice.textContent = "Drafting with AI…";

      try {
        const payload = {
          instruction: instr,
          source_email_id: activeEmailForDraft ? activeEmailForDraft.id : (draftSourceEmailId ? draftSourceEmailId.value : null),
          sender: draftTo ? draftTo.value : "",
          subject: draftSubject ? draftSubject.value : "",
          snippet: activeEmailForDraft ? (activeEmailForDraft.snippet || "") : "",
        };

        const res = await fetch("/api/gmail/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (res.ok) {
          const draft = await res.json();
          if (draftIdInput) draftIdInput.value = draft.id;
          if (draftTo) draftTo.value = draft.to_address;
          if (draftSubject) draftSubject.value = draft.subject;
          if (draftBody) draftBody.value = draft.body;
          if (draftStatusNotice) {
            draftStatusNotice.textContent = "Draft generated";
            setTimeout(() => { draftStatusNotice.textContent = ""; }, 3000);
          }
          await loadDrafts();
        } else {
          const err = await res.json();
          alert(err.error || "Failed to generate draft.");
          if (draftStatusNotice) draftStatusNotice.textContent = "";
        }
      } catch (err) {
        alert(`Error generating draft: ${err.message}`);
        if (draftStatusNotice) draftStatusNotice.textContent = "";
      }
    });
  }

  if (saveDraftBtn) {
    saveDraftBtn.addEventListener("click", async () => {
      const to = draftTo ? draftTo.value.trim() : "";
      const subj = draftSubject ? draftSubject.value.trim() : "";
      const body = draftBody ? draftBody.value.trim() : "";
      const curId = draftIdInput ? draftIdInput.value : null;

      if (!to || !subj || !body) {
        alert("Please fill in recipient, subject, and body.");
        return;
      }

      try {
        let res;
        if (curId) {
          res = await fetch(`/api/gmail/drafts/${curId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ to_address: to, subject: subj, body: body }),
          });
        } else {
          res = await fetch("/api/gmail/draft", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              to_address: to,
              subject: subj,
              body: body,
              source_email_id: draftSourceEmailId ? draftSourceEmailId.value : null,
            }),
          });
        }

        if (res.ok) {
          const draft = await res.json();
          if (draftIdInput) draftIdInput.value = draft.id;
          if (draftStatusNotice) {
            draftStatusNotice.textContent = "Draft saved";
            setTimeout(() => { draftStatusNotice.textContent = ""; }, 2500);
          }
          await loadDrafts();
        } else {
          const err = await res.json();
          alert(err.error || "Failed to save draft.");
        }
      } catch (err) {
        alert(`Error saving draft: ${err.message}`);
      }
    });
  }

  if (sendForApprovalBtn) {
    sendForApprovalBtn.addEventListener("click", async () => {
      const to = draftTo ? draftTo.value.trim() : "";
      const subj = draftSubject ? draftSubject.value.trim() : "";
      const body = draftBody ? draftBody.value.trim() : "";
      let curId = draftIdInput ? draftIdInput.value : null;

      if (!to || !subj || !body) {
        alert("Please fill in recipient, subject, and body.");
        return;
      }

      try {
        // Save first if not yet created or edited
        if (!curId) {
          const saveRes = await fetch("/api/gmail/draft", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              to_address: to,
              subject: subj,
              body: body,
              source_email_id: draftSourceEmailId ? draftSourceEmailId.value : null,
            }),
          });
          if (!saveRes.ok) {
            const err = await saveRes.json();
            alert(err.error || "Failed to save draft.");
            return;
          }
          const saved = await saveRes.json();
          curId = saved.id;
          if (draftIdInput) draftIdInput.value = curId;
        } else {
          await fetch(`/api/gmail/drafts/${curId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ to_address: to, subject: subj, body: body }),
          });
        }

        // Send for approval
        const res = await fetch(`/api/gmail/drafts/${curId}/send-for-approval`, {
          method: "POST",
        });

        if (res.ok) {
          if (draftStatusNotice) {
            draftStatusNotice.textContent = "Sent to Approvals!";
            setTimeout(() => { draftStatusNotice.textContent = ""; }, 3000);
          }
          closeDraftEditor();
          await loadDrafts();
          await loadApprovals();
          loadBriefing();
        } else {
          const err = await res.json();
          alert(err.error || "Failed to submit draft for approval.");
        }
      } catch (err) {
        alert(`Error sending draft for approval: ${err.message}`);
      }
    });
  }

  async function loadDrafts() {
    try {
      const res = await fetch("/api/gmail/drafts");
      if (!res.ok) return;
      const drafts = await res.json();
      renderDrafts(drafts);
    } catch (err) {
      console.warn("Failed to load drafts:", err);
    }
  }

  function renderDrafts(drafts) {
    if (!draftsList) return;
    draftsList.innerHTML = "";

    const count = Array.isArray(drafts) ? drafts.length : 0;
    if (draftsCount) draftsCount.textContent = count;

    if (count === 0) {
      draftsList.innerHTML = `<div class="empty-notice">No email drafts.</div>`;
      return;
    }

    drafts.forEach((d) => {
      const item = document.createElement("div");
      item.className = "draft-item";
      item.id = `draft-item-${d.id}`;

      const details = document.createElement("div");
      details.className = "draft-details";

      const meta = document.createElement("div");
      meta.className = "draft-meta";

      const statusBadge = document.createElement("span");
      const st = (d.status || "draft").toLowerCase();
      statusBadge.className = `draft-badge ${st === "pending approval" ? "pending" : (st === "sent" ? "sent" : "")}`;
      statusBadge.textContent = d.status || "draft";

      const toSpan = document.createElement("span");
      toSpan.textContent = `To: ${d.to_address}`;

      meta.appendChild(statusBadge);
      meta.appendChild(toSpan);

      const subjLine = document.createElement("div");
      subjLine.className = "draft-subject-line";
      subjLine.textContent = d.subject;

      const bodyPreview = document.createElement("div");
      bodyPreview.className = "draft-body-preview";
      bodyPreview.textContent = d.body;

      details.appendChild(meta);
      details.appendChild(subjLine);
      details.appendChild(bodyPreview);

      const actionsDiv = document.createElement("div");
      actionsDiv.className = "approval-actions";

      if (d.status === "draft") {
        const sendApproveBtn = document.createElement("button");
        sendApproveBtn.type = "button";
        sendApproveBtn.className = "btn-approve";
        sendApproveBtn.textContent = "Send for approval";
        sendApproveBtn.onclick = async () => {
          try {
            const res = await fetch(`/api/gmail/drafts/${d.id}/send-for-approval`, { method: "POST" });
            if (res.ok) {
              await loadDrafts();
              await loadApprovals();
              loadBriefing();
            } else {
              const err = await res.json();
              alert(err.error || "Failed to send draft for approval.");
            }
          } catch (err) {
            alert(`Error: ${err.message}`);
          }
        };

        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "btn-quiet-action";
        editBtn.textContent = "Edit";
        editBtn.onclick = () => {
          if (draftEditorWrap) draftEditorWrap.style.display = "flex";
          if (draftIdInput) draftIdInput.value = d.id;
          if (draftTo) draftTo.value = d.to_address;
          if (draftSubject) draftSubject.value = d.subject;
          if (draftBody) draftBody.value = d.body;
          if (draftSourceEmailId) draftSourceEmailId.value = d.source_email_id || "";
          draftEditorWrap.scrollIntoView({ behavior: "smooth", block: "nearest" });
        };

        actionsDiv.appendChild(editBtn);
        actionsDiv.appendChild(sendApproveBtn);
      }

      item.appendChild(details);
      item.appendChild(actionsDiv);
      draftsList.appendChild(item);
    });
  }

  loadDrafts();

  // -------------------------------------------------------------------------
  // Expenses Management
  // -------------------------------------------------------------------------
  async function loadExpensesSummary() {
    try {
      const res = await fetch("/api/expenses/summary");
      if (!res.ok) return;
      const data = await res.json();
      if (expensesMonthTotal) {
        const total = typeof data.month_total === "number" ? data.month_total : 0;
        expensesMonthTotal.textContent = total.toLocaleString("en-IN", { maximumFractionDigits: 2 });
      }
    } catch (err) {
      console.warn("Failed to load expenses summary:", err);
    }
  }

  async function loadExpenses() {
    try {
      const res = await fetch("/api/expenses");
      if (!res.ok) return;
      const expenses = await res.json();
      renderExpenses(expenses);
    } catch (err) {
      console.warn("Failed to load expenses:", err);
    }
  }

  function renderExpenses(expenses) {
    if (!expensesList) return;
    expensesList.innerHTML = "";

    const list = Array.isArray(expenses) ? expenses : [];
    if (list.length === 0) {
      expensesList.innerHTML = `<div class="empty-notice">No expenses logged.</div>`;
      return;
    }

    list.forEach((exp) => {
      const item = document.createElement("div");
      item.className = "expense-item";
      item.id = `expense-item-${exp.id}`;

      const left = document.createElement("div");
      left.className = "expense-item-left";

      const amtBadge = document.createElement("span");
      amtBadge.className = "expense-amount-badge";
      amtBadge.textContent = `₹${exp.amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

      const catTag = document.createElement("span");
      catTag.className = "expense-cat-tag";
      catTag.textContent = exp.category || "Other";

      left.appendChild(amtBadge);
      left.appendChild(catTag);
      if (exp.note) {
        const noteSpan = document.createElement("span");
        noteSpan.className = "expense-note-text";
        noteSpan.textContent = exp.note;
        left.appendChild(noteSpan);
      }

      const right = document.createElement("div");
      right.className = "expense-item-right";

      const dateSpan = document.createElement("span");
      dateSpan.className = "expense-date-text";
      let formattedDate = exp.spent_at || "";
      if (formattedDate.length > 10) {
        formattedDate = formattedDate.substring(5, 16);
      }
      dateSpan.textContent = formattedDate;

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn-delete-expense";
      delBtn.title = "Delete expense";
      delBtn.textContent = "×";
      delBtn.onclick = async () => {
        try {
          const delRes = await fetch(`/api/expenses/${exp.id}`, { method: "DELETE" });
          if (delRes.ok) {
            await loadExpenses();
            await loadExpensesSummary();
            loadBriefing();
          } else {
            const err = await delRes.json();
            alert(err.error || "Failed to delete expense.");
          }
        } catch (err) {
          alert(`Error deleting expense: ${err.message}`);
        }
      };

      right.appendChild(dateSpan);
      right.appendChild(delBtn);

      item.appendChild(left);
      item.appendChild(right);
      expensesList.appendChild(item);
    });
  }

  if (expenseForm) {
    expenseForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const amt = parseFloat(expenseAmount ? expenseAmount.value : 0);
      const cat = expenseCategory ? expenseCategory.value : "Other";
      const note = expenseNote ? expenseNote.value.trim() : "";

      if (isNaN(amt) || amt <= 0) {
        alert("Please enter a valid amount greater than 0.");
        return;
      }

      try {
        const res = await fetch("/api/expenses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ amount: amt, category: cat, note: note })
        });

        if (res.ok) {
          if (expenseAmount) expenseAmount.value = "";
          if (expenseNote) expenseNote.value = "";
          await loadExpenses();
          await loadExpensesSummary();
          loadBriefing();
        } else {
          const err = await res.json();
          alert(err.error || "Failed to log expense.");
        }
      } catch (err) {
        alert(`Error logging expense: ${err.message}`);
      }
    });
  }

  loadExpenses();
  loadExpensesSummary();

  // -------------------------------------------------------------------------
  // Notes Management
  // -------------------------------------------------------------------------
  async function loadNotes(query = "") {
    try {
      const url = query ? `/api/notes?q=${encodeURIComponent(query)}` : "/api/notes";
      const res = await fetch(url);
      if (!res.ok) return;
      const notes = await res.json();
      renderNotes(notes);
    } catch (err) {
      console.warn("Failed to load notes:", err);
    }
  }

  function renderNotes(notes) {
    if (!notesList) return;
    notesList.innerHTML = "";

    const list = Array.isArray(notes) ? notes : [];
    if (notesCount) notesCount.textContent = list.length;

    if (list.length === 0) {
      notesList.innerHTML = `<div class="empty-notice">No notes found.</div>`;
      return;
    }

    list.forEach((n) => {
      const item = document.createElement("div");
      item.className = "note-item";
      item.id = `note-item-${n.id}`;

      const left = document.createElement("div");
      left.className = "note-item-left";

      const titleEl = document.createElement("div");
      titleEl.className = "note-item-title";
      titleEl.textContent = n.title;

      const contentEl = document.createElement("div");
      contentEl.className = "note-item-content";
      contentEl.textContent = n.content;

      left.appendChild(titleEl);
      left.appendChild(contentEl);

      const right = document.createElement("div");
      right.className = "note-item-right";

      const dateSpan = document.createElement("span");
      dateSpan.className = "note-date-text";
      let dStr = n.created_at || "";
      if (dStr.length > 10) {
        dStr = dStr.substring(5, 10) + " " + dStr.substring(11, 16);
      }
      dateSpan.textContent = dStr;

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn-delete-note";
      delBtn.title = "Delete note";
      delBtn.textContent = "×";
      delBtn.onclick = async () => {
        try {
          const delRes = await fetch(`/api/notes/${n.id}`, { method: "DELETE" });
          if (delRes.ok) {
            const currentQ = notesSearchInput ? notesSearchInput.value.trim() : "";
            await loadNotes(currentQ);
          } else {
            const err = await delRes.json();
            alert(err.error || "Failed to delete note.");
          }
        } catch (err) {
          alert(`Error deleting note: ${err.message}`);
        }
      };

      right.appendChild(dateSpan);
      right.appendChild(delBtn);

      item.appendChild(left);
      item.appendChild(right);
      notesList.appendChild(item);
    });
  }

  if (noteForm) {
    noteForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = noteTitle ? noteTitle.value.trim() : "";
      const content = noteContent ? noteContent.value.trim() : "";

      if (!content) {
        alert("Please enter note content.");
        return;
      }

      try {
        const res = await fetch("/api/notes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title, content: content })
        });

        if (res.ok) {
          if (noteTitle) noteTitle.value = "";
          if (noteContent) noteContent.value = "";
          if (noteStatusNotice) {
            noteStatusNotice.textContent = "Note saved";
            setTimeout(() => { noteStatusNotice.textContent = ""; }, 2500);
          }
          const currentQ = notesSearchInput ? notesSearchInput.value.trim() : "";
          await loadNotes(currentQ);
        } else {
          const err = await res.json();
          alert(err.error || "Failed to save note.");
        }
      } catch (err) {
        alert(`Error saving note: ${err.message}`);
      }
    });
  }

  if (notesSearchInput) {
    notesSearchInput.addEventListener("input", (e) => {
      loadNotes(e.target.value.trim());
    });
  }

  loadNotes();

  // -------------------------------------------------------------------------
  // Voice Synthesis (TTS) - Free browser SpeechSynthesis
  // -------------------------------------------------------------------------
  function getVoiceForLang(langCode) {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    const target = (langCode || currentLanguage || "en-IN").toLowerCase();
    const prefix = target.split("-")[0];

    // 1. Exact match (e.g. te-IN)
    let match = voices.find(v => v.lang && v.lang.toLowerCase() === target);
    if (match) return match;

    // 2. Prefix match (e.g. te, kn, hi)
    match = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
    if (match) return match;

    // 3. Fallback to en-IN (say so in console only, not to the user)
    console.log(`No voice found for ${target}, falling back to en-IN`);
    return (
      voices.find(v => v.lang === "en-IN" || v.lang === "en_IN") ||
      voices.find(v => v.lang && v.lang.toLowerCase().includes("en-in")) ||
      voices.find(v => v.lang && v.lang.startsWith("en")) ||
      null
    );
  }

  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      getVoiceForLang(currentLanguage);
    };
  }

  function speakReply(text) {
    if (!voiceReplyEnabled || !('speechSynthesis' in window)) {
      return;
    }

    try {
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      const chosenVoice = getVoiceForLang(currentLanguage);
      if (chosenVoice) {
        utterance.voice = chosenVoice;
        utterance.lang = chosenVoice.lang || currentLanguage;
      } else {
        utterance.lang = currentLanguage;
      }
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
        if (voiceState) voiceState.textContent = texts.speaking;
      };

      utterance.onend = () => {
        const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
        if (voiceState && (voiceState.textContent === "Speaking…" || voiceState.textContent === texts.speaking)) {
          voiceState.textContent = texts.ready;
        }
      };

      utterance.onerror = () => {
        const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
        if (voiceState && (voiceState.textContent === "Speaking…" || voiceState.textContent === texts.speaking)) {
          voiceState.textContent = texts.ready;
        }
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn("SpeechSynthesis error:", err);
      const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
      if (voiceState && (voiceState.textContent === "Speaking…" || voiceState.textContent === texts.speaking)) {
        voiceState.textContent = texts.ready;
      }
    }
  }

  // Voice on/off toggle button
  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener("click", () => {
      voiceReplyEnabled = !voiceReplyEnabled;
      const onIcon = voiceToggleBtn.querySelector(".voice-icon-on");
      const offIcon = voiceToggleBtn.querySelector(".voice-icon-off");

      if (voiceReplyEnabled) {
        voiceToggleBtn.classList.add("active");
        voiceToggleBtn.title = "Voice replies: ON";
        if (onIcon) onIcon.style.display = "block";
        if (offIcon) offIcon.style.display = "none";
      } else {
        voiceToggleBtn.classList.remove("active");
        voiceToggleBtn.title = "Voice replies: OFF";
        if (onIcon) onIcon.style.display = "none";
        if (offIcon) offIcon.style.display = "block";
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
        if (voiceState && voiceState.textContent === "Speaking…") {
          voiceState.textContent = "Ready";
        }
      }
    });
  }

  // -------------------------------------------------------------------------
  // Speech Recognition (STT) - Free browser Web Speech API
  // -------------------------------------------------------------------------
  const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

  function initSpeechRecognition() {
    if (!SpeechRecognitionClass) {
      return null;
    }

    const rec = new SpeechRecognitionClass();
    rec.lang = currentLanguage || "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      isListening = true;
      speechTextRecognized = "";
      const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
      if (heroMicBtn) heroMicBtn.classList.add("active");
      if (barMicBtn) barMicBtn.classList.add("active");
      if (voiceState) voiceState.textContent = texts.listening;
      if (liveTranscript) liveTranscript.textContent = texts.listening;
    };

    rec.onresult = (event) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcriptChunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcriptChunk;
        } else {
          interim += transcriptChunk;
        }
      }

      const currentText = final || interim;
      if (currentText) {
        speechTextRecognized = currentText;
        messageInput.value = currentText;
        if (liveTranscript) liveTranscript.textContent = currentText;
      }
    };

    rec.onerror = (event) => {
      console.warn("Speech recognition event:", event.error);
      if (event.error === "not-allowed") {
        appendSystemNote("Microphone permission denied. Allow microphone access in your browser settings.");
      }
      stopListening();
    };

    rec.onend = () => {
      stopListening();
      const textToSend = speechTextRecognized.trim() || messageInput.value.trim();
      if (textToSend) {
        speechTextRecognized = "";
        sendMessage(textToSend);
      } else {
        const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
        if (voiceState) voiceState.textContent = texts.ready;
        if (liveTranscript) liveTranscript.textContent = "";
      }
    };

    return rec;
  }

  function startListening() {
    if (!SpeechRecognitionClass) {
      const unsupportedMsg = "Voice input needs Chrome or Edge. Text chat still works.";
      if (liveTranscript) liveTranscript.textContent = unsupportedMsg;
      appendSystemNote(unsupportedMsg);
      return;
    }

    if (isListening) {
      if (recognition) recognition.stop();
      return;
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    try {
      if (!recognition) {
        recognition = initSpeechRecognition();
      }
      if (recognition) {
        recognition.lang = currentLanguage || "en-IN";
      }
      recognition.start();
    } catch (e) {
      console.warn("Could not start recognition:", e);
      stopListening();
    }
  }

  function stopListening() {
    isListening = false;
    const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
    if (heroMicBtn) heroMicBtn.classList.remove("active");
    if (barMicBtn) barMicBtn.classList.remove("active");
    if (voiceState && (voiceState.textContent === "Listening…" || voiceState.textContent === texts.listening)) {
      voiceState.textContent = texts.ready;
    }
  }

  if (heroMicBtn) heroMicBtn.addEventListener("click", startListening);
  if (barMicBtn) barMicBtn.addEventListener("click", startListening);

  // -------------------------------------------------------------------------
  // Render Messages
  // -------------------------------------------------------------------------
  function appendUserMessage(text) {
    const placeholder = document.getElementById("chatPlaceholder");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    el.className = "chat-message user";

    const content = document.createElement("div");
    content.className = "message-text";
    content.textContent = text;

    el.appendChild(content);
    chatTranscript.appendChild(el);
    scrollToBottom();
  }

  function appendAuraReply(text, timestamp = formatTimestamp()) {
    const placeholder = document.getElementById("chatPlaceholder");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    el.className = "chat-message assistant";

    const meta = document.createElement("span");
    meta.className = "message-meta";
    meta.textContent = `AURA · ${timestamp}`;

    const content = document.createElement("div");
    content.className = "message-text";
    content.textContent = text;

    el.appendChild(meta);
    el.appendChild(content);
    chatTranscript.appendChild(el);

    scrollToBottom();
  }

  function appendSystemNote(text) {
    const placeholder = document.getElementById("chatPlaceholder");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    el.className = "chat-message system-note";

    const content = document.createElement("div");
    content.className = "message-text";
    content.textContent = text;

    el.appendChild(content);
    chatTranscript.appendChild(el);
    scrollToBottom();
  }

  function appendErrorMessage(errorText) {
    const placeholder = document.getElementById("chatPlaceholder");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    el.className = "chat-message assistant error";

    const meta = document.createElement("span");
    meta.className = "message-meta";
    meta.textContent = `AURA · ${formatTimestamp()}`;

    const content = document.createElement("div");
    content.className = "message-text";
    content.textContent = errorText;

    el.appendChild(meta);
    el.appendChild(content);
    chatTranscript.appendChild(el);
    scrollToBottom();
  }

  function showThinking() {
    const placeholder = document.getElementById("chatPlaceholder");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    el.className = "chat-message thinking";
    el.id = "thinkingIndicator";
    el.textContent = "Thinking…";
    chatTranscript.appendChild(el);
    if (voiceState) voiceState.textContent = "Thinking…";
    scrollToBottom();
  }

  function removeThinking() {
    const el = document.getElementById("thinkingIndicator");
    if (el) el.remove();
    const texts = LANGUAGE_TEXTS[currentLanguage] || LANGUAGE_TEXTS["en-IN"];
    if (voiceState && voiceState.textContent === "Thinking…") {
      voiceState.textContent = texts.ready;
    }
  }

  function scrollToBottom() {
    if (chatTranscript) {
      chatTranscript.scrollTop = chatTranscript.scrollHeight;
    }
  }

  // -------------------------------------------------------------------------
  // Send Message Logic
  // -------------------------------------------------------------------------
  async function sendMessage(rawText) {
    const text = rawText.trim();
    if (!text) return;

    messageInput.value = "";
    if (liveTranscript) liveTranscript.textContent = "";

    appendUserMessage(text);
    showThinking();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: conversationHistory
        })
      });

      removeThinking();

      if (!response.ok) {
        let errMessage = `Error ${response.status}`;
        try {
          const errData = await response.json();
          if (errData && errData.error) {
            errMessage = errData.error;
          }
        } catch {}
        appendErrorMessage(errMessage);
        return;
      }

      const data = await response.json();
      const reply = data.reply || "(no response)";

      conversationHistory.push({ role: "user", content: text });
      conversationHistory.push({ role: "model", content: reply });

      appendAuraReply(reply);
      speakReply(reply);
      loadFacts();
      loadApprovals();
      loadBriefing();
      loadExpenses();
      loadExpensesSummary();
      loadNotes();

    } catch (err) {
      removeThinking();
      appendErrorMessage(`Connection error: ${err.message}`);
    }
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(messageInput.value);
  });
});
