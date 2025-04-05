/**
 * NuTetra System Settings JavaScript
 * Handles toggle visibility, API requests, and other functionality for the system settings page
 * Note: Tab functionality is handled directly in the HTML template
 */

// Function to show/hide elements based on checkbox state
function toggleVisibility(controlId, targetId) {
    const control = document.getElementById(controlId);
    const target = document.getElementById(targetId);
    
    if (control && target) {
        control.addEventListener('change', function() {
            target.style.display = this.checked ? 'none' : 'block';
        });
        
        // Set initial state
        target.style.display = control.checked ? 'none' : 'block';
    }
}

// Function to show/hide elements based on radio selection
function setupRadioToggle(radioName, options) {
    const radios = document.getElementsByName(radioName);
    
    radios.forEach(radio => {
        radio.addEventListener('change', function() {
            for (const option in options) {
                const element = document.getElementById(options[option]);
                if (element) {
                    element.style.display = this.value === option ? 'block' : 'none';
                }
            }
        });
    });
    
    // Set initial state
    for (const radio of radios) {
        if (radio.checked) {
            for (const option in options) {
                const element = document.getElementById(options[option]);
                if (element) {
                    element.style.display = radio.value === option ? 'block' : 'none';
                }
            }
            break;
        }
    }
}

// Function to show status message
function showStatusMessage(message, type = 'success') {
    const statusMessage = document.getElementById('status-message');
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        statusMessage.textContent = '';
        statusMessage.className = 'status-message';
    }, 3000);
}

// Confirmation modal setup
function setupConfirmation(buttonId, title, message, onConfirm) {
    const button = document.getElementById(buttonId);
    const modal = document.getElementById('confirmation-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const confirmButton = document.getElementById('modal-confirm');
    const cancelButton = document.getElementById('modal-cancel');
    
    if (button) {
        button.addEventListener('click', function() {
            modalTitle.textContent = title;
            modalMessage.textContent = message;
            modal.style.display = 'flex';
            
            // Set up temporary confirm handler
            const confirmHandler = function() {
                onConfirm();
                modal.style.display = 'none';
                confirmButton.removeEventListener('click', confirmHandler);
            };
            
            confirmButton.addEventListener('click', confirmHandler);
            
            cancelButton.addEventListener('click', function() {
                modal.style.display = 'none';
                confirmButton.removeEventListener('click', confirmHandler);
            });
            
            // Close modal when clicking outside
            modal.addEventListener('click', function(event) {
                if (event.target === modal) {
                    modal.style.display = 'none';
                    confirmButton.removeEventListener('click', confirmHandler);
                }
            });
            
            // Close modal with escape key
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') {
                    modal.style.display = 'none';
                    confirmButton.removeEventListener('click', confirmHandler);
                }
            });
        });
    }
}

// Function to safely handle API requests
function makeApiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    return fetch(url, options)
        .then(response => {
            // Check if response is ok (status 200-299)
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            // Check content type to ensure it's JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Response is not JSON. The API endpoint may not be working correctly.');
            }
            
            return response.json();
        })
        .catch(error => {
            console.error('API request failed:', error);
            showStatusMessage(`Request failed: ${error.message}`, 'error');
            throw error;
        });
}

