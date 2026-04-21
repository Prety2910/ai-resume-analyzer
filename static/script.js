let currentAnalysis = null;

const resumeFile = document.getElementById("resumeFile");
const analyzeBtn = document.getElementById("analyzeBtn");
const statusMsg = document.getElementById("statusMsg");
const resultsSection = document.getElementById("resultsSection");

const scoreValue = document.getElementById("scoreValue");
const scoreLabel = document.getElementById("scoreLabel");
const scoreBar = document.getElementById("scoreBar");
const scoreCircle = document.getElementById("scoreCircle");
const wordCountText = document.getElementById("wordCountText");
const fileInfoText = document.getElementById("fileInfoText");

const bestRole = document.getElementById("bestRole");
const bestMatchScore = document.getElementById("bestMatchScore");
const allMatchesContainer = document.getElementById("allMatchesContainer");

const skillsContainer = document.getElementById("skillsContainer");
const missingSkillsContainer = document.getElementById("missingSkillsContainer");
const suggestionsList = document.getElementById("suggestionsList");

const chatBox = document.getElementById("chatBox");
const chatInput = document.getElementById("chatInput");
const sendChatBtn = document.getElementById("sendChatBtn");

analyzeBtn.addEventListener("click", analyzeResume);
sendChatBtn.addEventListener("click", sendChatMessage);

chatInput.addEventListener("keypress", function (e) {
  if (e.key === "Enter") {
    sendChatMessage();
  }
});

async function analyzeResume() {
  const file = resumeFile.files[0];

  if (!file) {
    statusMsg.textContent = "Please choose a PDF resume first.";
    return;
  }

  const formData = new FormData();
  formData.append("resume", file);

  statusMsg.textContent = "Analyzing your resume...";
  analyzeBtn.disabled = true;

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    console.log("Analyze response:", data);

    if (!response.ok) {
      statusMsg.textContent = data.error || "Something went wrong.";
      analyzeBtn.disabled = false;
      return;
    }

    currentAnalysis = data;
    renderResults(data);
    resultsSection.classList.remove("hidden");
    statusMsg.textContent = "Resume analyzed successfully.";

    chatBox.innerHTML = `
      <div class="bot-message">
        Your resume has been analyzed. Ask me about your score, missing skills, best role, or how to improve your resume.
      </div>
    `;
  } catch (error) {
    console.error(error);
    statusMsg.textContent = "Error analyzing resume. Please try again.";
  } finally {
    analyzeBtn.disabled = false;
  }
}

function renderResults(data) {
  scoreValue.textContent = `${data.score}%`;
  scoreLabel.textContent = data.score_label;
  scoreBar.style.width = `${data.score}%`;
  scoreCircle.style.background = `conic-gradient(#f0ab1f ${data.score * 3.6}deg, #2b2b2b 0deg)`;

  wordCountText.textContent = `${data.word_count} words detected in your resume`;
  fileInfoText.textContent = `File: ${data.file_name} • Analyzed at: ${data.analyzed_at}`;

  bestRole.textContent = data.best_role;
  bestMatchScore.textContent = `${data.best_match_score}%`;

  renderJobMatches(data.all_job_matches);
  renderTags(skillsContainer, data.detected_skills, false, "No skills detected.");
  renderTags(missingSkillsContainer, data.missing_skills, true, "No major missing skills found.");
  renderSuggestions(data.suggestions);
}

function renderJobMatches(matches) {
  allMatchesContainer.innerHTML = "";

  Object.entries(matches).forEach(([role, score]) => {
    const item = document.createElement("div");
    item.className = "match-item";

    item.innerHTML = `
      <div class="match-item-top">
        <span>${role}</span>
        <span>${score}%</span>
      </div>
      <div class="match-track">
        <div class="match-fill" style="width: ${score}%"></div>
      </div>
    `;

    allMatchesContainer.appendChild(item);
  });
}

function renderTags(container, items, isMissing, emptyText) {
  container.innerHTML = "";

  if (!items || items.length === 0) {
    const p = document.createElement("p");
    p.className = "empty-text";
    p.textContent = emptyText;
    container.appendChild(p);
    return;
  }

  items.forEach((item) => {
    const tag = document.createElement("span");
    tag.className = isMissing ? "tag missing" : "tag";
    tag.textContent = item;
    container.appendChild(tag);
  });
}

function renderSuggestions(suggestions) {
  suggestionsList.innerHTML = "";

  if (!suggestions || suggestions.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No additional suggestions right now.";
    suggestionsList.appendChild(li);
    return;
  }

  suggestions.forEach((tip) => {
    const li = document.createElement("li");
    li.textContent = tip;
    suggestionsList.appendChild(li);
  });
}

async function sendChatMessage() {
  const message = chatInput.value.trim();

  if (!message) return;

  addUserMessage(message);
  chatInput.value = "";

  if (!currentAnalysis) {
    addBotMessage("Please analyze a resume first.");
    return;
  }

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: message,
        analysis: currentAnalysis
      })
    });

    const data = await response.json();
    addBotMessage(data.reply || "Sorry, I could not answer that.");
  } catch (error) {
    console.error(error);
    addBotMessage("There was a problem connecting to the chatbot.");
  }
}

function addUserMessage(text) {
  const div = document.createElement("div");
  div.className = "user-message";
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function addBotMessage(text) {
  const div = document.createElement("div");
  div.className = "bot-message";
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}
