// ============================================================
//  SCRIPT.JS – Shared UI functions
// ============================================================

function renderContentList(containerId, chapters) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (chapters.length === 0) {
    container.innerHTML = `<p>No content found</p>`;
    return;
  }

  container.innerHTML = chapters.map((ch, idx) => `
    <div class="content-card">
      <div class="card-number">${idx + 1}</div>

      <div class="card-info">
        <h3>${ch.title}</h3>
        <p>${ch.category}</p>
      </div>

      <div class="card-actions">
        <button onclick="goLearn(${idx})" class="btn-action learn">
          ▶ Learn
        </button>

        <button onclick="goNotes(${idx})" class="btn-action notes">
          📄 Notes
        </button>

        <button onclick="goQuiz(${idx})" class="btn-action quiz">
          📝 Quiz
        </button>
      </div>
    </div>
  `).join('');

  // store globally
  window.currentChapters = chapters;
}

function renderStudents(containerId, students) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = students.map(s => `
    <div class="student-card">
      <div class="student-avatar">${s.name.charAt(0)}</div>
      <div class="student-info">
        <h3>${s.name}</h3>
        <p>Grade: ${s.grade}</p>
      </div>
      <div class="progress-wrap">
        <div class="progress-bar">
          <div class="progress-fill" style="width:${s.progress}%"></div>
        </div>
        <span>${s.progress}%</span>
      </div>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  const current = window.location.pathname.split('/').pop();
  document.querySelectorAll('.nav-item').forEach(link => {
    const href = link.getAttribute('href');
    if (href === current) link.classList.add('active');
    else link.classList.remove('active');
  });
});


// === Videos tab===

function addVideo() {
    let input = document.getElementById("videoInput");
    let file = input.files[0];

    if (file) {
        let video = document.createElement("video");
        video.controls = true;
        video.width = 300;

        let source = document.createElement("source");
        source.src = URL.createObjectURL(file);
        source.type = "video/mp4";

        video.appendChild(source);

        document.getElementById("videoContainer").appendChild(video);
    }
}