// Load system information
function loadSystemInfo() {
    makeApiRequest('/api/system/info')
        .then(data => {
            document.getElementById('system-name').textContent = data.system_name;
            document.getElementById('software-version').textContent = data.version;
            document.getElementById('system-uptime').textContent = data.uptime;
            document.getElementById('hardware-platform').textContent = data.platform;
            document.getElementById('cpu-temp').textContent = data.cpu_temp;
            document.getElementById('detected-platform').textContent = data.platform;
            document.getElementById('gpio-interface').textContent = data.gpio_interface;
            document.getElementById('gpio-chip').textContent = data.gpio_chip ? `gpiochip${data.gpio_chip}` : 'Not detected';
            
            // Also set form values
            document.getElementById('new-system-name').value = data.system_name;
            
            if (data.gpio_chip !== null) {
                document.getElementById('gpio-chip-select').value = data.gpio_chip;
            }
            
            if (data.gpio_interface) {
                if (data.gpio_interface.includes('rpi_lgpio')) {
                    document.getElementById('gpio-library').value = 'rpi_lgpio';
                } else if (data.gpio_interface.includes('lgpio')) {
                    document.getElementById('gpio-library').value = 'lgpio';
                } else if (data.gpio_interface.includes('simulation')) {
                    document.getElementById('gpio-library').value = 'simulation';
                }
            }
        })
        .catch(error => {
            console.error('Error loading system info:', error);
            showStatusMessage('Failed to load system information. See console for details.', 'error');
        });
}

