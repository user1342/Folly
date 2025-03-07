/**
 * Settings functionality for LLM Challenge UI
 * Handles the settings modal and form actions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings modal
    initSettingsModal();
});

/**
 * Initialize the settings modal functionality
 */
function initSettingsModal() {
    // Get modal elements
    const modal = document.getElementById('settings-modal');
    const settingsBtn = document.querySelector('.settings-button');
    const closeBtn = document.querySelector('.close-modal');
    
    // Open modal when settings button is clicked
    if (settingsBtn) {
        settingsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            modal.classList.add('active');
        });
    }
    
    // Close modal when close button is clicked
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.remove('active');
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.classList.remove('active');
        }
    });
    
    // Prevent modal close when clicking inside modal content
    if (modal) {
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }
    }
}

/**
 * Submit the clear settings form
 */
function submitClearSettings() {
    if (confirm('This will reset your API settings to the default. Continue?')) {
        document.getElementById('clear-settings-form').submit();
    }
}
