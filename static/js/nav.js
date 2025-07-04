/**
 * Navigation Side Panel Controller
 * ===============================
 * 
 * This module provides functionality for the side navigation panel in the VMS.
 * It handles the toggle behavior, overlay management, and keyboard shortcuts
 * for the "More" menu dropdown.
 * 
 * Key Features:
 * - Side panel toggle functionality
 * - Overlay creation and management
 * - Keyboard shortcut support (ESC key)
 * - Click outside to close behavior
 * - Smooth animations and transitions
 * 
 * DOM Elements:
 * - #moreMenuToggle: The "More" menu button
 * - #sideNavPanel: The side navigation panel
 * - .side-nav-overlay: Dynamically created overlay
 * 
 * Event Handlers:
 * - Click on moreMenuToggle: Toggle side panel
 * - Click on overlay: Close side panel
 * - ESC key: Close side panel if open
 * 
 * CSS Classes:
 * - .active: Applied to panel and toggle when open
 * - .side-nav-overlay: Overlay styling
 * 
 * Dependencies:
 * - Bootstrap 5.3.3 CSS/JS
 * - Custom CSS for side panel styling
 * 
 * Usage:
 * - Automatically initializes on DOM content loaded
 * - No manual initialization required
 * - Works with existing HTML structure
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const moreMenuToggle = document.getElementById('moreMenuToggle');
    const sideNavPanel = document.getElementById('sideNavPanel');
    const body = document.body;
    
    // Create overlay element for background dimming
    const overlay = document.createElement('div');
    overlay.className = 'side-nav-overlay';
    body.appendChild(overlay);
    
    /**
     * Toggle the side navigation panel visibility
     * Handles both opening and closing the panel
     */
    function toggleSideNav() {
        sideNavPanel.classList.toggle('active');
        moreMenuToggle.classList.toggle('active');
        overlay.classList.toggle('active');
    }
    
    // Event listener for the "More" menu button
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