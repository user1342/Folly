/**
 * Simple AJAX utilities for Folly application
 */

// Detect if running in iframe
const isInIframe = window !== window.parent;

// Function to submit forms via AJAX
function ajaxifyForm(formElement, options = {}) {
    if (!formElement) return;
    
    const defaults = {
        onStart: () => {},
        onSuccess: (data) => {
            if (data.redirect) {
                window.location.href = data.redirect;
            } else if (data.html) {
                document.open();
                document.write(data.html);
                document.close();
            }
        },
        onError: (error) => {
            console.error('AJAX form error:', error);
            alert('Error submitting form. Please try again.');
        },
        extraHeaders: {}
    };
    
    const settings = {...defaults, ...options};
    
    formElement.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Call the onStart callback
        settings.onStart();
        
        // Prepare form data
        const formData = new FormData(this);
        
        // Get the form action URL
        const url = this.action || window.location.href;
        
        // Set up AJAX request
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
            ...settings.extraHeaders
        };
        
        // Send the request
        fetch(url, {
            method: 'POST',
            headers: headers,
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            settings.onSuccess(data);
        })
        .catch(error => {
            settings.onError(error);
        });
    });
}

// Automatically handle all forms with class "ajax-form"
document.addEventListener('DOMContentLoaded', function() {
    if (isInIframe) {
        // In iframe, ajaxify all forms unless they have data-bypass-ajax
        const forms = document.querySelectorAll('form:not([data-bypass-ajax])');
        forms.forEach(form => {
            if (!form.classList.contains('ajax-processed')) {
                ajaxifyForm(form);
                form.classList.add('ajax-processed');
            }
        });
    } else {
        // Outside iframe, only ajaxify forms with class ajax-form
        const forms = document.querySelectorAll('form.ajax-form');
        forms.forEach(form => {
            if (!form.classList.contains('ajax-processed')) {
                ajaxifyForm(form);
                form.classList.add('ajax-processed');
            }
        });
    }
});
