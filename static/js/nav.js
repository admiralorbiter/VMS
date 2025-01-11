document.addEventListener('DOMContentLoaded', function() {
    const moreMenuToggle = document.getElementById('moreMenuToggle');
    const sideNavPanel = document.getElementById('sideNavPanel');
    const body = document.body;
    
    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'side-nav-overlay';
    body.appendChild(overlay);
    
    function toggleSideNav() {
        sideNavPanel.classList.toggle('active');
        moreMenuToggle.classList.toggle('active');
        overlay.classList.toggle('active');
    }
    
    moreMenuToggle.addEventListener('click', function(e) {
        e.preventDefault();
        toggleSideNav();
    });
    
    // Close side nav when clicking overlay
    overlay.addEventListener('click', toggleSideNav);
    
    // Close side nav when pressing ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sideNavPanel.classList.contains('active')) {
            toggleSideNav();
        }
    });
}); 