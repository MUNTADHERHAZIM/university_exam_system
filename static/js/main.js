// University Exam System — Main JS

// Sidebar toggle
document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }

    // Auto-dismiss alerts
    document.querySelectorAll('.alert.auto-dismiss').forEach(a => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(a);
            bsAlert.close();
        }, 4000);
    });
});