// Setup all event handlers and button clicks
function setupEventHandlers() {
    // Save system name
    const saveSystemNameBtn = document.getElementById('save-system-name');
    if (saveSystemNameBtn) {
        saveSystemNameBtn.addEventListener('click', function() {
            const newName = document.getElementById('new-system-name').value.trim();
            
            if (newName) {
                makeApiRequest('/api/system/name', 'POST', { name: newName })
                    .then(data => {
                        if (data.success) {
                            showStatusMessage('System name updated', 'success');
                            document.getElementById('system-name').textContent = newName;
                        } else {
                            showStatusMessage(`Error: ${data.message}`, 'error');
                        }
                    })
                    .catch(() => {
                        // Error is already handled by makeApiRequest
                    });
            } else {
                showStatusMessage('System name cannot be empty', 'error');
            }
        });
    }
    
    // Save GPIO settings
    const saveGpioBtn = document.getElementById('save-gpio-settings');
    if (saveGpioBtn) {
        saveGpioBtn.addEventListener('click', function() {
            const chipNumber = document.getElementById('gpio-chip-select').value;
            const library = document.getElementById('gpio-library').value;
            
            makeApiRequest('/api/system/gpio-settings', 'POST', { 
                gpio_chip: parseInt(chipNumber),
                gpio_library: library
            })
                .then(data => {
                    if (data.success) {
                        showStatusMessage('GPIO settings updated. Restart services to apply changes.', 'success');
                        
                        // Update displayed info
                        document.getElementById('gpio-chip').textContent = `gpiochip${chipNumber}`;
                        document.getElementById('gpio-interface').textContent = library;
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(() => {
                    // Error is already handled by makeApiRequest
                });
        });
    }
    
    // Test GPIO
    const testGpioBtn = document.getElementById('test-gpio');
    if (testGpioBtn) {
        testGpioBtn.addEventListener('click', function() {
            makeApiRequest('/api/system/test-gpio', 'POST')
                .then(data => {
                    if (data.success) {
                        showStatusMessage('GPIO test successful', 'success');
                    } else {
                        showStatusMessage(`GPIO test failed: ${data.message}`, 'error');
                    }
                })
                .catch(() => {
                    // Error is already handled by makeApiRequest
                });
        });
    }
    
    // Save pin assignments
    const savePinsBtn = document.getElementById('save-pin-assignments');
    if (savePinsBtn) {
        savePinsBtn.addEventListener('click', function() {
            const pinAssignments = {
                ph_up: parseInt(document.getElementById('ph-up-pin').value),
                ph_down: parseInt(document.getElementById('ph-down-pin').value),
                nutrient_a: parseInt(document.getElementById('nutrient-a-pin').value),
                nutrient_b: parseInt(document.getElementById('nutrient-b-pin').value),
                main: parseInt(document.getElementById('main-pump-pin').value),
                i2c_bus: parseInt(document.getElementById('i2c-bus').value),
                i2c_enabled: document.getElementById('i2c-enabled').checked
            };
            
            makeApiRequest('/api/system/pin-assignments', 'POST', pinAssignments)
                .then(data => {
                    if (data.success) {
                        showStatusMessage('Pin assignments saved. Restart services to apply changes.', 'success');
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(() => {
                    // Error is already handled by makeApiRequest
                });
        });
    }
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded - initializing system settings page");
    
    // Ensure modal is hidden
    const modal = document.getElementById('confirmation-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    // Set up toggle visibility
    toggleVisibility('date-time-auto', 'manual-date-time');
    toggleVisibility('ip-auto', 'static-ip-settings');
    toggleVisibility('enable-auth', 'auth-settings', true);
    toggleVisibility('enable-email', 'email-settings', true);
    toggleVisibility('enable-push', 'push-settings', true);
    
    // Set up radio toggle
    setupRadioToggle('push-service', {
        'pushover': 'pushover-settings',
        'telegram': 'telegram-settings'
    });
    
    // Set up confirmation handlers
    setupConfirmation('system-restart', 'Restart System', 
        'Are you sure you want to restart all nutetra services?', 
        function() {
            // Send restart services request
            makeApiRequest('/api/system/restart', 'POST')
                .then(data => {
                    if (data.success) {
                        showStatusMessage('System services restarting...', 'success');
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(() => {
                    // Error is already handled by makeApiRequest
                });
        }
    );
    
    setupConfirmation('system-reboot', 'Reboot Device', 
        'Are you sure you want to reboot the Raspberry Pi? This will disconnect your session.',
        function() {
            // Send reboot request
            makeApiRequest('/api/system/reboot', 'POST')
                .then(data => {
                    if (data.success) {
                        showStatusMessage('Device is rebooting. Please wait...', 'success');
                        
                        // Show countdown to reconnect
                        setTimeout(() => {
                            document.body.innerHTML = '<div class="reboot-message">' +
                                '<h2>Device is rebooting</h2>' +
                                '<p>Please wait while the system restarts.</p>' +
                                '<p>This page will attempt to reconnect in <span id="countdown">60</span> seconds.</p>' +
                                '</div>';
                            
                            let countdown = 60;
                            const countdownElement = document.getElementById('countdown');
                            
                            const interval = setInterval(() => {
                                countdown--;
                                countdownElement.textContent = countdown;
                                
                                if (countdown <= 0) {
                                    clearInterval(interval);
                                    window.location.reload();
                                }
                            }, 1000);
                        }, 2000);
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(() => {
                    // Error is already handled by makeApiRequest
                });
        }
    );
    
    setupConfirmation('clear-logs', 'Clear System Logs', 
        'Are you sure you want to clear all system logs? This cannot be undone.',
        function() {
            // Send clear logs request
            makeApiRequest('/api/system/clear-logs', 'POST')
                .then(data => {
                    if (data.success) {
                        showStatusMessage('System logs cleared', 'success');
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(() => {
                    // Error is already handled by makeApiRequest
                });
        }
    );
    
    setupConfirmation('factory-reset', 'Factory Reset', 
        'WARNING: This will reset all settings and erase all data. This cannot be undone! Type "RESET" to confirm.',
        function() {
            const confirmInput = document.getElementById('confirm-reset');
            
            if (confirmInput && confirmInput.value === 'RESET') {
                // Send factory reset request
                makeApiRequest('/api/system/factory-reset', 'POST')
                    .then(data => {
                        if (data.success) {
                            showStatusMessage('Factory reset initiated. System will reboot.', 'success');
                            
                            setTimeout(() => {
                                window.location.href = '/';
                            }, 5000);
                        } else {
                            showStatusMessage(`Error: ${data.message}`, 'error');
                        }
                    })
                    .catch(() => {
                        // Error is already handled by makeApiRequest
                    });
            } else {
                showStatusMessage('Please type "RESET" in the confirmation field to proceed with factory reset', 'error');
            }
        }
    );
    
    // Setup event handlers for buttons
    setupEventHandlers();
    
    // Load system info
    loadSystemInfo();
    
    console.log("All initialization complete");
}); 