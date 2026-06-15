// ============================================================
//  THEME.JS – Auto-applies role theme + site name on every page
//  Add <script src="theme.js"></script> to every HTML page
// ============================================================

(function () {
  const role     = sessionStorage.getItem('role') || 'student';
  const siteName = sessionStorage.getItem('siteName') || 'SmartLearn Hub';
  const cls      = sessionStorage.getItem('userClass') || '';

  // 1. Apply body theme class
  if(document.body) document.body.classList.add('theme-' + role);

  // 2. Wait for DOM then update dynamic content
  document.addEventListener('DOMContentLoaded', function () {

    // Update all sidebar logo text
    document.querySelectorAll('.sidebar-logo span').forEach(el => {
      el.textContent = siteName;
    });

    // Update all <title> tags
    const titleEl = document.querySelector('title');
    if (titleEl) {
      titleEl.textContent = titleEl.textContent.replace('SmartLearn', siteName).replace('SmartLearn Hub', siteName);
    }

    // Show class badge in header if present
    const headerRight = document.querySelector('.header-right');
    if (headerRight && cls) {
      const badge = document.createElement('div');
      badge.className = 'role-badge';
      badge.innerHTML = (role === 'teacher' ? '🏫 ' : '📚 ') + cls;
      badge.style.marginRight = '10px';
      headerRight.insertBefore(badge, headerRight.firstChild);
    }

    // Add role badge next to avatar
    const avatar = document.querySelector('.user-avatar');
    if (avatar) {
      avatar.title = role.charAt(0).toUpperCase() + role.slice(1) + (cls ? ' · ' + cls : '');
    }
  });
})();
function saveChapter() {
const title = document.getElementById("chapterTitle").value;
const category = document.getElementById("chapterCategory").value;
const video = document.getElementById("videoFile").files[0];
const pdf = document.getElementById("pdfFile").files[0];
const desc = document.getElementById("chapterDesc").value;

if (!title || !video || !pdf) {
alert("Please fill all required fields!");
return;
}

console.log("Chapter:", title);
console.log("Video file:", video.name);
console.log("PDF file:", pdf.name);

alert("File selected successfully!\n(Backend lagel save karayla)");
}
