// data.js — Shared Store using localStorage (works across tabs on same Pi server)

const appData = {
  siteName: "SmartLearn",
  version:  "1.0.0",
  students: [
    { id:1, name:"Aarav Sharma",   roll:"R001", grade:"10th", progress:78 },
    { id:2, name:"Priya Patel",    roll:"R002", grade:"9th",  progress:92 },
    { id:3, name:"Rohit Verma",    roll:"R003", grade:"10th", progress:55 },
    { id:4, name:"Sneha Kulkarni", roll:"R004", grade:"8th",  progress:63 },
    { id:5, name:"Arjun Desai",    roll:"R005", grade:"10th", progress:85 },
    { id:6, name:"Meera Joshi",    roll:"R006", grade:"9th",  progress:71 }
  ]
};

(function(){
  var KEY = 'SL_STORE';
  var defaults = {
    chapters:    { math:[], science:[], english:[], social:[], computer:[] },
    papers:      { math:[], science:[], english:[], social:[], computer:[] },
    quizResults: []
  };

  var saved = null;
  try { saved = JSON.parse(localStorage.getItem(KEY)); } catch(e){}

  window.SLStore = saved || defaults;

  // Always ensure all subject keys exist even on old saved data
  ['math','science','english','social','computer'].forEach(function(id){
    if(!window.SLStore.chapters[id])    window.SLStore.chapters[id]    = [];
    if(!window.SLStore.papers[id])      window.SLStore.papers[id]      = [];
  });
  if(!window.SLStore.quizResults) window.SLStore.quizResults = [];

  window.SLStore.save = function(){
    try {
      localStorage.setItem(KEY, JSON.stringify({
        chapters:    this.chapters,
        papers:      this.papers,
        quizResults: this.quizResults
      }));
    } catch(e){ alert('Storage full or blocked. Try clearing browser data.'); }
  };
})();