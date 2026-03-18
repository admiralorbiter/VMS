document.addEventListener('DOMContentLoaded', function () {
            var btn = document.getElementById('show-more-teachers-btn');
            if (btn) {
                btn.addEventListener('click', function () {
                    document.getElementById('teacher-table-body-extra').style.display = '';
                    btn.style.display = 'none';
                });
            }

            // Handle month header clicks
            document.addEventListener('click', function (e) {
                if (e.target.closest('.month-header')) {
                    const monthHeader = e.target.closest('.month-header');
                    const monthIndex = monthHeader.getAttribute('data-month-index');
                    toggleMonthDetails(monthIndex);
                }
            });
        });

        function toggleMonthDetails(idx) {
            var details = document.getElementById('month-details-' + idx);
            var chevron = document.getElementById('chevron-' + idx);
            if (details.classList.contains('collapsed')) {
                details.classList.remove('collapsed');
                chevron.classList.remove('collapsed');
            } else {
                details.classList.add('collapsed');
                chevron.classList.add('collapsed');
            }
        }
