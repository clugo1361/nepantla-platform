// Main JavaScript file for Nepantla API Platform

document.addEventListener('DOMContentLoaded', function() {
    // Check API health status on page load
    checkApiHealth();
    
    // Add event listeners for any interactive elements
    setupEventListeners();
});

/**
 * Check the health of the API and update UI accordingly
 */
function checkApiHealth() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            console.log('API Health Status:', data);
            // Could update a status indicator in the UI here if needed
        })
        .catch(error => {
            console.error('API Health Check Failed:', error);
            // Could show an error message in the UI here if needed
        });
}

/**
 * Set up event listeners for interactive elements
 */
function setupEventListeners() {
    // Example: Highlight code blocks on click for easy copying
    const codeBlocks = document.querySelectorAll('pre code');
    if (codeBlocks) {
        codeBlocks.forEach(block => {
            block.addEventListener('click', function() {
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(this);
                selection.removeAllRanges();
                selection.addRange(range);
            });
        });
    }
    
    // Add more event listeners as needed
}

/**
 * Utility function to format timestamps
 * @param {string} isoTimestamp - ISO format timestamp
 * @returns {string} - Formatted date/time string
 */
function formatTimestamp(isoTimestamp) {
    if (!isoTimestamp) return '';
    
    const date = new Date(isoTimestamp);
    return date.toLocaleString();
}

/**
 * Utility function to handle API errors
 * @param {Error} error - The error object
 * @param {string} context - Context where error occurred
 */
function handleApiError(error, context) {
    console.error(`API Error (${context}):`, error);
    // Could show a toast notification or update UI with error details
}
