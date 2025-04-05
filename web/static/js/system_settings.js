/**
 * NuTetra System Settings JavaScript
 * Handles tab navigation, toggle visibility, and API requests for the system settings page
 */

// Tab switching function with direct style manipulation
function showTab(tabId) {
    console.log("showTab called for:", tabId);
    
    // Hide all tab contents with !important
    document.querySelectorAll('.tab-content').forEach(function(tab) {
        tab.style.cssText = 'display: none !important';
        console.log("Hiding tab:", tab.id);
    });
    
    // Show the selected tab with !important
    var selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.style.cssText = 'display: block !important';
        console.log("Showing tab:", tabId);
    } else {
        console.error("Tab not found:", tabId);
    }
    
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(function(btn) {
        btn.classList.remove('active');
        btn.style.background = '';
        btn.style.color = '';
        console.log("Removing active class from button:", btn.id);
    });
    
    var activeButton = document.getElementById('btn-' + tabId);
    if (activeButton) {
        activeButton.classList.add('active');
        console.log("Added active class to button:", activeButton.id);
    } else {
        console.error("Button not found for tab:", tabId);
    }
}

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

// Load system information
function loadSystemInfo() {
    fetch('/api/system/info')
        .then(response => response.json())
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
                fetch('/api/system/name', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name: newName }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatusMessage('System name updated', 'success');
                        document.getElementById('system-name').textContent = newName;
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    showStatusMessage(`Error: ${error.message}`, 'error');
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
            
            fetch('/api/system/gpio-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    gpio_chip: parseInt(chipNumber),
                    gpio_library: library
                }),
            })
            .then(response => response.json())
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
            .catch(error => {
                showStatusMessage(`Error: ${error.message}`, 'error');
            });
        });
    }
    
    // Test GPIO
    const testGpioBtn = document.getElementById('test-gpio');
    if (testGpioBtn) {
        testGpioBtn.addEventListener('click', function() {
            fetch('/api/system/test-gpio', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatusMessage('GPIO test successful', 'success');
                    } else {
                        showStatusMessage(`GPIO test failed: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    showStatusMessage(`Error: ${error.message}`, 'error');
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
            
            fetch('/api/system/pin-assignments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(pinAssignments),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatusMessage('Pin assignments saved. Restart services to apply changes.', 'success');
                } else {
                    showStatusMessage(`Error: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                showStatusMessage(`Error: ${error.message}`, 'error');
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
    
    // Make sure the first tab is shown
    showTab('general-tab');
    
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
            fetch('/api/system/restart', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatusMessage('System services restarting...', 'success');
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    showStatusMessage(`Error: ${error.message}`, 'error');
                });
        }
    );
    
    setupConfirmation('system-reboot', 'Reboot Device', 
        'Are you sure you want to reboot the Raspberry Pi? This will disconnect your session.',
        function() {
            // Send reboot request
            fetch('/api/system/reboot', { method: 'POST' })
                .then(response => response.json())
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
                .catch(error => {
                    showStatusMessage(`Error: ${error.message}`, 'error');
                });
        }
    );
    
    setupConfirmation('clear-logs', 'Clear System Logs', 
        'Are you sure you want to clear all system logs? This cannot be undone.',
        function() {
            // Send clear logs request
            fetch('/api/system/clear-logs', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatusMessage('System logs cleared', 'success');
                    } else {
                        showStatusMessage(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    showStatusMessage(`Error: ${error.message}`, 'error');
                });
        }
    );
    
    setupConfirmation('factory-reset', 'Factory Reset', 
        'WARNING: This will reset all settings and erase all data. This cannot be undone!',
        function() {
            const confirmInput = document.getElementById('confirm-reset');
            
            if (confirmInput.value === 'RESET') {
                // Send factory reset request
                fetch('/api/system/factory-reset', { method: 'POST' })
                    .then(response => response.json())
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
                    .catch(error => {
                        showStatusMessage(`Error: ${error.message}`, 'error');
                    });
            } else {
                showStatusMessage('Please type "RESET" to confirm factory reset', 'error');
            }
        }
    );
    
    // Setup event handlers for buttons
    setupEventHandlers();
    
    // Load system info
    loadSystemInfo();
    
    console.log("All initialization complete");
}); 