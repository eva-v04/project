let previousCount = -1;

function checkNotifications() {
    fetch('/check-notifications/') 
        .then(res => res.json())
        .then(data => {
            // data.notifications είναι η λίστα που στέλνει η View σου
            if (data.notifications && data.notifications.length > 0) {
                data.notifications.forEach(notif => {
                    // Εμφανίζουμε το Pop-up για κάθε νέα ειδοποίηση
                    showToast(notif.title, notif.message);
                });
                
                // Ενημερώνουμε και το badge αν υπάρχει στη σελίδα
                updateBadgeManually(data.notifications.length);
            }
        })
        .catch(err => console.error("Error fetching notifications:", err));
}

function showToast(title, message) {
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    
    // Όταν ο χρήστης πατάει το Pop-up, πηγαίνει στο ιστορικό
    toast.innerHTML = `
        <div onclick="window.location.href='/notifications/'" style="cursor:pointer;">
            <strong style="color: #00d2ff;">${title}</strong><br>
            <span style="font-size: 0.9rem;">${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    //για να εμφανιστεί
    setTimeout(() => toast.classList.add('show'), 100);
    
    //για να εξαφανιστεί μετά από 6 δευτερόλεπτα
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 6000);
}

// Βοηθητική συνάρτηση για να αλλάζει ο αριθμός στην καμπάνα
function updateBadgeManually(count) {
    const badge = document.getElementById('notification-badge');
    if (badge && count > 0) {
        badge.innerText = count;
        badge.style.display = 'block';
    }
}

// Έλεγχος κάθε 5 δευτερόλεπτα
setInterval(checkNotifications, 5000);
// Έλεγχος και με το που φορτώνει η σελίδα
document.addEventListener('DOMContentLoaded', checkNotifications);