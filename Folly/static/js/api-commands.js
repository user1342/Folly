/**
 * API Commands Panel functionality
 * Handles displaying and copying API command examples for challenges
 */

document.addEventListener('DOMContentLoaded', function() {
    initApiCommandsPanel();
});

/**
 * Initialize the API commands panel
 */
function initApiCommandsPanel() {
    // Get panel elements
    const panel = document.getElementById('api-commands-panel');
    const panelToggle = document.getElementById('api-panel-toggle');
    const closeBtn = document.querySelector('.close-api-panel');
    const tabs = document.querySelectorAll('.api-tab');
    const codeBlocks = document.querySelectorAll('.api-code-block');
    const copyButtons = document.querySelectorAll('.copy-btn');
    
    // Set up toggle button
    if (panelToggle) {
        panelToggle.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent document click from closing immediately
            panel.classList.add('active');
        });
    }
    
    // Set up close button
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            panel.classList.remove('active');
        });
    }
    
    // Allow closing panel by clicking outside
    document.addEventListener('click', function(event) {
        if (panel && panel.classList.contains('active') && 
            !panel.contains(event.target) && 
            event.target !== panelToggle) {
            panel.classList.remove('active');
        }
    });
    
    // Prevent clicks inside panel from closing it
    if (panel) {
        panel.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
    
    // Set up tabs
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show correct content
            codeBlocks.forEach(block => {
                block.classList.remove('active');
                if (block.id === target) {
                    block.classList.add('active');
                }
            });
        });
    });
    
    // Set up copy buttons
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const codeElem = this.closest('.api-code-block').querySelector('pre.code');
            const copyIndicator = this.querySelector('.copied-indicator');
            
            if (codeElem) {
                // Copy text to clipboard
                navigator.clipboard.writeText(codeElem.textContent).then(() => {
                    // Show copied indicator
                    copyIndicator.style.display = 'inline';
                    
                    // Reset after animation
                    setTimeout(() => {
                        copyIndicator.style.display = 'none';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy text: ', err);
                    alert('Failed to copy to clipboard. Please try again or copy manually.');
                });
            }
        });
    });
}

/**
 * Format the challenge name for API endpoints
 * @param {string} name - The challenge name
 * @returns {string} - Formatted name for API
 */
function formatChallengeNameForApi(name) {
    return name.toLowerCase().replace(/\s+/g, '_');
}
