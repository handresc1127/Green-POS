/**
 * Green-POS Main JavaScript File
 */

// Clase simplificada para manejo de impresión
class POSPrinter {
    static feedPaper() {
        const spacer = document.createElement('div');
        spacer.style.height = '40px';
        spacer.className = 'print-spacer';
        return spacer;
    }

    static removeFeedPaper() {
        const spacers = document.querySelectorAll('.print-spacer');
        spacers.forEach(spacer => spacer.remove());
    }
}

// Crear una instancia global del controlador de la impresora
window.posPrinter = new POSPrinter();

document.addEventListener('DOMContentLoaded', function () {
    // Activate Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    const autoAlerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    autoAlerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Format currency inputs
    const currencyInputs = document.querySelectorAll('.currency-input');
    currencyInputs.forEach(function (input) {
        input.addEventListener('blur', function () {
            const value = parseFloat(this.value);
            if (!isNaN(value)) {
                this.value = value.toFixed(2);
            }
        });
    });

    // Confirm dangerous actions
    const dangerForms = document.querySelectorAll('form.confirm-submit');
    dangerForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            const confirmMessage = this.dataset.confirmMessage || '¿Está seguro de realizar esta acción?';
            if (!confirm(confirmMessage)) {
                e.preventDefault();
            }
        });
    });
});
