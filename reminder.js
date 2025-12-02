// simple client-side reminder using localStorage (acts like a cookie)
// shows popup once a day unless dismissed
document.addEventListener("DOMContentLoaded", function() {
  const popup = document.getElementById('reminder-popup');
  const remindNow = document.getElementById('remind-now');
  const dismiss = document.getElementById('dismiss-reminder');

  // Date key format YYYY-MM-DD
  function todayKey() {
    const d = new Date();
    return d.getFullYear() + "-" + (d.getMonth()+1).toString().padStart(2,'0') + "-" + d.getDate().toString().padStart(2,'0');
  }

  const dismissedFor = localStorage.getItem('dismissed_for_date'); // YYYY-MM-DD
  const lastShown = localStorage.getItem('reminder_last_shown'); // timestamp

  // show if not dismissed for today
  if (dismissedFor !== todayKey()) {
    // check last shown to avoid showing repeatedly within same session
    if (!lastShown || (Date.now() - parseInt(lastShown, 10) > (1000*60*60*6))) { // 6 hours threshold
      popup.classList.remove('hidden');
      localStorage.setItem('reminder_last_shown', Date.now().toString());
    }
  }

  remindNow.addEventListener('click', () => {
    // hide for now and show in 1 hour by clearing last_shown so it can reappear
    popup.classList.add('hidden');
    // set last_shown such that it will be allowed to show after 1 hour
    localStorage.setItem('reminder_last_shown', (Date.now() - (1000*60*60*5)).toString());
  });

  dismiss.addEventListener('click', () => {
    localStorage.setItem('dismissed_for_date', todayKey());
    popup.classList.add('hidden');
  });
});
