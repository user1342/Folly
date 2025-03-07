/**
 * Challenge page functionality
 * Handles form submissions, loading indicators, and UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const form = document.getElementById('prompt-form');
    const textarea = document.querySelector('.input-box');
    const sendButton = document.getElementById('send-button');
    const resetButton = document.getElementById('reset-button');
    const loadingMessageRow = document.getElementById('loading-message-row');
    const progressContainer = document.getElementById('progress-container');
    
    // Auto-resize textarea to fit content
    function resizeTextarea(el) {
        el.style.height = '24px';
        el.style.height = Math.min((el.scrollHeight), 200) + 'px';
    }
    
    // Activate loading indicators
    function activateLoading() {
        // Disable inputs
        sendButton.disabled = true;
        resetButton.disabled = true;
        textarea.disabled = true;
        
        // Update button state
        sendButton.classList.add('disabled');
        sendButton.classList.add('loading');
        
        // Show progress bar
        progressContainer.classList.add('active');
        
        // Show loading message
        loadingMessageRow.classList.remove('d-none');
        
        // Force a repaint to ensure animations start
        void loadingMessageRow.offsetWidth;
        
        // Scroll to show loading indicator
        setTimeout(() => {
            loadingMessageRow.scrollIntoView({behavior: 'smooth', block: 'end'});
        }, 100);
        
        console.log('Loading indicators activated');
    }
    
    // Auto-resize on input
    if (textarea) {
        textarea.addEventListener('input', function() {
            resizeTextarea(this);
        });
        
        // Initial resize
        resizeTextarea(textarea);
    }
    
    // Handle Enter key to submit (but allow Shift+Enter for new lines)
    if (textarea) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!sendButton.disabled) {
                    form.submit();
                }
            }
        });
    }
    
    // Handle form submission
    if (form) {
        form.addEventListener('submit', function(e) {
            activateLoading();
        });
    }
    
    // Scroll to bottom on load
    window.scrollTo(0, document.body.scrollHeight);
});
