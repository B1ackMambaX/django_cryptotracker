document.getElementById('refreshPrices').addEventListener('click', function() {
    const btn = this;
    const url = btn.dataset.url;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Обновление...';

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('warning', data.error);
            }

            document.getElementById('totalInvested').textContent = '$' + data.totals.total_invested.toFixed(2);
            document.getElementById('totalValue').textContent = '$' + data.totals.total_current_value.toFixed(2);

            const plSign = data.totals.total_profit_loss >= 0 ? '+' : '';
            const plPercent = data.totals.total_profit_loss_percent.toFixed(2);
            document.getElementById('totalPL').textContent =
                plSign + '$' + data.totals.total_profit_loss.toFixed(2) + ' (' + plSign + plPercent + '%)';
            document.getElementById('totalPL').className =
                'card-title ' + (data.totals.total_profit_loss >= 0 ? 'profit' : 'loss');

            data.portfolios.forEach(p => {
                const row = document.querySelector(`tr[data-portfolio-id="${p.id}"]`);
                if (row) {
                    row.querySelector('.current-price').textContent = '$' + p.current_price.toFixed(2);
                    row.querySelector('.current-value').textContent = '$' + p.current_value.toFixed(2);

                    const plSign = p.profit_loss >= 0 ? '+' : '';
                    const plClass = p.profit_loss >= 0 ? 'profit' : 'loss';

                    row.querySelector('.profit-loss').textContent = plSign + '$' + p.profit_loss.toFixed(2);
                    row.querySelector('.profit-loss').className = plClass + ' profit-loss';

                    row.querySelector('.profit-loss-percent').textContent =
                        '(' + plSign + p.profit_loss_percent.toFixed(2) + '%)';
                    row.querySelector('.profit-loss-percent').className = plClass + ' profit-loss-percent';
                }
            });

            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Обновить цены';
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'Ошибка при обновлении цен. Проверьте подключение к интернету.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Обновить цены';
        });
});

function showAlert(type, message) {
    const existingAlerts = document.querySelectorAll('.ajax-alert');
    existingAlerts.forEach(alert => alert.remove());

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show ajax-alert`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector('main.container');
    const firstChild = container.querySelector('.d-flex');
    container.insertBefore(alertDiv, firstChild);

    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}
